import pytest

from src.agents.patron_itself.patron_agent import agent


@pytest.mark.asyncio
async def test_agent():
    user_ask = "It's cold today"

    response = agent.invoke(
        {"messages": [{"role": "user", "content": user_ask}]}
    )

    print(response)
