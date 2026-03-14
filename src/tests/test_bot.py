import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.bot import start, bot_participation


@pytest.mark.asyncio
async def test_start():
    # Arrange
    update = MagicMock()
    update.effective_user.id = 12345
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    # Act
    await start(update, context)

    # Assert
    context.bot.send_message.assert_called_once_with(
        chat_id=12345,
        text='Wellcome'
    )


@pytest.mark.asyncio
@patch("src.bot.run_agent")
async def test_bot_participation(mock_run_agent):
    # Arrange
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
