from datetime import datetime, timezone

import pytest

from agents.patron_itself.repositories.tasks_repository import TasksRepository
from agents.patron_itself.tools.task_tools import create_task_tools

USER_ID = "tool_test_user"
CHAT_ID = "chat_456"


@pytest.fixture()
def repo(test_container):
    repo = test_container.get(TasksRepository)
    yield repo
    repo._collection.drop()


@pytest.fixture()
def tools(repo):
    return {t.name: t for t in create_task_tools(repo)}


class TestCreateTask:

    def test_creates_and_returns_id(self, tools):
        result = tools["create_task"].invoke(
            {
                "text": "Remind me to call Bob",
                "due_at": "2025-06-01T12:00:00+00:00",
                "user_id": USER_ID,
                "chat_id": CHAT_ID,
            }
        )

        assert "Task created" in result
        assert "id:" in result

    def test_task_appears_in_list(self, tools):
        tools["create_task"].invoke(
            {
                "text": "Buy milk",
                "due_at": "2025-06-01T12:00:00+00:00",
                "user_id": USER_ID,
                "chat_id": CHAT_ID,
            }
        )

        tasks = tools["list_tasks"].invoke({"user_id": USER_ID})

        assert len(tasks) == 1
        assert tasks[0]["text"] == "Buy milk"
        assert tasks[0]["status"] == "pending"


class TestListTasks:

    def test_filters_by_status(self, tools, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        repo.create(USER_ID, CHAT_ID, "Pending one", due)
        task_id = repo.create(USER_ID, CHAT_ID, "Done one", due)
        repo.mark_completed(task_id)

        pending = tools["list_tasks"].invoke({"user_id": USER_ID, "status": "pending"})
        completed = tools["list_tasks"].invoke({"user_id": USER_ID, "status": "completed"})

        assert len(pending) == 1
        assert pending[0]["text"] == "Pending one"
        assert len(completed) == 1
        assert completed[0]["text"] == "Done one"

    def test_empty_list(self, tools):
        tasks = tools["list_tasks"].invoke({"user_id": USER_ID})
        assert tasks == []


class TestDeleteTask:

    def test_deletes_task(self, tools, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(USER_ID, CHAT_ID, "To delete", due)

        result = tools["delete_task"].invoke({"task_id": task_id, "user_id": USER_ID})

        assert "deleted" in result
        assert repo.get_tasks_for_user(USER_ID) == []

    def test_delete_nonexistent(self, tools):
        result = tools["delete_task"].invoke({"task_id": "nope", "user_id": USER_ID})
        assert "not found" in result
