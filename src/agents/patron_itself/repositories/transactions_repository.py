from __future__ import annotations

from datetime import datetime, timezone

from injector import inject
from pymongo import MongoClient
from pymongo.collection import Collection


class TransactionsRepository:

    @inject
    def __init__(self, mongo_client: MongoClient):
        db = mongo_client.get_database("patron_users")
        self._collection: Collection = db.get_collection("transactions")
        self._ensure_indexes()

    def _ensure_indexes(self):
        self._collection.create_index("user_id")
        self._collection.create_index("telegram_payment_charge_id", unique=True)

    def create(
        self,
        user_id: str,
        telegram_payment_charge_id: str,
        provider_payment_charge_id: str,
        total_amount: int,
        currency: str = "XTR",
        is_recurring: bool = False,
    ) -> str:
        """Record a successful payment transaction. Returns the inserted id."""
        doc = {
            "user_id": user_id,
            "telegram_payment_charge_id": telegram_payment_charge_id,
            "provider_payment_charge_id": provider_payment_charge_id,
            "total_amount": total_amount,
            "currency": currency,
            "is_recurring": is_recurring,
            "created_at": datetime.now(timezone.utc),
        }
        result = self._collection.insert_one(doc)
        return str(result.inserted_id)

    def get_by_user(self, user_id: str) -> list[dict]:
        """Return all transactions for a user, newest first."""
        return list(
            self._collection.find({"user_id": user_id}).sort("created_at", -1)
        )

    def get_by_charge_id(self, telegram_payment_charge_id: str) -> dict | None:
        """Find a transaction by its Telegram charge ID."""
        return self._collection.find_one(
            {"telegram_payment_charge_id": telegram_payment_charge_id}
        )
