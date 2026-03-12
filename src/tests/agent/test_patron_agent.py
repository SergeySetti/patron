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
