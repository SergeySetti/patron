import pytest
from unittest.mock import AsyncMock, MagicMock
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
async def test_bot_participation():
    # Arrange
    update = MagicMock()
    update.message.chat_id = 67890
    update.message.message_id = 111
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    # Act
    await bot_participation(update, context)

    # Assert
    context.bot.send_message.assert_called_once_with(
        chat_id=67890,
        reply_to_message_id=111,
        text='responce result'
    )
