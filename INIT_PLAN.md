# Project start plan

## Purpose

This is a prototype for Telegram bot as planning and remembering personal assistant. It remembers what needs to be remembered and schedule the reminders, recurrent events, tasks, goals, plans.

See .env for basic dependencies

For educational purposes this project uses Langchain as agentic framework. I still prefer Google ADK thou...

## Envs are

TELEGRAM_BOT_TOKEN=secret
MONGODB_URI=mongodb+srv://secret
MONGODB_DATABASE=patron
GOOGLE_API_KEY=secret
GOOGLE_GENAI_USE_VERTEXAI=False

## src/bot.py

* Create this file
* Boilerplate it like this

```python 
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
```
