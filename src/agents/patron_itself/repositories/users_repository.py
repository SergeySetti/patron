from __future__ import annotations

from datetime import datetime, timezone, timedelta

from injector import inject
from pymongo import MongoClient
from pymongo.collection import Collection

SUBSCRIPTION_DURATION = timedelta(days=30)
TRIAL_DURATION = timedelta(days=14)


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
            {"$set": {"timezone": timezone},
             "$setOnInsert": {"created_at": _utcnow()}},
            upsert=True,
        )

    def get_custom_prompt(self, user_id: str) -> str | None:
        """Return the user's custom system prompt section, or None."""
        user = self._collection.find_one(
            {"user_id": user_id}, {"custom_prompt": 1}
        )
        if user:
            return user.get("custom_prompt")
        return None

    def set_custom_prompt(self, user_id: str, custom_prompt: str) -> None:
        """Create or update the user's custom system prompt section."""
        self._collection.update_one(
            {"user_id": user_id},
            {"$set": {"custom_prompt": custom_prompt},
             "$setOnInsert": {"created_at": _utcnow()}},
            upsert=True,
        )

    def clear_custom_prompt(self, user_id: str) -> None:
        """Remove the user's custom system prompt section."""
        self._collection.update_one(
            {"user_id": user_id},
            {"$unset": {"custom_prompt": ""}},
        )

    def set_username(self, user_id: str, username: str | None) -> None:
        """Store the Telegram username for the user."""
        self._collection.update_one(
            {"user_id": user_id},
            {"$set": {"username": username},
             "$setOnInsert": {"created_at": _utcnow()}},
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

    def start_trial(self, user_id: str) -> datetime | None:
        """Grant a 14-day free trial if the user has never had a subscription.

        Returns the trial expiry datetime, or None if the user already has
        (or had) a subscription.
        """
        user = self._collection.find_one(
            {"user_id": user_id}, {"subscription_expires_at": 1}
        )
        if user and user.get("subscription_expires_at") is not None:
            return None  # already had a subscription or trial

        trial_expires = _utcnow() + TRIAL_DURATION
        self._collection.update_one(
            {"user_id": user_id},
            {"$set": {"subscription_expires_at": trial_expires},
             "$setOnInsert": {"created_at": _utcnow()}},
            upsert=True,
        )
        return trial_expires

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
            {"$set": {"subscription_expires_at": new_expires},
             "$setOnInsert": {"created_at": _utcnow()}},
            upsert=True,
        )
        return new_expires
