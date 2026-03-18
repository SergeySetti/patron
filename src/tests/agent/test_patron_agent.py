import os
from contextlib import nullcontext, ExitStack
from pprint import pprint
from unittest.mock import patch, MagicMock

import pytest
from injector import Injector
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from src.agents.patron_itself.patron_agent import run_agent
from src.tests.conftest import TestPatronModule

USE_REAL_API = os.environ.get("PATRON_REAL_API", "").lower() in ("1", "true", "yes")
USE_REAL_API = 0


class FakeChatModel(FakeMessagesListChatModel):
    """Fake chat model that supports bind_tools (needed by create_agent)."""

    def bind_tools(self, tools, **kwargs):
        """Accept tools but ignore them — responses are pre-scripted."""
        return self


def _make_fake_model(responses: list[str] | None = None):
    """Build a FakeChatModel with canned AIMessage responses."""
    if responses is None:
        responses = ["I'm a fake response from the mocked model."]
    return FakeChatModel(responses=[AIMessage(content=r) for r in responses])


def _patch_model(responses: list[str] | None = None):
    """Patch model, init_chat_model, and app_container. No-op when PATRON_REAL_API=1."""
    if USE_REAL_API:
        return nullcontext()

    fake = _make_fake_model(responses)
    test_container = Injector([TestPatronModule()])
    stack = ExitStack()

    # Patch the module-level `model` (used when no model_override)
    stack.enter_context(patch("src.agents.patron_itself.patron_agent.model", fake))
    # Patch init_chat_model (used when model_override is passed, and by SummarizationMiddleware)
    stack.enter_context(patch("src.agents.patron_itself.patron_agent.init_chat_model", return_value=fake))
    # Patch app_container with in-memory Qdrant + mongomock (no external services needed)
    stack.enter_context(patch("src.agents.patron_itself.patron_agent.app_container", test_container))
    # Reset cached tool globals so they re-initialize with the test container
    stack.enter_context(patch("src.agents.patron_itself.patron_agent._memory_tools", None))
    stack.enter_context(patch("src.agents.patron_itself.patron_agent._task_tools", None))
    stack.enter_context(patch("src.agents.patron_itself.patron_agent._user_tools", None))

    return stack


@pytest.mark.asyncio
async def test_agent_response():
    with _patch_model(["The weather in New York is sunny and 72°F."]):
        response = await run_agent("What is the weather in New York?")

    last_message = response["messages"][-1].text
    print(last_message)
    assert last_message


@pytest.mark.asyncio
async def test_agent_with_checkpointer():
    with _patch_model(["Here's a joke: Why do programmers prefer dark mode? Because light attracts bugs!"]) as _:
        with patch("src.agents.patron_itself.patron_agent.MongoDBSaver") as mock_mongo_saver:
            in_memory_checkpointer = InMemorySaver()
            mock_mongo_saver.from_conn_string.return_value.__enter__ = MagicMock(return_value=in_memory_checkpointer)
            mock_mongo_saver.from_conn_string.return_value.__exit__ = MagicMock(return_value=False)

            response = await run_agent(
                "I bet you can't tell me a joke and save the conversation state!",
                "user1",
                "session1",
            )

    pprint(response)

    message_text = response["messages"][-1].text
    print(message_text)
    assert message_text

    mock_mongo_saver.from_conn_string.assert_called_once()
