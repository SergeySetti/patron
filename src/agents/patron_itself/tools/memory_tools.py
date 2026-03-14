from datetime import datetime

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from agents.patron_itself.repositories.memories_repository import MemoriesRepository


def create_memory_tools(repo: MemoriesRepository) -> list:
    """Create memory tools bound to a MemoriesRepository instance."""

    @tool
    def add_memory(
        text: str,
        user_id: Annotated[str, InjectedState("user_id")],
        metadata: dict | None = None,
    ) -> str:
        """Save a new memory for the user. Use this to remember facts, preferences, or anything the user asks you to remember."""
        point_id = repo.save(user_id, text, metadata=metadata)
        return f"Memory saved (id: {point_id})"

    @tool
    def recall_memories_by_semantic_query(
        query: str,
        user_id: Annotated[str, InjectedState("user_id")],
        limit: int = 5,
    ) -> list[dict]:
        """Search user memories by meaning. Use this when the user asks you to recall or remember something."""
        return repo.search(user_id, query, limit=limit)

    @tool
    def recall_memories_by_time_constraints(
        user_id: Annotated[str, InjectedState("user_id")],
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        """Find user memories within a date range. Both bounds are optional and inclusive."""
        return repo.find_by_date_range(user_id, date_from=date_from, date_to=date_to)

    @tool
    def delete_memory(
        memory_id: str,
    ) -> str:
        """Delete a single memory by its id."""
        repo.delete(memory_id)
        return f"Memory {memory_id} deleted"

    return [add_memory, recall_memories_by_semantic_query, recall_memories_by_time_constraints, delete_memory]
