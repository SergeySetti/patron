from pprint import pprint
from unittest import skip
from unittest.mock import patch, MagicMock

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from src.agents.patron_itself.patron_agent import run_agent


@pytest.mark.asyncio
@skip("This test is meant for manual inspection and requires real API calls. Uncomment to run.")
async def test_real_agent_response():
    user_ask = "What is the weather in New York?"

    # response = await run_agent(user_ask, 'user1', 'session1')
    response = await run_agent(user_ask)

    messages = response['messages']
    print(
        messages[-1].text
    )  # Print the last message content for inspection


@pytest.mark.asyncio
@skip("This test requires real API calls and external service connections. Uncomment to run.")
@patch("src.agents.patron_itself.patron_agent.MongoDBSaver")
async def test_agent_with_checkpointer(mock_mongo_saver):
    in_memory_checkpointer = InMemorySaver()
    mock_mongo_saver.from_conn_string.return_value.__enter__ = MagicMock(return_value=in_memory_checkpointer)
    mock_mongo_saver.from_conn_string.return_value.__exit__ = MagicMock(return_value=False)

    user_ask = "I bet you can't tell me a joke and save the conversation state in the checkpointer at the same time!"

    response = await run_agent(user_ask, 'user1', 'session1')

    pprint(response)

    message_text = response["messages"][-1].text
    print(message_text)

    mock_mongo_saver.from_conn_string.assert_called_once()
