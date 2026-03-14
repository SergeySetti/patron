import uuid
from datetime import datetime, timezone, timedelta

import pytest
from qdrant_client import QdrantClient

from agents.patron_itself.repositories.memories_repository import MemoriesRepository, COLLECTION_NAME

TEST_USER_ID = "test_user_42"


@pytest.fixture()
def repo(test_container):
    repo = test_container.get(MemoriesRepository)
    yield repo
    try:
        test_container.get(QdrantClient).delete_collection(COLLECTION_NAME)
    except Exception:
        pass


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

    def test_save_stores_created_at(self, repo):
        point_id = repo.save(TEST_USER_ID, "Timestamped memory")

        result = repo.get_by_id(point_id)

        assert result["created_at"] is not None
        parsed = datetime.fromisoformat(result["created_at"])
        assert parsed.tzinfo is not None

    def test_save_with_explicit_created_at(self, repo):
        ts = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        point_id = repo.save(TEST_USER_ID, "Memory with explicit date", created_at=ts)

        result = repo.get_by_id(point_id)

        assert result["created_at"] == ts.isoformat()

    def test_find_by_date_range(self, repo):
        base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo.save(TEST_USER_ID, "January memory", created_at=base)
        repo.save(TEST_USER_ID, "February memory", created_at=base + timedelta(days=31))
        repo.save(TEST_USER_ID, "March memory", created_at=base + timedelta(days=60))

        results = repo.find_by_date_range(
            TEST_USER_ID,
            date_from=base,
            date_to=base + timedelta(days=35),
        )

        texts = [r["text"] for r in results]
        assert "January memory" in texts
        assert "February memory" in texts
        assert "March memory" not in texts

    def test_find_by_date_range_open_ended_from(self, repo):
        base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo.save(TEST_USER_ID, "Old memory", created_at=base)
        repo.save(TEST_USER_ID, "New memory", created_at=base + timedelta(days=60))

        results = repo.find_by_date_range(TEST_USER_ID, date_from=base + timedelta(days=30))

        texts = [r["text"] for r in results]
        assert "New memory" in texts
        assert "Old memory" not in texts

    def test_find_by_date_range_open_ended_to(self, repo):
        base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo.save(TEST_USER_ID, "Old memory", created_at=base)
        repo.save(TEST_USER_ID, "New memory", created_at=base + timedelta(days=60))

        results = repo.find_by_date_range(TEST_USER_ID, date_to=base + timedelta(days=30))

        texts = [r["text"] for r in results]
        assert "Old memory" in texts
        assert "New memory" not in texts

    def test_find_by_date_range_filters_by_user(self, repo):
        ts = datetime(2025, 3, 1, tzinfo=timezone.utc)
        repo.save("user_A", "A's memory", created_at=ts)
        repo.save("user_B", "B's memory", created_at=ts)

        results = repo.find_by_date_range("user_A", date_from=ts, date_to=ts)

        texts = [r["text"] for r in results]
        assert "A's memory" in texts
        assert "B's memory" not in texts
