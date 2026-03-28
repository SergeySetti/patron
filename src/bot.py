import os

import telegram
from telegram import LabeledPrice, Update
from telegram.ext import (
    CommandHandler,
    Application,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
)

from agents.patron_itself.patron_agent import run_agent
from agents.patron_itself.repositories.memories_repository import MemoriesRepository
from agents.patron_itself.repositories.transactions_repository import TransactionsRepository
from agents.patron_itself.repositories.users_repository import UsersRepository
from dependencies import app_container, AssistantLogger
from task_scheduler import check_due_tasks

CONFIRMING_DELETE_MEMORIES = 0
AWAITING_CUSTOM_PROMPT = 1

SUBSCRIPTION_TITLE = "Patron Monthly"
SUBSCRIPTION_DESCRIPTION = "Monthly subscription to Patron AI assistant"
SUBSCRIPTION_PRICE = 250  # Telegram Stars
SUBSCRIPTION_PAYLOAD = f"patron_monthly_{SUBSCRIPTION_PRICE}"

# 14 days in seconds, used for subscription expiration logic
SUBSCRIPTION_PERIOD = 14 * 24 * 60 * 60

logger = app_container.get(AssistantLogger)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)

    # Grant 14-day free trial for brand-new users
    users_repo = app_container.get(UsersRepository)
    users_repo.set_username(user_id, update.effective_user.username)
    trial_expires = users_repo.start_trial(user_id)
    if trial_expires:
        trial_str = trial_expires.strftime("%Y-%m-%d %H:%M UTC")
        logger.info(f"Trial started for user {user_id} until {trial_str}")

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
    trial_note = ""
    if trial_expires:
        trial_note = (
            f"\n\n\u2B50 *Your {SUBSCRIPTION_PERIOD // (24 * 60 * 60)}-day free trial has started!* "
            "After it ends, use /subscribe to keep using Patron."
        )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_text + trial_note,
        parse_mode="Markdown",
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


async def delete_memories_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user to confirm deletion of all their memories."""
    await update.message.reply_text(
        "This will permanently delete ALL your memories. "
        "Type `delete` to confirm or /cancel to abort.",
        parse_mode="Markdown",
    )
    return CONFIRMING_DELETE_MEMORIES


async def delete_memories_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user's confirmation for deleting all memories."""
    if update.message.text.strip().lower() == "delete":
        user_id = str(update.effective_user.id)
        memories_repo = app_container.get(MemoriesRepository)
        count = memories_repo.delete_all_for_user(user_id)
        await update.message.reply_text(f"Done. {count} memories deleted.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Deletion cancelled. Type `delete` to confirm or /cancel to abort.",
        parse_mode="Markdown",
    )
    return CONFIRMING_DELETE_MEMORIES


async def delete_memories_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the delete memories flow."""
    await update.message.reply_text("Deletion cancelled.")
    return ConversationHandler.END


TERMS_AND_CONDITIONS = (
    "*Terms and Conditions*\n"
    "Last updated: March 15, 2026\n"
    "\n"
    "By using Patron you agree to the following terms.\n"
    "\n"
    "*1. Service Description*\n"
    "Patron is an AI\u2011powered personal assistant available through Telegram. "
    "It provides memory storage, task scheduling, and conversational assistance.\n"
    "\n"
    "*2. Account & Eligibility*\n"
    "You must have a valid Telegram account. One Patron subscription per Telegram user. "
    "You are responsible for everything that happens under your account.\n"
    "\n"
    "*3. Free Trial*\n"
    "New users receive a 14\u2011day free trial. No payment is required to start the trial. "
    "After the trial expires you need an active subscription to continue using the service.\n"
    "\n"
    "*4. Subscription & Payments*\n"
    "Subscriptions are billed monthly via Telegram Stars. "
    "Each payment extends your access by 30 days. "
    "Payments are non\u2011refundable except where required by applicable law. "
    "Refund requests can be submitted to the contact email below.\n"
    "\n"
    "*5. Your Data*\n"
    "Patron stores the memories and tasks you create. "
    "Your data is used solely to provide the service and is never sold to third parties. "
    "You can delete all your memories at any time with /deletememories. "
    "We may use anonymized, aggregated analytics to improve the service.\n"
    "\n"
    "*6. Acceptable Use*\n"
    "You agree not to use Patron to store illegal content, "
    "attempt to abuse or reverse\u2011engineer the service, "
    "or interfere with other users' access.\n"
    "\n"
    "*7. AI Limitations*\n"
    "Patron is powered by AI and may produce inaccurate or incomplete responses. "
    "It is not a substitute for professional advice (medical, legal, financial, etc.). "
    "Use your own judgment when acting on information provided by the assistant.\n"
    "\n"
    "*8. Availability*\n"
    "We aim for continuous availability but do not guarantee uninterrupted service. "
    "Maintenance windows or outages may occur without prior notice.\n"
    "\n"
    "*9. Termination*\n"
    "You may stop using Patron at any time. "
    "We reserve the right to suspend or terminate accounts that violate these terms.\n"
    "\n"
    "*10. Changes to Terms*\n"
    "We may update these terms from time to time. "
    "Continued use of the service after changes constitutes acceptance.\n"
    "\n"
    "*Contact:* serhii.setti@pm.me"
)


async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the terms and conditions."""
    await update.message.reply_text(TERMS_AND_CONDITIONS, parse_mode="Markdown")


async def contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send contact information."""
    await update.message.reply_text(
        "*Contacts*\n"
        "\n"
        "Email: serhii.setti@pm.me\n"
        "Telegram: @SergeySetti\n"
        "\n"
        "Have a specific workflow in mind? We can integrate almost any "
        "third\u2011party tool or service into your Patron bot \u2014 "
        "calendars, CRMs, project trackers, you name it. "
        "Reach out to discuss a custom integration at a special rate!",
        parse_mode="Markdown",
    )


async def custom_prompt_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show current custom prompt and ask user for a new one."""
    user_id = str(update.effective_user.id)
    users_repo = app_container.get(UsersRepository)
    current = users_repo.get_custom_prompt(user_id)

    if current:
        text = (
            f"*Your current custom prompt:*\n{current}\n\n"
            "Send new text to replace it, type `clear` to remove, or /cancel."
        )
    else:
        text = (
            "You don't have a custom prompt yet.\n\n"
            "Send me the text you'd like to include in every conversation "
            "(preferences, style, goals, etc.) or /cancel."
        )

    await update.message.reply_text(text, parse_mode="Markdown")
    return AWAITING_CUSTOM_PROMPT


async def custom_prompt_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save or clear the user's custom prompt."""
    user_id = str(update.effective_user.id)
    users_repo = app_container.get(UsersRepository)
    text = update.message.text.strip()

    if text.lower() == "clear":
        users_repo.clear_custom_prompt(user_id)
        await update.message.reply_text("Custom prompt cleared.")
    else:
        users_repo.set_custom_prompt(user_id, text)
        await update.message.reply_text(
            "Custom prompt saved! It will be included in all future conversations."
        )

    return ConversationHandler.END


async def custom_prompt_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the custom prompt flow."""
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def _is_subscribed(user_id: str) -> bool:
    """Check whether the user has an active subscription."""
    users_repo = app_container.get(UsersRepository)
    return users_repo.get_subscription_status(user_id) == "active"


async def bot_participation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    user_message = update.message.text
    user_id = str(update.effective_user.id)
    chat_id = str(update.message.chat_id)

    username = update.effective_user.username
    logger.info(f"User message from @{username}: {user_message}")

    response = await run_agent(user_message, user_id, chat_id,
                               is_subscribed=_is_subscribed(user_id))
    agent_reply = response['messages'][-1].text

    logger.info(f"Agent reply: {agent_reply}")

    await context.bot.send_message(
        chat_id=update.message.chat_id,
        reply_to_message_id=update.message.message_id,
        text=agent_reply,
    )


async def voice_participation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    user_id = str(update.effective_user.id)
    chat_id = str(update.message.chat_id)

    voice = update.message.voice
    voice_file = await context.bot.get_file(voice.file_id)
    audio_bytes = await voice_file.download_as_bytearray()

    caption = update.message.caption or ""
    logger.info(f"Voice message from user {user_id} ({voice.duration}s, {voice.file_size} bytes)")

    response = await run_agent(caption, user_id, chat_id, audio=bytes(audio_bytes),
                               is_subscribed=_is_subscribed(user_id))
    agent_reply = response['messages'][-1].text

    logger.info(f"Agent reply: {agent_reply}")

    await context.bot.send_message(
        chat_id=update.message.chat_id,
        reply_to_message_id=update.message.message_id,
        text=agent_reply,
    )


async def photo_participation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    user_id = str(update.effective_user.id)
    chat_id = str(update.message.chat_id)

    # Telegram provides multiple sizes; pick the largest
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    image_bytes = await photo_file.download_as_bytearray()

    # Determine MIME type from file path (Telegram returns .jpg typically)
    file_path = photo_file.file_path or ""
    if file_path.endswith(".png"):
        mime = "image/png"
    else:
        mime = "image/jpeg"

    caption = update.message.caption or ""
    logger.info(f"Photo from user {user_id} ({photo.width}x{photo.height}, {photo.file_size} bytes)")

    response = await run_agent(caption, user_id, chat_id, image=bytes(image_bytes), image_mime=mime,
                               is_subscribed=_is_subscribed(user_id))
    agent_reply = response['messages'][-1].text

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
    application.add_handler(CommandHandler("terms", terms))
    application.add_handler(CommandHandler("contacts", contacts))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(
        MessageHandler(telegram.ext.filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )

    delete_memories_handler = ConversationHandler(
        entry_points=[CommandHandler("deletememories", delete_memories_start)],
        states={
            CONFIRMING_DELETE_MEMORIES: [
                CommandHandler("cancel", delete_memories_cancel),
                MessageHandler(telegram.ext.filters.TEXT & ~telegram.ext.filters.COMMAND, delete_memories_confirm),
            ],
        },
        fallbacks=[CommandHandler("cancel", delete_memories_cancel)],
    )
    application.add_handler(delete_memories_handler)

    custom_prompt_handler = ConversationHandler(
        entry_points=[CommandHandler("customprompt", custom_prompt_start)],
        states={
            AWAITING_CUSTOM_PROMPT: [
                CommandHandler("cancel", custom_prompt_cancel),
                MessageHandler(telegram.ext.filters.TEXT & ~telegram.ext.filters.COMMAND, custom_prompt_receive),
            ],
        },
        fallbacks=[CommandHandler("cancel", custom_prompt_cancel)],
    )
    application.add_handler(custom_prompt_handler)

    application.add_handler(
        MessageHandler(telegram.ext.filters.VOICE, voice_participation)
    )
    application.add_handler(
        MessageHandler(telegram.ext.filters.PHOTO, photo_participation)
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
