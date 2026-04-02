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
                "user_timezone": "Europe/Kyiv",
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
                "user_timezone": "Europe/Kyiv",
            }
        )

        tasks = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv"})

        assert len(tasks) == 1
        assert tasks[0]["text"] == "Buy milk"
        assert tasks[0]["status"] == "pending"

    def test_creates_recurring_task(self, tools):
        result = tools["create_task"].invoke(
            {
                "text": "Daily standup",
                "due_at": "2025-06-01T09:00:00+00:00",
                "recurrence": "0 9 * * *",
                "user_id": USER_ID,
                "chat_id": CHAT_ID,
                "user_timezone": "Europe/Kyiv",
            }
        )

        assert "Task created" in result
        assert "recurrence: 0 9 * * *" in result

    def test_recurring_task_shows_recurrence_in_list(self, tools):
        tools["create_task"].invoke(
            {
                "text": "Weekly review",
                "due_at": "2025-06-02T10:00:00+00:00",
                "recurrence": "0 10 * * 1",
                "user_id": USER_ID,
                "chat_id": CHAT_ID,
                "user_timezone": "Europe/Kyiv",
            }
        )

        tasks = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv"})

        assert len(tasks) == 1
        assert tasks[0]["recurrence"] == "0 10 * * 1"

    def test_one_off_task_has_no_recurrence_in_list(self, tools):
        tools["create_task"].invoke(
            {
                "text": "One-off task",
                "due_at": "2025-06-01T12:00:00+00:00",
                "user_id": USER_ID,
                "chat_id": CHAT_ID,
                "user_timezone": "Europe/Kyiv",
            }
        )

        tasks = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv"})

        assert "recurrence" not in tasks[0]

    def test_creates_task_with_special_instructions(self, tools):
        tools["create_task"].invoke(
            {
                "text": "Morning workout",
                "due_at": "2025-06-01T07:00:00+00:00",
                "special_instructions_for_agent": "Include exercises from stored plan",
                "user_id": USER_ID,
                "chat_id": CHAT_ID,
                "user_timezone": "Europe/Kyiv",
            }
        )

        tasks = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv"})

        assert len(tasks) == 1
        assert tasks[0]["special_instructions_for_agent"] == (
            "Include exercises from stored plan"
        )


class TestUpdateTask:

    def test_update_text(self, tools, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(USER_ID, CHAT_ID, "Old text", due)

        result = tools["update_task"].invoke(
            {"task_id": task_id, "text": "New text", "user_id": USER_ID, "user_timezone": "Europe/Kyiv"}
        )

        assert "updated" in result
        tasks = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv"})
        assert tasks[0]["text"] == "New text"

    def test_update_due_at(self, tools, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(USER_ID, CHAT_ID, "Task", due)

        result = tools["update_task"].invoke(
            {
                "task_id": task_id,
                "due_at": "2025-07-01T12:00:00+00:00",
                "user_id": USER_ID,
                "user_timezone": "Europe/Kyiv",
            }
        )

        assert "updated" in result

    def test_update_add_recurrence(self, tools, repo):
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(USER_ID, CHAT_ID, "Task", due)

        tools["update_task"].invoke(
            {
                "task_id": task_id,
                "recurrence": "0 9 * * *",
                "user_id": USER_ID,
                "user_timezone": "Europe/Kyiv",
            }
        )

        tasks = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv"})
        assert tasks[0]["recurrence"] == "0 9 * * *"

    def test_update_remove_recurrence(self, tools, repo):
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(
            USER_ID, CHAT_ID, "Task", due, recurrence="0 9 * * *",
        )

        tools["update_task"].invoke(
            {
                "task_id": task_id,
                "remove_recurrence": True,
                "user_id": USER_ID,
                "user_timezone": "Europe/Kyiv",
            }
        )

        tasks = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv"})
        assert "recurrence" not in tasks[0]

    def test_update_special_instructions(self, tools, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(USER_ID, CHAT_ID, "Task", due)

        tools["update_task"].invoke(
            {
                "task_id": task_id,
                "special_instructions_for_agent": "Be motivational",
                "user_id": USER_ID,
                "user_timezone": "Europe/Kyiv",
            }
        )

        tasks = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv"})
        assert tasks[0]["special_instructions_for_agent"] == "Be motivational"

    def test_update_remove_special_instructions(self, tools, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(
            USER_ID, CHAT_ID, "Task", due,
            special_instructions_for_agent="Be brief",
        )

        tools["update_task"].invoke(
            {
                "task_id": task_id,
                "remove_special_instructions": True,
                "user_id": USER_ID,
                "user_timezone": "Europe/Kyiv",
            }
        )

        tasks = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv"})
        assert "special_instructions_for_agent" not in tasks[0]

    def test_update_nonexistent(self, tools):
        result = tools["update_task"].invoke(
            {"task_id": "nope", "text": "New", "user_id": USER_ID, "user_timezone": "Europe/Kyiv"}
        )
        assert "not found" in result

    def test_update_no_fields(self, tools, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(USER_ID, CHAT_ID, "Task", due)

        result = tools["update_task"].invoke(
            {"task_id": task_id, "user_id": USER_ID, "user_timezone": "Europe/Kyiv"}
        )

        assert "Nothing to update" in result


class TestListTasks:

    def test_filters_by_status(self, tools, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        repo.create(USER_ID, CHAT_ID, "Pending one", due)
        task_id = repo.create(USER_ID, CHAT_ID, "Done one", due)
        repo.mark_completed(task_id)

        pending = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv", "status": "pending"})
        completed = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv", "status": "completed"})

        assert len(pending) == 1
        assert pending[0]["text"] == "Pending one"
        assert len(completed) == 1
        assert completed[0]["text"] == "Done one"

    def test_empty_list(self, tools):
        tasks = tools["list_tasks"].invoke({"user_id": USER_ID, "user_timezone": "Europe/Kyiv"})
        assert tasks == []


class TestDeleteTask:

    def test_deletes_task(self, tools, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(USER_ID, CHAT_ID, "To delete", due)

        result = tools["delete_task"].invoke({"task_id": task_id, "user_id": USER_ID, "user_timezone": "Europe/Kyiv"})

        assert "deleted" in result
        assert repo.get_tasks_for_user(USER_ID) == []

    def test_delete_nonexistent(self, tools):
        result = tools["delete_task"].invoke({"task_id": "nope", "user_id": USER_ID, "user_timezone": "Europe/Kyiv"})
        assert "not found" in result

    def test_delete_stops_recurring(self, tools, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(
            USER_ID, CHAT_ID, "Recurring", due, recurrence="0 9 * * *",
        )

        result = tools["delete_task"].invoke({"task_id": task_id, "user_id": USER_ID, "user_timezone": "Europe/Kyiv"})

        assert "deleted" in result
        assert repo.get_tasks_for_user(USER_ID) == []
