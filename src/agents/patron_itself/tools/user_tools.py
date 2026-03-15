from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from agents.patron_itself.repositories.users_repository import UsersRepository


def create_user_tools(repo: UsersRepository) -> list:
    """Create user-data tools bound to a UsersRepository instance."""

    @tool
    def get_user_timezone(
        user_id: Annotated[str, InjectedState("user_id")],
    ) -> str:
        """Get the user's stored timezone.

        Returns the IANA timezone string (e.g. 'Europe/London') or a message
        indicating no timezone is set. If no timezone is stored, you MUST ask
        the user for their current time so you can determine and save their timezone.
        """
        tz = repo.get_timezone(user_id)
        if tz:
            return f"User timezone: {tz}"
        return "No timezone set. Ask the user for their current time to determine their timezone."

    @tool
    def set_user_timezone(
        timezone: str,
        user_id: Annotated[str, InjectedState("user_id")],
    ) -> str:
        """Save or update the user's timezone.

        Use an IANA timezone name (e.g. 'America/New_York', 'Europe/Moscow').
        Call this after determining the user's timezone from their current time.

        Args:
            timezone: IANA timezone name.
        """
        repo.set_timezone(user_id, timezone)
        return f"Timezone set to {timezone}"

    return [get_user_timezone, set_user_timezone]
