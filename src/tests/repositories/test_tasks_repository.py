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


class TestRecurrence:

    def test_create_recurring_task(self, repo):
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Daily standup",
            due, recurrence="0 9 * * *",
        )

        tasks = repo.get_tasks_for_user(TEST_USER_ID)

        assert len(tasks) == 1
        assert tasks[0]["recurrence"] == "0 9 * * *"
        assert tasks[0]["_id"] == task_id

    def test_create_with_invalid_cron_raises(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="Invalid cron expression"):
            repo.create(
                TEST_USER_ID, TEST_CHAT_ID, "Bad cron",
                due, recurrence="not a cron",
            )

    def test_create_with_too_frequent_cron_raises(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="Recurrence too frequent"):
            repo.create(
                TEST_USER_ID, TEST_CHAT_ID, "Every minute",
                due, recurrence="* * * * *",
            )

    def test_create_with_every_30_min_raises(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="Recurrence too frequent"):
            repo.create(
                TEST_USER_ID, TEST_CHAT_ID, "Every 30 min",
                due, recurrence="*/30 * * * *",
            )

    def test_create_with_hourly_allowed(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Hourly",
            due, recurrence="0 * * * *",
        )
        tasks = repo.get_tasks_for_user(TEST_USER_ID)
        assert tasks[0]["recurrence"] == "0 * * * *"

    def test_one_off_task_has_no_recurrence_field(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        repo.create(TEST_USER_ID, TEST_CHAT_ID, "One-off", due)

        tasks = repo.get_tasks_for_user(TEST_USER_ID)
        assert "recurrence" not in tasks[0]

    def test_reschedule_advances_due_at(self, repo):
        # Daily at 09:00 — first due June 1
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Daily",
            due, recurrence="0 9 * * *",
        )

        next_due = repo.reschedule(task_id)

        # Next occurrence: June 2 at 09:00
        assert next_due.replace(tzinfo=None) == datetime(2025, 6, 2, 9, 0, 0)

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert task["status"] == "pending"
        assert task["due_at"].replace(tzinfo=None) == datetime(2025, 6, 2, 9, 0, 0)

    def test_reschedule_returns_none_for_one_off(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "One-off", due)

        result = repo.reschedule(task_id)

        assert result is None

    def test_reschedule_returns_none_for_nonexistent(self, repo):
        result = repo.reschedule("nonexistent-id")
        assert result is None

    def test_reschedule_weekly(self, repo):
        # Every Monday at 10:00 — first due Monday June 2
        due = datetime(2025, 6, 2, 10, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Weekly review",
            due, recurrence="0 10 * * 1",
        )

        next_due = repo.reschedule(task_id)

        # Next Monday: June 9 at 10:00
        assert next_due.replace(tzinfo=None) == datetime(2025, 6, 9, 10, 0, 0)

    def test_reschedule_keeps_task_pending(self, repo):
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Recurring",
            due, recurrence="0 9 * * *",
        )

        repo.reschedule(task_id)

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert task["status"] == "pending"

    def test_recurring_task_stays_due_until_rescheduled(self, repo):
        """A recurring task past its due_at still shows up in get_due_tasks
        until explicitly rescheduled."""
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Daily",
            due, recurrence="0 9 * * *",
        )

        now = datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert len(repo.get_due_tasks(now)) == 1

        repo.reschedule(task_id)

        # After reschedule, next due is June 2 — no longer due at June 1 10:00
        assert len(repo.get_due_tasks(now)) == 0

    def test_delete_stops_recurring_task(self, repo):
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Recurring to delete",
            due, recurrence="0 9 * * *",
        )

        deleted = repo.delete(task_id)

        assert deleted is True
        assert repo.get_tasks_for_user(TEST_USER_ID) == []


class TestUpdate:

    def test_update_text(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Old text", due)

        found = repo.update(task_id, text="New text")

        assert found is True
        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert task["text"] == "New text"

    def test_update_due_at(self, repo):
        old_due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        new_due = datetime(2025, 7, 1, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Task", old_due)

        repo.update(task_id, due_at=new_due)

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert task["due_at"].replace(tzinfo=None) == new_due.replace(tzinfo=None)

    def test_update_add_recurrence(self, repo):
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Task", due)

        repo.update(task_id, recurrence="0 9 * * *")

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert task["recurrence"] == "0 9 * * *"

    def test_update_remove_recurrence(self, repo):
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Task",
            due, recurrence="0 9 * * *",
        )

        repo.update(task_id, recurrence=None)

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert "recurrence" not in task

    def test_update_recurrence_validates_frequency(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Task", due)

        with pytest.raises(ValueError, match="Recurrence too frequent"):
            repo.update(task_id, recurrence="* * * * *")

    def test_update_add_special_instructions(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Task", due)

        repo.update(
            task_id,
            special_instructions_for_agent="Reply in Ukrainian",
        )

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert task["special_instructions_for_agent"] == "Reply in Ukrainian"

    def test_update_remove_special_instructions(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Task", due,
            special_instructions_for_agent="Be brief",
        )

        repo.update(task_id, special_instructions_for_agent=None)

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert "special_instructions_for_agent" not in task

    def test_update_multiple_fields(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        new_due = datetime(2025, 7, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Old", due)

        repo.update(
            task_id,
            text="New",
            due_at=new_due,
            recurrence="0 9 * * *",
            special_instructions_for_agent="Motivational tone",
        )

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert task["text"] == "New"
        assert task["due_at"].replace(tzinfo=None) == new_due.replace(tzinfo=None)
        assert task["recurrence"] == "0 9 * * *"
        assert task["special_instructions_for_agent"] == "Motivational tone"

    def test_update_no_fields_returns_false(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(TEST_USER_ID, TEST_CHAT_ID, "Task", due)

        result = repo.update(task_id)

        assert result is False

    def test_update_nonexistent_returns_false(self, repo):
        result = repo.update("nonexistent-id", text="New text")

        assert result is False

    def test_update_preserves_other_fields(self, repo):
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Original",
            due, recurrence="0 9 * * *",
            special_instructions_for_agent="Be brief",
        )

        repo.update(task_id, text="Updated")

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert task["text"] == "Updated"
        assert task["recurrence"] == "0 9 * * *"
        assert task["special_instructions_for_agent"] == "Be brief"
        assert task["due_at"].replace(tzinfo=None) == due.replace(tzinfo=None)


class TestSpecialInstructions:

    def test_create_with_special_instructions(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        task_id = repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Morning checklist", due,
            special_instructions_for_agent="Reply in bullet points, motivational tone",
        )

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert task["special_instructions_for_agent"] == (
            "Reply in bullet points, motivational tone"
        )

    def test_one_off_task_has_no_special_instructions_field(self, repo):
        due = datetime(2025, 6, 1, tzinfo=timezone.utc)
        repo.create(TEST_USER_ID, TEST_CHAT_ID, "Plain task", due)

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert "special_instructions_for_agent" not in task

    def test_special_instructions_with_recurrence(self, repo):
        due = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
        repo.create(
            TEST_USER_ID, TEST_CHAT_ID, "Daily workout", due,
            recurrence="0 9 * * *",
            special_instructions_for_agent="Include today's exercises from the stored plan",
        )

        task = repo.get_tasks_for_user(TEST_USER_ID)[0]
        assert task["recurrence"] == "0 9 * * *"
        assert task["special_instructions_for_agent"] == (
            "Include today's exercises from the stored plan"
        )
