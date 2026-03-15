from __future__ import annotations

import uuid
from datetime import datetime, timezone

from injector import inject
from pymongo import MongoClient
from pymongo.collection import Collection


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
    ) -> str:
        """Create a task and return its id."""
        task_id = str(uuid.uuid4())
        self._collection.insert_one(
            {
                "_id": task_id,
                "user_id": user_id,
                "chat_id": chat_id,
                "text": text,
                "due_at": due_at,
                "status": "pending",
                "created_at": datetime.now(timezone.utc),
            }
        )
        return task_id

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
