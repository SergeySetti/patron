from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from agents.patron_itself.repositories.users_repository import UsersRepository, SUBSCRIPTION_DURATION

TEST_USER_ID = "test_user_42"


@pytest.fixture()
def repo(test_container):
    repo = test_container.get(UsersRepository)
    yield repo
    repo._collection.drop()


class TestUsersRepository:

    def test_get_timezone_returns_none_for_new_user(self, repo):
        assert repo.get_timezone(TEST_USER_ID) is None

    def test_set_and_get_timezone(self, repo):
        repo.set_timezone(TEST_USER_ID, "Europe/London")

        assert repo.get_timezone(TEST_USER_ID) == "Europe/London"

    def test_set_timezone_updates_existing(self, repo):
        repo.set_timezone(TEST_USER_ID, "Europe/London")
        repo.set_timezone(TEST_USER_ID, "America/New_York")

        assert repo.get_timezone(TEST_USER_ID) == "America/New_York"

    def test_get_returns_none_for_unknown_user(self, repo):
        assert repo.get("unknown_user") is None

    def test_get_returns_user_data(self, repo):
        repo.set_timezone(TEST_USER_ID, "Asia/Tokyo")

        user = repo.get(TEST_USER_ID)

        assert user is not None
        assert user["user_id"] == TEST_USER_ID
        assert user["timezone"] == "Asia/Tokyo"

    def test_user_isolation(self, repo):
        repo.set_timezone("user_A", "Europe/Berlin")
        repo.set_timezone("user_B", "US/Pacific")

        assert repo.get_timezone("user_A") == "Europe/Berlin"
        assert repo.get_timezone("user_B") == "US/Pacific"


MOCK_UTCNOW = "agents.patron_itself.repositories.users_repository._utcnow"


class TestSubscription:

    def test_get_subscription_status_returns_none_for_new_user(self, repo):
        assert repo.get_subscription_status(TEST_USER_ID) is None

    def test_extend_subscription_from_scratch(self, repo):
        now = datetime(2025, 6, 1, tzinfo=timezone.utc)
        with patch(MOCK_UTCNOW, return_value=now):
            new_expires = repo.extend_subscription(TEST_USER_ID)

        assert new_expires == now + SUBSCRIPTION_DURATION

    def test_extend_subscription_stacks_on_active(self, repo):
        now = datetime(2025, 6, 1, tzinfo=timezone.utc)
        existing_expires = now + timedelta(days=15)  # 15 days left

        repo._collection.update_one(
            {"user_id": TEST_USER_ID},
            {"$set": {"subscription_expires_at": existing_expires}},
            upsert=True,
        )

        with patch(MOCK_UTCNOW, return_value=now):
            new_expires = repo.extend_subscription(TEST_USER_ID)

        # Should stack: 15 remaining + 30 new = 45 days from now
        assert new_expires == existing_expires + SUBSCRIPTION_DURATION

    def test_extend_subscription_resets_if_expired(self, repo):
        now = datetime(2025, 6, 1, tzinfo=timezone.utc)
        expired = now - timedelta(days=5)

        repo._collection.update_one(
            {"user_id": TEST_USER_ID},
            {"$set": {"subscription_expires_at": expired}},
            upsert=True,
        )

        with patch(MOCK_UTCNOW, return_value=now):
            new_expires = repo.extend_subscription(TEST_USER_ID)

        assert new_expires == now + SUBSCRIPTION_DURATION

    def test_active_subscription_returns_active_status(self, repo):
        now = datetime(2025, 6, 1, tzinfo=timezone.utc)
        future = now + timedelta(days=10)
        repo._collection.update_one(
            {"user_id": TEST_USER_ID},
            {"$set": {"subscription_expires_at": future}},
            upsert=True,
        )

        with patch(MOCK_UTCNOW, return_value=now):
            assert repo.get_subscription_status(TEST_USER_ID) == "active"

    def test_expired_subscription_returns_none_status(self, repo):
        now = datetime(2025, 6, 1, tzinfo=timezone.utc)
        past = now - timedelta(days=1)
        repo._collection.update_one(
            {"user_id": TEST_USER_ID},
            {"$set": {"subscription_expires_at": past}},
            upsert=True,
        )

        with patch(MOCK_UTCNOW, return_value=now):
            assert repo.get_subscription_status(TEST_USER_ID) is None

    def test_subscription_does_not_affect_timezone(self, repo):
        repo.set_timezone(TEST_USER_ID, "Europe/London")
        repo.extend_subscription(TEST_USER_ID)

        assert repo.get_timezone(TEST_USER_ID) == "Europe/London"
        assert repo.get_subscription_status(TEST_USER_ID) == "active"
