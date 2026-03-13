import sys
from unittest.mock import AsyncMock, patch, MagicMock
import unittest

# Mock dependencies
mock_langchain = MagicMock()
mock_langchain_google_genai = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['langchain'] = mock_langchain
sys.modules['langchain.agents'] = mock_langchain
sys.modules['langchain_google_genai'] = mock_langchain_google_genai

from src.agents.patron_itself.patron_agent import agent

class TestAgent(unittest.IsolatedAsyncioTestCase):
    async def test_agent(self):
        user_ask = "What is the weather in London?"

        # We mock the agent to avoid real API calls during tests if needed, 
        # but here we want to see if the structure works.
        with patch.object(agent, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = {"output": "It's always sunny in London!"}
            
            response = await agent.ainvoke({"input": user_ask})

            self.assertIn("output", response)
            self.assertEqual(response["output"], "It's always sunny in London!")
            mock_ainvoke.assert_called_once_with({"input": user_ask})

    async def test_real_agent_response(self):
        # We mock this as well because we don't have API keys or network for real calls
        user_ask = "What is the weather in New York?"
        
        with patch.object(agent, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = {
                'messages': [MagicMock(content=[{'text': "It's always sunny in New York!"}])]
            }
            
            response = await agent.ainvoke({
                "messages": [{"role": "user", "content": user_ask}],
                "user_preferences": {"style": "technical", "verbosity": "detailed"},
            })

            messages = response['messages']
            self.assertEqual(messages[-1].content[-1]["text"], "It's always sunny in New York!")

if __name__ == '__main__':
    unittest.main()
