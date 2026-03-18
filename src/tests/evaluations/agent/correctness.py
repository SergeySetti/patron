import asyncio
from unittest.mock import patch, MagicMock

import nest_asyncio
import mlflow
from langgraph.checkpoint.memory import InMemorySaver
from mlflow.genai.scorers import Correctness

from agents.patron_itself.patron_agent import run_agent

nest_asyncio.apply()


@patch("src.agents.patron_itself.patron_agent.MongoDBSaver")
def test_agent_with_checkpointer(mock_mongo_saver):
    mlflow.autolog(disable=True)
    mlflow.set_tracking_uri("http://localhost:5000")

    in_memory_checkpointer = InMemorySaver()
    mock_mongo_saver.from_conn_string.return_value.__enter__ = MagicMock(return_value=in_memory_checkpointer)
    mock_mongo_saver.from_conn_string.return_value.__exit__ = MagicMock(return_value=False)

    loop = asyncio.get_event_loop()

    def predict_fn(question):
        response = loop.run_until_complete(run_agent(question, "user1", "session2"))
        return response["messages"][-1].text

    # QA pairs for evaluation
    dataset = [
        {
            "inputs": {"question": "Can MLflow manage prompts?"},
            "expectations": {"expected_response": "Yes!"},
        },
        {
            "inputs": {"question": "Can MLflow create a taco for my lunch?"},
            "expectations": {"expected_response": "No, unfortunately, MLflow is not a taco maker."},
        },
    ]

    # Run the evaluation
    results = mlflow.genai.evaluate(
        data=dataset,
        predict_fn=predict_fn,
        scorers=[
            # Built-in LLM judge
            Correctness(model="gemini:/gemini-3.1-flash-lite-preview"),
        ],
    )
