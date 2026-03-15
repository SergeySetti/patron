from datetime import datetime

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from agents.patron_itself.repositories.tasks_repository import TasksRepository


def create_task_tools(repo: TasksRepository) -> list:
    """Create task-management tools bound to a TasksRepository instance."""

    @tool
    def create_task(
        text: str,
        due_at: datetime,
        user_id: Annotated[str, InjectedState("user_id")],
        chat_id: Annotated[str, InjectedState("chat_id")],
    ) -> str:
        """Create a scheduled task for the user.

        The task text describes what needs to be done or reminded about.
        When the due_at time arrives, the system will read the task,
        decide what action to take, and message the user accordingly.

        Args:
            text: Description of the task or reminder.
            due_at: When the task should be executed (ISO datetime).
        """
        task_id = repo.create(user_id, chat_id, text, due_at)
        return f"Task created (id: {task_id}, due: {due_at.isoformat()})"

    @tool
    def list_tasks(
        user_id: Annotated[str, InjectedState("user_id")],
        status: str | None = None,
    ) -> list[dict]:
        """List the user's tasks, optionally filtered by status ('pending' or 'completed')."""
        tasks = repo.get_tasks_for_user(user_id, status=status)
        return [
            {
                "id": t["_id"],
                "text": t["text"],
                "due_at": t["due_at"].isoformat() if t.get("due_at") else None,
                "status": t["status"],
            }
            for t in tasks
        ]

    @tool
    def delete_task(
        task_id: str,
        user_id: Annotated[str, InjectedState("user_id")],
    ) -> str:
        """Delete a task by its id."""
        deleted = repo.delete(task_id)
        if deleted:
            return f"Task {task_id} deleted"
        return f"Task {task_id} not found"

    return [create_task, list_tasks, delete_task]
