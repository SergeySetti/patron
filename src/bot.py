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
    welcome_text = (
        "Meet *Patron* — the AI-powered personal assistant that lives inside Telegram.\n"
        "\n"
        "\U0001f9e0 *Your memory, supercharged.*\n"
        "We forget things. Patron doesn't. Tell it anything — a business idea at 2am, "
        "a book recommendation from a friend, a recipe you stumbled upon — and it stores "
        "it with deep semantic understanding. Weeks later, ask \"what was that startup idea "
        "about logistics?\" and Patron pulls up exactly what you said. No folders. No tags. Just ask.\n"
        "\n"
        "\u2705 *Tasks without the task app.*\n"
        "Say \"remind me to renew my domain on March 20th\" and it's done. Patron understands "
        "natural language, handles timezones automatically, and nudges you right in Telegram "
        "when the moment comes. No separate app to check, no notifications to configure.\n"
        "\n"
        "\U0001f517 *Context that carries over.*\n"
        "Unlike basic chatbots that forget you after each message, Patron maintains a continuous "
        "conversation. It knows your timezone, your preferences, and builds a picture of what "
        "matters to you over time.\n"
        "\n"
        "\U0001f4ac *Why Telegram?*\n"
        "Because it's where you already are. No new app to download, no new habit to build. "
        "Just open a chat and start talking to the smartest assistant you've ever had."
    )
    await context.bot.send_message(
        chat_id=user_id, text=welcome_text, parse_mode="Markdown"
    )


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
