import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.bot import start, bot_participation


@pytest.mark.asyncio
@patch("src.bot.app_container")
async def test_start_grants_trial_for_new_user(mock_container):
    from datetime import datetime, timezone, timedelta
    mock_users_repo = MagicMock()
    trial_expires = datetime(2025, 7, 1, tzinfo=timezone.utc)
    mock_users_repo.start_trial.return_value = trial_expires
    mock_container.get.return_value = mock_users_repo

    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_chat.id = 12345
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    await start(update, context)

    mock_users_repo.start_trial.assert_called_once_with("12345")
    context.bot.send_message.assert_called_once()
    call_kwargs = context.bot.send_message.call_args[1]
    assert "Patron" in call_kwargs["text"]
    assert "free trial" in call_kwargs["text"]


@pytest.mark.asyncio
@patch("src.bot.app_container")
async def test_start_no_trial_for_existing_user(mock_container):
    mock_users_repo = MagicMock()
    mock_users_repo.start_trial.return_value = None  # already had subscription
    mock_container.get.return_value = mock_users_repo

    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_chat.id = 12345
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    await start(update, context)

    context.bot.send_message.assert_called_once()
    call_kwargs = context.bot.send_message.call_args[1]
    assert "Patron" in call_kwargs["text"]
    assert "free trial" not in call_kwargs["text"]


@pytest.mark.asyncio
@patch("src.bot.app_container")
@patch("src.bot.run_agent")
async def test_bot_participation(mock_run_agent, mock_container):
    # Arrange — mock subscription as active
    mock_users_repo = MagicMock()
    mock_users_repo.get_subscription_status.return_value = "active"
    mock_container.get.return_value = mock_users_repo

    agent_response_text = "It's always sunny in New York!"
    mock_message = MagicMock()
    mock_message.content = [{"text": agent_response_text}]
    mock_run_agent.return_value = {
        'messages': [mock_message]
    }

    update = MagicMock()
    update.message.text = "What is the weather in New York?"
    update.message.chat_id = 67890
    update.message.message_id = 111
    update.effective_user.id = 12345
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    # Act
    await bot_participation(update, context)

    # Assert
    mock_run_agent.assert_called_once_with(
        "What is the weather in New York?",
        "12345",
        "67890",
    )
    context.bot.send_message.assert_called_once_with(
        chat_id=67890,
        reply_to_message_id=111,
        text=agent_response_text,
    )


@pytest.mark.asyncio
@patch("src.bot.app_container")
@patch("src.bot.run_agent")
async def test_bot_participation_inactive_subscription(mock_run_agent, mock_container):
    mock_users_repo = MagicMock()
    mock_users_repo.get_subscription_status.return_value = None
    mock_container.get.return_value = mock_users_repo

    update = MagicMock()
    update.message.text = "Hello"
    update.message.chat_id = 67890
    update.message.message_id = 111
    update.effective_user.id = 12345
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    await bot_participation(update, context)

    mock_run_agent.assert_not_called()
    call_kwargs = context.bot.send_message.call_args[1]
    assert "/subscribe" in call_kwargs["text"]
