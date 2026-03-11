import os
import telegram
from telegram import Update
from telegram.ext import (
    CommandHandler,
    Application,
    ContextTypes,
    MessageHandler,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    test = 'Wellcome'
    await context.bot.send_message(chat_id=user_id, text=test)


async def bot_participation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        reply_to_message_id=update.message.message_id,
        text='responce result',
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
