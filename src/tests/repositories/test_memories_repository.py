import os
import uuid

import pytest
from unittest.mock import MagicMock
from qdrant_client import QdrantClient

from agents.patron_itself.repositories.memories_repository import MemoriesRepository, COLLECTION_NAME

USE_REAL_QDRANT = os.getenv("USE_REAL_QDRANT", "").lower() in ("1", "true", "yes")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
TEST_USER_ID = "test_user_42"


def _make_fake_vector(seed: float = 0.1) -> list[float]:
    """Create a deterministic 768-dim vector for testing without hitting Gemini API."""
    import math
    return [math.sin(seed * (i + 1)) for i in range(768)]


@pytest.fixture()
def qdrant():
    """Use in-memory Qdrant by default; set USE_REAL_QDRANT=1 for a real instance."""
    if USE_REAL_QDRANT:
        client = QdrantClient(url=QDRANT_URL)
    else:
        client = QdrantClient(location=":memory:")
    yield client
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass


@pytest.fixture()
def vectorizer_mock():
    """Mock the VectorizerGemini so tests don't need a Google API key."""
    mock = MagicMock()
    call_counter = {"n": 0}

    def side_effect(text, task_type=None):
        call_counter["n"] += 1
        return _make_fake_vector(seed=call_counter["n"] * 0.1 + hash(text) % 100)

    mock.vectorize_one.side_effect = side_effect
    return mock


@pytest.fixture()
def repo(qdrant, vectorizer_mock):
    return MemoriesRepository(qdrant_client=qdrant, vectorizer=vectorizer_mock)


class TestMemoriesRepository:

    def test_save_and_get_by_id(self, repo):
        point_id = repo.save(TEST_USER_ID, "Remember to buy milk")

        result = repo.get_by_id(point_id)

        assert result is not None
        assert result["id"] == point_id
        assert result["text"] == "Remember to buy milk"

    def test_save_with_metadata(self, repo):
        point_id = repo.save(TEST_USER_ID, "Meeting at 3pm", metadata={"category": "calendar"})

        result = repo.get_by_id(point_id)

        assert result["metadata"] == {"category": "calendar"}

    def test_search_returns_relevant_memories(self, repo):
        repo.save(TEST_USER_ID, "I love Italian pasta with tomato sauce")
        repo.save(TEST_USER_ID, "My dentist appointment is on Friday")
        repo.save(TEST_USER_ID, "The best pizza place is on Main Street")

        results = repo.search(TEST_USER_ID, "food and restaurants")

        assert len(results) > 0
        assert all(r["text"] for r in results)
        assert all(r["score"] is not None for r in results)

    def test_search_filters_by_user_id(self, repo):
        repo.save("user_A", "Secret memory of user A")
        repo.save("user_B", "Secret memory of user B")

        results_a = repo.search("user_A", "secret")
        results_b = repo.search("user_B", "secret")

        texts_a = [r["text"] for r in results_a]
        texts_b = [r["text"] for r in results_b]

        assert "Secret memory of user A" in texts_a
        assert "Secret memory of user B" not in texts_a
        assert "Secret memory of user B" in texts_b
        assert "Secret memory of user A" not in texts_b

    def test_search_respects_limit(self, repo):
        for i in range(5):
            repo.save(TEST_USER_ID, f"Memory number {i}")

        results = repo.search(TEST_USER_ID, "memory", limit=2)

        assert len(results) == 2

    def test_delete(self, repo):
        point_id = repo.save(TEST_USER_ID, "Memory to delete")

        repo.delete(point_id)

        result = repo.get_by_id(point_id)
        assert result is None

    def test_get_by_id_not_found(self, repo):
        result = repo.get_by_id(str(uuid.uuid4()))

        assert result is None
