import os
import telegram
from telegram import Update
from telegram.ext import (
    CommandHandler,
    Application,
    ContextTypes,
    MessageHandler,
)

from dependencies import app_container, AssistantLogger
from agents.patron_itself.patron_agent import run_agent
from task_scheduler import check_due_tasks

logger = app_container.get(AssistantLogger)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    test = 'Wellcome'
    await context.bot.send_message(chat_id=user_id, text=test)


async def bot_participation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    chat_id = str(update.message.chat_id)

    logger.info(f"User message: {user_message}")

    response = await run_agent(user_message, user_id, chat_id)
    agent_reply = response['messages'][-1].content[-1]["text"]

    logger.info(f"Agent reply: {agent_reply}")

    await context.bot.send_message(
        chat_id=update.message.chat_id,
        reply_to_message_id=update.message.message_id,
        text=agent_reply,
    )


def main() -> None:

    logger.info("Starting Telegram bot...")
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(
        MessageHandler(telegram.ext.filters.TEXT, bot_participation)
    )

    # Schedule task checker to run every 60 seconds
    application.job_queue.run_repeating(check_due_tasks, interval=60, first=10)
    logger.info("Task scheduler started (checking every 60s)")

    logger.info("Bot is polling for updates...")
    application.run_polling()


if __name__ == "__main__":
    main()
