from datetime import datetime, timezone, timedelta

import pytest
from qdrant_client import QdrantClient

from agents.patron_itself.repositories.memories_repository import MemoriesRepository, COLLECTION_NAME
from agents.patron_itself.tools.memory_tools import create_memory_tools

USER_ID = "tool_test_user"


@pytest.fixture()
def repo(test_container):
    repo = test_container.get(MemoriesRepository)
    yield repo
    try:
        test_container.get(QdrantClient).delete_collection(COLLECTION_NAME)
    except Exception:
        pass


@pytest.fixture()
def tools(repo):
    return {t.name: t for t in create_memory_tools(repo)}


class TestAddMemory:

    def test_saves_and_returns_id(self, tools):
        result = tools["add_memory"].invoke(
            {"text": "Remember this", "user_id": USER_ID}
        )

        assert "Memory saved" in result
        assert "id:" in result

    def test_saves_with_metadata(self, tools, repo):
        result = tools["add_memory"].invoke(
            {"text": "With meta", "user_id": USER_ID, "metadata": {"tag": "test"}}
        )
        point_id = result.split("id: ")[1].rstrip(")")

        memory = repo.get_by_id(point_id)
        assert memory["metadata"] == {"tag": "test"}


class TestRecallMemoriesBySemanticQuery:

    def test_returns_matching_memories(self, tools):
        tools["add_memory"].invoke({"text": "I like pizza", "user_id": USER_ID})
        tools["add_memory"].invoke({"text": "My cat is fluffy", "user_id": USER_ID})

        results = tools["recall_memories_by_semantic_query"].invoke(
            {"query": "food preferences", "user_id": USER_ID}
        )

        assert len(results) > 0
        assert all("text" in r for r in results)

    def test_respects_limit(self, tools):
        for i in range(5):
            tools["add_memory"].invoke({"text": f"Memory {i}", "user_id": USER_ID})

        results = tools["recall_memories_by_semantic_query"].invoke(
            {"query": "memory", "user_id": USER_ID, "limit": 2}
        )

        assert len(results) == 2


class TestRecallMemoriesByTimeConstraints:

    def test_filters_by_date_range(self, tools, repo):
        base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo.save(USER_ID, "January", created_at=base)
        repo.save(USER_ID, "March", created_at=base + timedelta(days=60))

        results = tools["recall_memories_by_time_constraints"].invoke({
            "user_id": USER_ID,
            "date_from": base.isoformat(),
            "date_to": (base + timedelta(days=30)).isoformat(),
        })

        texts = [r["text"] for r in results]
        assert "January" in texts
        assert "March" not in texts


class TestDeleteMemory:

    def test_deletes_memory(self, tools, repo):
        point_id = repo.save(USER_ID, "To be deleted")

        result = tools["delete_memory"].invoke({"memory_id": point_id})

        assert "deleted" in result
        assert repo.get_by_id(point_id) is None
