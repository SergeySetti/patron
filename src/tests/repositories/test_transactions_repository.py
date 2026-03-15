import pytest

from agents.patron_itself.repositories.transactions_repository import TransactionsRepository

TEST_USER_ID = "test_user_tx"


@pytest.fixture()
def repo(test_container):
    repo = test_container.get(TransactionsRepository)
    yield repo
    repo._collection.drop()


class TestTransactionsRepository:

    def test_create_and_get_by_user(self, repo):
        repo.create(
            user_id=TEST_USER_ID,
            telegram_payment_charge_id="tg_charge_1",
            provider_payment_charge_id="prov_1",
            total_amount=500,
        )

        txns = repo.get_by_user(TEST_USER_ID)

        assert len(txns) == 1
        assert txns[0]["user_id"] == TEST_USER_ID
        assert txns[0]["total_amount"] == 500
        assert txns[0]["currency"] == "XTR"

    def test_get_by_charge_id(self, repo):
        repo.create(
            user_id=TEST_USER_ID,
            telegram_payment_charge_id="tg_charge_2",
            provider_payment_charge_id="prov_2",
            total_amount=500,
        )

        txn = repo.get_by_charge_id("tg_charge_2")

        assert txn is not None
        assert txn["telegram_payment_charge_id"] == "tg_charge_2"

    def test_get_by_charge_id_returns_none(self, repo):
        assert repo.get_by_charge_id("nonexistent") is None

    def test_get_by_user_returns_empty_for_unknown(self, repo):
        assert repo.get_by_user("unknown_user") == []

    def test_multiple_transactions_ordered_newest_first(self, repo):
        from datetime import datetime, timezone, timedelta
        earlier = datetime(2025, 1, 1, tzinfo=timezone.utc)
        later = earlier + timedelta(days=30)

        # Insert older one first
        repo._collection.insert_one({
            "user_id": TEST_USER_ID,
            "telegram_payment_charge_id": "tg_first",
            "provider_payment_charge_id": "prov_first",
            "total_amount": 500,
            "currency": "XTR",
            "is_recurring": False,
            "created_at": earlier,
        })
        repo._collection.insert_one({
            "user_id": TEST_USER_ID,
            "telegram_payment_charge_id": "tg_second",
            "provider_payment_charge_id": "prov_second",
            "total_amount": 500,
            "currency": "XTR",
            "is_recurring": False,
            "created_at": later,
        })

        txns = repo.get_by_user(TEST_USER_ID)

        assert len(txns) == 2
        assert txns[0]["telegram_payment_charge_id"] == "tg_second"

    def test_is_recurring_flag(self, repo):
        repo.create(
            user_id=TEST_USER_ID,
            telegram_payment_charge_id="tg_rec",
            provider_payment_charge_id="prov_rec",
            total_amount=500,
            is_recurring=True,
        )

        txn = repo.get_by_charge_id("tg_rec")

        assert txn["is_recurring"] is True

    def test_user_isolation(self, repo):
        repo.create(
            user_id="user_A",
            telegram_payment_charge_id="tg_a",
            provider_payment_charge_id="prov_a",
            total_amount=500,
        )
        repo.create(
            user_id="user_B",
            telegram_payment_charge_id="tg_b",
            provider_payment_charge_id="prov_b",
            total_amount=500,
        )

        assert len(repo.get_by_user("user_A")) == 1
        assert len(repo.get_by_user("user_B")) == 1
