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
async def test_bot_participation():
    # Arrange
    update = MagicMock()
    update.message.chat_id = 67890
    update.message.message_id = 111
    update.message.text = "Hello"
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    # Mock the agent
    with patch('src.bot.agent') as mock_agent:
        mock_agent.ainvoke = AsyncMock(return_value={"output": "Hello from agent!"})

        # Act
        await bot_participation(update, context)

        # Assert
        mock_agent.ainvoke.assert_called_once_with({"input": "Hello"})
        context.bot.send_message.assert_called_once_with(
            chat_id=67890,
            reply_to_message_id=111,
            text='Hello from agent!'
        )
