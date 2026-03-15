from datetime import datetime, timezone, timedelta

import pytest

from agents.patron_itself.repositories.tasks_repository import TasksRepository

TEST_USER_ID = "test_user_42"
TEST_CHAT_ID = "chat_123"


@pytest.fixture()
def repo(test_container):
    repo = test_container.get(TasksRepository)
    yield repo
    repo._collection.drop()


class TestTasksRepository:

    def test_create_and_get_tasks(self, repo):
        due = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Buy groceries", due)

        tasks = repo.get_tasks_for_user(TEST_USER_ID)

        assert len(tasks) == 1
        assert tasks[0]["_id"] == task_id
        assert tasks[0]["text"] == "Buy groceries"
        assert tasks[0]["status"] == "pending"
        assert tasks[0]["due_at"].replace(tzinfo=None) == due.replace(tzinfo=None)

    def test_get_due_tasks(self, repo):
        past = datetime(2025, 1, 1, tzinfo=timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)

        repo.create(TEST_USER_ID, TEST_CHAT_ID, "Past task", past)
        repo.create(TEST_USER_ID, TEST_CHAT_ID, "Future task", future)

        now = datetime(2025, 6, 1, tzinfo=timezone.utc)
        due_tasks = repo.get_due_tasks(now)

        texts = [t["text"] for t in due_tasks]
        assert "Past task" in texts
        assert "Future task" not in texts

    def test_mark_completed(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Complete me", due)

        repo.mark_completed(task_id)

        tasks = repo.get_tasks_for_user(TEST_USER_ID, status="completed")
        assert len(tasks) == 1
        assert tasks[0]["status"] == "completed"
        assert tasks[0].get("completed_at") is not None

    def test_completed_tasks_not_returned_as_due(self, repo):
        past = datetime(2025, 1, 1, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Done task", past)
        repo.mark_completed(task_id)

        due_tasks = repo.get_due_tasks(datetime(2025, 6, 1, tzinfo=timezone.utc))
        assert len(due_tasks) == 0

    def test_delete(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Delete me", due)

        deleted = repo.delete(task_id)

        assert deleted is True
        assert repo.get_tasks_for_user(TEST_USER_ID) == []

    def test_delete_nonexistent(self, repo):
        deleted = repo.delete("nonexistent-id")
        assert deleted is False

    def test_filter_by_status(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        repo.create(TEST_USER_ID, TEST_CHAT_ID, "Pending task", due)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Completed task", due)
        repo.mark_completed(task_id)

        pending = repo.get_tasks_for_user(TEST_USER_ID, status="pending")
        completed = repo.get_tasks_for_user(TEST_USER_ID, status="completed")

        assert len(pending) == 1
        assert pending[0]["text"] == "Pending task"
        assert len(completed) == 1
        assert completed[0]["text"] == "Completed task"

    def test_user_isolation(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        repo.create("user_A", TEST_CHAT_ID, "A's task", due)
        repo.create("user_B", TEST_CHAT_ID, "B's task", due)

        tasks_a = repo.get_tasks_for_user("user_A")
        tasks_b = repo.get_tasks_for_user("user_B")

        assert len(tasks_a) == 1
        assert tasks_a[0]["text"] == "A's task"
        assert len(tasks_b) == 1
        assert tasks_b[0]["text"] == "B's task"

    def test_tasks_sorted_by_due_at(self, repo):
        base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo.create(TEST_USER_ID, TEST_CHAT_ID, "Third", base + timedelta(days=60))
        repo.create(TEST_USER_ID, TEST_CHAT_ID, "First", base)
        repo.create(TEST_USER_ID, TEST_CHAT_ID, "Second", base + timedelta(days=30))

        tasks = repo.get_tasks_for_user(TEST_USER_ID)

        assert [t["text"] for t in tasks] == ["First", "Second", "Third"]
