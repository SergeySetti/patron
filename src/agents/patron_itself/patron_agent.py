import base64
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import ModelFallbackMiddleware, SummarizationMiddleware
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.graph.state import CompiledStateGraph

from agents.patron_itself.middleware import ToolLoggingMiddleware
from agents.patron_itself.repositories.memories_repository import MemoriesRepository
from agents.patron_itself.repositories.tasks_repository import TasksRepository
from agents.patron_itself.repositories.users_repository import UsersRepository
from agents.patron_itself.tools.memory_tools import create_memory_tools
from agents.patron_itself.tools.task_tools import create_task_tools
from agents.patron_itself.tools.user_tools import create_user_tools
from dependencies import app_container

load_dotenv()


class CustomAgentState(AgentState):
    user_id: str
    chat_id: str
    preferences: dict
    user_timezone: str


CLAUDE = "anthropic:claude-opus-4-6"
GEMINI = "google_genai:gemini-3.1-pro-preview"

PRIMARY_MODEL = GEMINI
SECONDARY_MODEL = CLAUDE

model = init_chat_model(PRIMARY_MODEL)

DB_URI = os.getenv("ASSISTANT_SESSIONS_DATABASE_URL")
MONGODB_URI = os.getenv("MONGODB_URI")

_memory_tools = None
_task_tools = None
_user_tools = None


def _get_memory_tools() -> list:
    global _memory_tools
    if _memory_tools is None:
        memories_repo = app_container.get(MemoriesRepository)
        _memory_tools = create_memory_tools(memories_repo)
    return _memory_tools


def _get_task_tools() -> list:
    global _task_tools
    if _task_tools is None:
        tasks_repo = app_container.get(TasksRepository)
        _task_tools = create_task_tools(tasks_repo)
    return _task_tools


def _get_user_tools() -> list:
    global _user_tools
    if _user_tools is None:
        users_repo = app_container.get(UsersRepository)
        _user_tools = create_user_tools(users_repo)
    return _user_tools


def _get_user_timezone(user_id: str) -> str:
    """Fetch stored timezone for the user, or empty string if unknown."""
    users_repo = app_container.get(UsersRepository)
    return users_repo.get_timezone(user_id) or ""


async def run_agent(message: str, user_id: str = None, thread_id: str = None,
                    audio: bytes = None, image: bytes = None, image_mime: str = None):
    use_checkpointer = user_id is not None and thread_id is not None

    if use_checkpointer:
        with MongoDBSaver.from_conn_string(MONGODB_URI, 'patron_sessions') as checkpointer:
            return await _invoke_agent(message, user_id, thread_id, checkpointer,
                                       audio=audio, image=image, image_mime=image_mime)
    else:
        return await _invoke_agent(message, user_id, thread_id,
                                   audio=audio, image=image, image_mime=image_mime)


def _get_user_custom_prompt(user_id: str) -> str:
    """Fetch stored custom prompt for the user, or empty string."""
    users_repo = app_container.get(UsersRepository)
    return users_repo.get_custom_prompt(user_id) or ""


_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def _build_system_prompt(user_timezone: str, custom_prompt: str = "") -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if user_timezone:
        timezone_block = _load_prompt("timezone_known.md").format(user_timezone=user_timezone)
    else:
        timezone_block = _load_prompt("timezone_unknown.md")

    custom_prompt_block = f"User instructions:\n{custom_prompt}" if custom_prompt else ""

    return _load_prompt("system_prompt.md").format(
        current_time=now_utc,
        timezone_block=timezone_block,
        custom_prompt_block=custom_prompt_block,
    ).rstrip()


async def _invoke_agent(message: str, user_id: str, thread_id: str, checkpointer=None,
                        audio: bytes = None, image: bytes = None, image_mime: str = None):
    user_timezone = _get_user_timezone(user_id) if user_id else ""
    custom_prompt = _get_user_custom_prompt(user_id) if user_id else ""

    agent: CompiledStateGraph = create_agent(
        model=model,
        tools=[*_get_memory_tools(), *_get_task_tools(), *_get_user_tools()],
        state_schema=CustomAgentState,  # noqa
        checkpointer=checkpointer,
        system_prompt=_build_system_prompt(user_timezone, custom_prompt),
        middleware=[
            ToolLoggingMiddleware(),
            # ModelFallbackMiddleware(GEMINI),
            SummarizationMiddleware(
                model=PRIMARY_MODEL,
                trigger=("tokens", 10000),  # noqa
                keep=("messages", 100),  # noqa
            )
        ],
    )

    config = {"configurable": {"thread_id": thread_id}} if thread_id else None

    content = []
    if audio:
        content.append({
            "type": "media",
            "mime_type": "audio/ogg",
            "data": base64.b64encode(audio).decode("utf-8"),
        })
    if image:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{image_mime};base64,{base64.b64encode(image).decode('utf-8')}",
            },
        })
    if message:
        content.append({"type": "text", "text": message})

    if not content:
        content = message

    return await agent.ainvoke(
        {  # noqa
            "messages": [{"role": "user", "content": content}],
            "user_id": user_id,
            "chat_id": thread_id or "",
            "user_timezone": user_timezone,
        },
        config,
    )
