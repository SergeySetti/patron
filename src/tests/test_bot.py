import sys
from unittest.mock import AsyncMock, MagicMock
import unittest

# Mock dependencies that are not available
mock_telegram = MagicMock()
sys.modules['telegram'] = mock_telegram
sys.modules['telegram.ext'] = MagicMock()

from src.bot import start, bot_participation

class TestBot(unittest.IsolatedAsyncioTestCase):
    async def test_start(self):
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
            text='Welcome'
        )

    async def test_bot_participation(self):
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
            text='response result'
        )

if __name__ == '__main__':
    unittest.main()
