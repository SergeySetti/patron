import pytest

from agents.patron_itself.repositories.users_repository import UsersRepository
from agents.patron_itself.tools.user_tools import create_user_tools

USER_ID = "tool_test_user"


@pytest.fixture()
def repo(test_container):
    repo = test_container.get(UsersRepository)
    yield repo
    repo._collection.drop()


@pytest.fixture()
def tools(repo):
    return {t.name: t for t in create_user_tools(repo)}


class TestGetUserTimezone:

    def test_returns_no_timezone_message_for_new_user(self, tools):
        result = tools["get_user_timezone"].invoke({"user_id": USER_ID})

        assert "No timezone set" in result

    def test_returns_timezone_when_set(self, tools, repo):
        repo.set_timezone(USER_ID, "Europe/Moscow")

        result = tools["get_user_timezone"].invoke({"user_id": USER_ID})

        assert "Europe/Moscow" in result


class TestSetUserTimezone:

    def test_sets_timezone(self, tools, repo):
        result = tools["set_user_timezone"].invoke(
            {"timezone": "America/Chicago", "user_id": USER_ID}
        )

        assert "America/Chicago" in result
        assert repo.get_timezone(USER_ID) == "America/Chicago"

    def test_updates_existing_timezone(self, tools, repo):
        repo.set_timezone(USER_ID, "Europe/London")

        tools["set_user_timezone"].invoke(
            {"timezone": "Asia/Tokyo", "user_id": USER_ID}
        )

        assert repo.get_timezone(USER_ID) == "Asia/Tokyo"
