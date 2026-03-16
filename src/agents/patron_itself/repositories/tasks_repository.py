from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from croniter import croniter
from injector import inject
from pymongo import MongoClient
from pymongo.collection import Collection

MIN_RECURRENCE_INTERVAL = timedelta(hours=1)

_NOT_PROVIDED = object()


def _validate_recurrence(cron_expr: str) -> None:
    """Raise ValueError if the cron expression is invalid or fires
    more often than once per hour."""
    if not croniter.is_valid(cron_expr):
        raise ValueError(f"Invalid cron expression: {cron_expr}")

    # Check minimum interval by computing two consecutive firings
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    cron = croniter(cron_expr, base)
    first = cron.get_next(datetime)
    second = cron.get_next(datetime)
    if (second - first) < MIN_RECURRENCE_INTERVAL:
        raise ValueError(
            f"Recurrence too frequent: interval is {second - first}. "
            f"Minimum allowed is {MIN_RECURRENCE_INTERVAL}."
        )


class TasksRepository:

    @inject
    def __init__(self, mongo_client: MongoClient):
        db = mongo_client.get_database("patron_tasks")
        self._collection: Collection = db.get_collection("tasks")
        self._ensure_indexes()

    def _ensure_indexes(self):
        self._collection.create_index("user_id")
        self._collection.create_index([("due_at", 1), ("status", 1)])

    def create(
        self,
        user_id: str,
        chat_id: str,
        text: str,
        due_at: datetime,
        recurrence: str | None = None,
        special_instructions_for_agent: str | None = None,
    ) -> str:
        """Create a task and return its id.

        Args:
            user_id: Owner of the task.
            chat_id: Telegram chat where reminders are sent.
            text: Description of the task.
            due_at: When the task should fire (UTC).
            recurrence: Optional cron expression (e.g. ``"0 9 * * *"``
                for every day at 09:00 UTC). When set, the task
                automatically reschedules after each execution.
                Minimum interval: 1 hour.
            special_instructions_for_agent: Optional instructions that
                tell the agent *how* to handle the task when it fires
                (e.g. tone, format, extra context). Not shown to the
                user directly — only consumed by the agent.
        """
        if recurrence is not None:
            _validate_recurrence(recurrence)

        task_id = str(uuid.uuid4())
        doc: dict = {
            "_id": task_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "text": text,
            "due_at": due_at,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
        }
        if recurrence is not None:
            doc["recurrence"] = recurrence
        if special_instructions_for_agent is not None:
            doc["special_instructions_for_agent"] = special_instructions_for_agent

        self._collection.insert_one(doc)
        return task_id

    def update(
        self,
        task_id: str,
        text: str | None = None,
        due_at: datetime | None = None,
        recurrence=_NOT_PROVIDED,
        special_instructions_for_agent=_NOT_PROVIDED,
    ) -> bool:
        """Update fields on an existing task.

        Only provided (non-default) fields are changed. Pass ``None``
        explicitly for ``recurrence`` or
        ``special_instructions_for_agent`` to remove them.

        Returns True if the task was found and updated.
        """
        sets: dict = {}
        unsets: dict = {}

        if text is not None:
            sets["text"] = text
        if due_at is not None:
            sets["due_at"] = due_at

        if recurrence is not _NOT_PROVIDED:
            if recurrence is None:
                unsets["recurrence"] = ""
            else:
                _validate_recurrence(recurrence)
                sets["recurrence"] = recurrence

        if special_instructions_for_agent is not _NOT_PROVIDED:
            if special_instructions_for_agent is None:
                unsets["special_instructions_for_agent"] = ""
            else:
                sets["special_instructions_for_agent"] = (
                    special_instructions_for_agent
                )

        if not sets and not unsets:
            return False

        update_doc: dict = {}
        if sets:
            update_doc["$set"] = sets
        if unsets:
            update_doc["$unset"] = unsets

        result = self._collection.update_one({"_id": task_id}, update_doc)
        return result.matched_count > 0

    def get_due_tasks(self, now: datetime | None = None) -> list[dict]:
        """Return all pending tasks whose due_at <= now."""
        if now is None:
            now = datetime.now(timezone.utc)
        cursor = self._collection.find(
            {"status": "pending", "due_at": {"$lte": now}}
        )
        return list(cursor)

    def mark_completed(self, task_id: str) -> None:
        self._collection.update_one(
            {"_id": task_id},
            {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc)}},
        )

    def reschedule(self, task_id: str) -> datetime | None:
        """Advance a recurring task to its next occurrence.

        If the task has a ``recurrence`` cron expression the next due_at
        is computed and the task stays ``pending``. Returns the new
        due_at, or ``None`` if the task is not recurring.
        """
        task = self._collection.find_one({"_id": task_id})
        if not task or "recurrence" not in task:
            return None

        cron = croniter(task["recurrence"], task["due_at"])
        next_due = cron.get_next(datetime)
        # croniter may strip tzinfo — ensure UTC
        if next_due.tzinfo is None:
            next_due = next_due.replace(tzinfo=timezone.utc)

        self._collection.update_one(
            {"_id": task_id},
            {"$set": {"due_at": next_due, "status": "pending"}},
        )
        return next_due

    def get_tasks_for_user(self, user_id: str, status: str | None = None) -> list[dict]:
        """Return tasks for a user, optionally filtered by status."""
        query: dict = {"user_id": user_id}
        if status is not None:
            query["status"] = status
        return list(self._collection.find(query).sort("due_at", 1))

    def delete(self, task_id: str) -> bool:
        """Delete a task. Returns True if deleted."""
        result = self._collection.delete_one({"_id": task_id})
        return result.deleted_count > 0
