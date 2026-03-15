from __future__ import annotations

import logging

from telegram.ext import ContextTypes

from agents.patron_itself.patron_agent import run_agent
from agents.patron_itself.repositories.tasks_repository import TasksRepository
from dependencies import app_container, AssistantLogger

logger: logging.Logger = app_container.get(AssistantLogger)


async def check_due_tasks(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback executed every minute by the job queue.

    Finds all pending tasks whose due_at has passed, runs the agent for
    each one, and sends the result to the user's chat.
    """
    tasks_repo = app_container.get(TasksRepository)
    due_tasks = tasks_repo.get_due_tasks()

    for task in due_tasks:
        task_id = task["_id"]
        user_id = task["user_id"]
        chat_id = task["chat_id"]
        task_text = task["text"]

        logger.info(f"Executing due task {task_id} for user {user_id}: {task_text}")

        try:
            tasks_repo.mark_completed(task_id)

            prompt = (
                f"The following scheduled task is now due. "
                f"Read it, decide what to do or answer, and respond accordingly:\n\n"
                f"{task_text}"
            )
            response = await run_agent(prompt, user_id, chat_id)
            agent_reply = response["messages"][-1].content[-1]["text"]

            await context.bot.send_message(chat_id=int(chat_id), text=agent_reply)
            logger.info(f"Task {task_id} executed and user notified")

        except Exception:
            logger.exception(f"Failed to execute task {task_id}")
