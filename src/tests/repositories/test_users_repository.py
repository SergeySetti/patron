import pytest

from agents.patron_itself.repositories.users_repository import UsersRepository

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
