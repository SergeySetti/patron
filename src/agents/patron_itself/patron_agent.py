import os

from dotenv import load_dotenv
from langchain.agents import create_agent, AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.graph.state import CompiledStateGraph

from agents.patron_itself.repositories.memories_repository import MemoriesRepository
from agents.patron_itself.tools.memory_tools import create_memory_tools
from dependencies import app_container

load_dotenv()


class CustomAgentState(AgentState):
    user_id: str
    preferences: dict


def get_weather(city: str) -> str:
    """Get weather for a given city"""
    return f"It's always sunny in {city}!"


model = ChatGoogleGenerativeAI(model="gemini-3.1-pro-preview")

DB_URI = os.getenv("ASSISTANT_SESSIONS_DATABASE_URL")
MONGODB_URI = os.getenv("MONGODB_URI")

_memory_tools = None


def _get_memory_tools() -> list:
    global _memory_tools
    if _memory_tools is None:
        memories_repo = app_container.get(MemoriesRepository)
        _memory_tools = create_memory_tools(memories_repo)
    return _memory_tools


async def run_agent(message: str, user_id: str = None, thread_id: str = None):
    use_checkpointer = user_id is not None and thread_id is not None

    if use_checkpointer:
        with MongoDBSaver.from_conn_string(MONGODB_URI, 'patron_sessions') as checkpointer:
            return await _invoke_agent(message, user_id, thread_id, checkpointer)
    else:
        return await _invoke_agent(message, user_id, thread_id)


async def _invoke_agent(message: str, user_id: str, thread_id: str, checkpointer=None):
    agent: CompiledStateGraph = create_agent(
        model=model,
        tools=[get_weather, *_get_memory_tools()],
        state_schema=CustomAgentState,  # noqa
        checkpointer=checkpointer,
        system_prompt="You are a helpful assistant",
    )

    config = {"configurable": {"thread_id": thread_id}} if thread_id else None

    return await agent.ainvoke(
        {  # noqa
            "messages": [{"role": "user", "content": message}],
            "user_id": user_id,
        },
        config,
    )
