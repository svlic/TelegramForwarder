import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from models.models import ForwardRule
from scheduler.chat_updater import ChatUpdater
from utils.constants import CHAT_UPDATE_INTERVAL_SECONDS


class ForwardRuleAIFieldTests(unittest.TestCase):
    def test_is_ai_is_mapped_by_sqlalchemy(self):
        self.assertIn("is_ai", ForwardRule.__table__.columns)


class ChatUpdaterScheduleTests(unittest.IsolatedAsyncioTestCase):
    async def test_updates_chats_every_twenty_minutes(self):
        updater = ChatUpdater(user_client=object())
        updater._update_all_chats = AsyncMock()

        with patch(
            "scheduler.chat_updater.asyncio.sleep",
            new=AsyncMock(side_effect=[None, asyncio.CancelledError()]),
        ) as sleep:
            await updater._run_update_task()

        self.assertEqual(CHAT_UPDATE_INTERVAL_SECONDS, 20 * 60)
        self.assertEqual(sleep.await_args_list[0].args, (20 * 60,))
        updater._update_all_chats.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
