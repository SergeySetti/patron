from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from agents.patron_itself.repositories.tasks_repository import TasksRepository


def _local_to_utc(dt: datetime, tz_name: str) -> datetime:
    """Interpret a datetime as local time in the given timezone and convert to UTC."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    tz = ZoneInfo(tz_name)
    return dt.replace(tzinfo=tz).astimezone(timezone.utc)


def _utc_to_local(dt: datetime, tz_name: str) -> datetime:
    """Convert a UTC datetime to the user's local timezone."""
    tz = ZoneInfo(tz_name)
    return dt.astimezone(tz)


def create_task_tools(repo: TasksRepository) -> list:
    """Create task-management tools bound to a TasksRepository instance."""

    @tool
    def create_task(
            text: str,
            due_at: datetime,
            user_id: Annotated[str, InjectedState("user_id")],
            chat_id: Annotated[str, InjectedState("chat_id")],
            user_timezone: Annotated[str, InjectedState("user_timezone")],
            recurrence: str | None = None,
            special_instructions_for_agent: str | None = None,
    ) -> str:
        """Create a scheduled task for the user.

        The task text describes what needs to be done or reminded about.
        When the due_at time arrives, the system will read the task,
        decide what action to take, and message the user accordingly.

        For recurring tasks, provide a cron expression in ``recurrence``.
        The task will automatically reschedule after each execution.
        Minimum recurrence interval is 1 hour.

        Common cron patterns (in the user's local time):
          "0 9 * * *"     — every day at 09:00
          "0 9 * * 1"     — every Monday at 09:00
          "0 9 * * 1-5"   — weekdays at 09:00
          "0 */2 * * *"   — every 2 hours
          "30 8 1 * *"    — 1st of every month at 08:30

        Use ``special_instructions_for_agent`` to control *how* the
        agent should handle the task when it fires — e.g. response
        tone, format, language, or extra context the agent should
        consider. These instructions are consumed by the agent only,
        not shown to the user directly.

        Args:
            text: Description of the task or reminder.
            due_at: When the task should first execute (in user's local time).
            recurrence: Optional cron expression for repeating tasks.
            special_instructions_for_agent: Optional agent-facing
                instructions for handling this task.
        """
        if not user_timezone:
            return ("Cannot create task: user timezone is not set. "
                    "Ask the user for their current time and set the timezone first.")
        due_at_utc = _local_to_utc(due_at, user_timezone)
        task_id = repo.create(
            user_id, chat_id, text, due_at_utc,
            recurrence=recurrence,
            special_instructions_for_agent=special_instructions_for_agent,
        )
        msg = f"Task created (id: {task_id}, due: {due_at.isoformat()}"
        if recurrence:
            msg += f", recurrence: {recurrence}"
        msg += ")"
        return msg

    @tool
    def update_task(
            task_id: str,
            user_id: Annotated[str, InjectedState("user_id")],
            user_timezone: Annotated[str, InjectedState("user_timezone")],
            text: str | None = None,
            due_at: datetime | None = None,
            recurrence: str | None = None,
            remove_recurrence: bool = False,
            special_instructions_for_agent: str | None = None,
            remove_special_instructions: bool = False,
    ) -> str:
        """Update an existing task.

        Only the fields you provide will be changed; everything else
        stays the same.

        To **remove** recurrence (turn a recurring task into a one-off),
        set ``remove_recurrence=True``.  To **remove** the special
        instructions, set ``remove_special_instructions=True``.

        Args:
            task_id: The id of the task to update.
            text: New task description (optional).
            due_at: New due date/time in user's local time (optional).
            recurrence: New cron expression (optional, min interval 1h).
            remove_recurrence: Set True to remove recurrence.
            special_instructions_for_agent: New agent instructions (optional).
            remove_special_instructions: Set True to remove instructions.
        """
        kwargs: dict = {}
        if text is not None:
            kwargs["text"] = text
        if due_at is not None:
            if not user_timezone:
                return ("Cannot update due_at: user timezone is not set. "
                        "Ask the user for their current time and set the timezone first.")
            kwargs["due_at"] = _local_to_utc(due_at, user_timezone)

        if remove_recurrence:
            kwargs["recurrence"] = None
        elif recurrence is not None:
            kwargs["recurrence"] = recurrence

        if remove_special_instructions:
            kwargs["special_instructions_for_agent"] = None
        elif special_instructions_for_agent is not None:
            kwargs["special_instructions_for_agent"] = (
                special_instructions_for_agent
            )

        if not kwargs:
            return "Nothing to update — no fields provided."

        found = repo.update(task_id, **kwargs)
        if found:
            return f"Task {task_id} updated"
        return f"Task {task_id} not found"

    @tool
    def list_tasks(
            user_id: Annotated[str, InjectedState("user_id")],
            user_timezone: Annotated[str, InjectedState("user_timezone")],
            status: str | None = None,
    ) -> list[dict]:
        """List the user's tasks, optionally filtered by status ('pending' or 'completed').

        Times are returned in the user's local timezone."""
        tasks = repo.get_tasks_for_user(user_id, status=status)
        return [
            {
                "id": t["_id"],
                "text": t["text"],
                "due_at": (
                    _utc_to_local(t["due_at"], user_timezone).isoformat()
                    if t.get("due_at") and user_timezone
                    else (t["due_at"].isoformat() if t.get("due_at") else None)
                ),
                "status": t["status"],
                **({"recurrence": t["recurrence"]}
                   if "recurrence" in t else {}),
                **({"special_instructions_for_agent": t["special_instructions_for_agent"]}
                   if "special_instructions_for_agent" in t else {}),
            }
            for t in tasks
        ]

    @tool
    def delete_task(
            task_id: str,
            user_id: Annotated[str, InjectedState("user_id")],
    ) -> str:
        """Delete a task by its id. This also stops recurring tasks."""
        deleted = repo.delete(task_id)
        if deleted:
            return f"Task {task_id} deleted"
        return f"Task {task_id} not found"

    return [create_task, update_task, list_tasks, delete_task]
