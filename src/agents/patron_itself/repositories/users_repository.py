from __future__ import annotations

from injector import inject
from pymongo import MongoClient
from pymongo.collection import Collection


class UsersRepository:

    @inject
    def __init__(self, mongo_client: MongoClient):
        db = mongo_client.get_database("patron_users")
        self._collection: Collection = db.get_collection("users")
        self._ensure_indexes()

    def _ensure_indexes(self):
        self._collection.create_index("user_id", unique=True)

    def get(self, user_id: str) -> dict | None:
        """Return user data or None if not found."""
        return self._collection.find_one({"user_id": user_id})

    def get_timezone(self, user_id: str) -> str | None:
        """Return the user's timezone string (e.g. 'Europe/London') or None."""
        user = self._collection.find_one({"user_id": user_id}, {"timezone": 1})
        if user:
            return user.get("timezone")
        return None

    def set_timezone(self, user_id: str, timezone: str) -> None:
        """Create or update the user's timezone."""
        self._collection.update_one(
            {"user_id": user_id},
            {"$set": {"timezone": timezone}},
            upsert=True,
        )
