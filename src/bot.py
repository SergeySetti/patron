import os
import telegram
from telegram import Update
from telegram.ext import (
    CommandHandler,
    Application,
    ContextTypes,
    MessageHandler,
)

from src.agents.patron_itself.patron_agent import run_agent


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    test = 'Wellcome'
    await context.bot.send_message(chat_id=user_id, text=test)


async def bot_participation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    chat_id = str(update.message.chat_id)

    response = await run_agent(user_message, user_id, chat_id)
    agent_reply = response['messages'][-1].content[-1]["text"]

    await context.bot.send_message(
        chat_id=update.message.chat_id,
        reply_to_message_id=update.message.message_id,
        text=agent_reply,
    )


def main() -> None:
    print("Starting Telegram bot...")
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(
        MessageHandler(telegram.ext.filters.TEXT, bot_participation)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
