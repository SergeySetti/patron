from pprint import pprint

import pytest
from unittest.mock import AsyncMock, patch
from src.agents.patron_itself.patron_agent import agent

@pytest.mark.asyncio
async def test_agent():
    user_ask = "What is the weather in London?"

    # We mock the agent to avoid real API calls during tests if needed, 
    # but here we want to see if the structure works.
    # Since we can't run it without API key, let's mock the ainvoke.
    with patch.object(agent, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
        mock_ainvoke.return_value = {"output": "It's always sunny in London!"}
        
        response = await agent.ainvoke({"input": user_ask})

        assert "output" in response
        assert response["output"] == "It's always sunny in London!"
        mock_ainvoke.assert_called_once_with({"input": user_ask})

@pytest.mark.asyncio
async def test_real_agent_response():
    user_ask = "What is the weather in New York?"
    real_agent = agent  # Use the real agent without mocking
    # This test will actually call the agent, so it requires a valid API key and network access.
    response = await agent.ainvoke({
        "messages": [{"role": "user", "content": user_ask}],
        "user_preferences": {"style": "technical", "verbosity": "detailed"},
    })

    messages = response['messages']
    print(
        messages[-1].content[-1]["text"]
    )  # Print the last message content for inspection
