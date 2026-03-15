import os
import telegram
from telegram import LabeledPrice, Update
from telegram.ext import (
    CommandHandler,
    Application,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
)

from dependencies import app_container, AssistantLogger
from agents.patron_itself.patron_agent import run_agent
from agents.patron_itself.repositories.users_repository import UsersRepository
from agents.patron_itself.repositories.transactions_repository import TransactionsRepository
from task_scheduler import check_due_tasks

SUBSCRIPTION_TITLE = "Patron Monthly"
SUBSCRIPTION_DESCRIPTION = "Monthly subscription to Patron AI assistant"
SUBSCRIPTION_PAYLOAD = "patron_monthly_500"
SUBSCRIPTION_PRICE = 2  # Telegram Stars
SUBSCRIPTION_PERIOD = 2592000  # 30 days in seconds

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


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a Telegram Stars invoice for the monthly subscription."""
    chat_id = update.effective_chat.id
    await context.bot.send_invoice(
        chat_id=chat_id,
        title=SUBSCRIPTION_TITLE,
        description=SUBSCRIPTION_DESCRIPTION,
        payload=SUBSCRIPTION_PAYLOAD,
        currency="XTR",
        prices=[LabeledPrice("Monthly", SUBSCRIPTION_PRICE)],
    )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approve all pre-checkout queries for our subscription payload."""
    query = update.pre_checkout_query
    if query.invoice_payload == SUBSCRIPTION_PAYLOAD:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Unknown payment payload.")


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a successful Stars payment: record transaction and activate subscription."""
    payment = update.message.successful_payment
    user_id = str(update.effective_user.id)

    users_repo = app_container.get(UsersRepository)
    transactions_repo = app_container.get(TransactionsRepository)

    transactions_repo.create(
        user_id=user_id,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id,
        total_amount=payment.total_amount,
        currency=payment.currency,
        is_recurring=payment.is_recurring or False,
    )

    new_expires = users_repo.extend_subscription(user_id)
    expires_str = new_expires.strftime("%Y-%m-%d %H:%M UTC")

    logger.info(f"Subscription extended for user {user_id} until {expires_str}")
    await update.message.reply_text(
        f"Thank you! Your subscription is active until {expires_str}. Enjoy Patron!"
    )


async def bot_participation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    chat_id = str(update.message.chat_id)

    # Check subscription status — inactive users get a reminder
    users_repo = app_container.get(UsersRepository)
    status = users_repo.get_subscription_status(user_id)
    if status != "active":
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            reply_to_message_id=update.message.message_id,
            text=(
                "Your subscription is not active. "
                "Please use /subscribe to continue using Patron."
            ),
        )
        return

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
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(
        MessageHandler(telegram.ext.filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )

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
