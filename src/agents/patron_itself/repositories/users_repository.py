from __future__ import annotations

from datetime import datetime, timezone, timedelta

from injector import inject
from pymongo import MongoClient
from pymongo.collection import Collection

SUBSCRIPTION_DURATION = timedelta(days=30)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC). Needed because some
    backends (e.g. mongomock) strip tzinfo on round-trip."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


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

    def get_subscription_status(self, user_id: str) -> str | None:
        """Return 'active' if subscription hasn't expired, else None."""
        expires = self.get_subscription_expires_at(user_id)
        if expires and _make_aware(expires) > _utcnow():
            return "active"
        return None

    def get_subscription_expires_at(self, user_id: str) -> datetime | None:
        """Return the subscription expiry datetime or None."""
        user = self._collection.find_one(
            {"user_id": user_id}, {"subscription_expires_at": 1}
        )
        if user:
            return user.get("subscription_expires_at")
        return None

    def extend_subscription(self, user_id: str) -> datetime:
        """Add 30 days to the subscription, stacking on remaining time.

        Returns the new expiry datetime.
        """
        now = _utcnow()
        current_expires = self.get_subscription_expires_at(user_id)

        # Stack on remaining time if still active, otherwise start from now
        if current_expires and _make_aware(current_expires) > now:
            base = _make_aware(current_expires)
        else:
            base = now
        new_expires = base + SUBSCRIPTION_DURATION

        self._collection.update_one(
            {"user_id": user_id},
            {"$set": {"subscription_expires_at": new_expires}},
            upsert=True,
        )
        return new_expires
