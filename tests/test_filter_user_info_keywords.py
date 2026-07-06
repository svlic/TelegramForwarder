"""Regression: is_filter_user_info must keep process_user_info / get_sender_info wired."""

import unittest
from types import SimpleNamespace

from enums.enums import ForwardMode
from utils import common


class _FakeSender:
    def __init__(self, *, first_name=None, last_name=None, title=None):
        self.first_name = first_name
        self.last_name = last_name
        self.title = title


class _FakeMessage:
    def __init__(self, *, sender_chat=None):
        self.sender_chat = sender_chat
        self.peer_id = None


class _FakeEvent:
    def __init__(self, *, sender=None, sender_chat=None):
        self.sender = sender
        self.message = _FakeMessage(sender_chat=sender_chat)
        self.client = None


def _blacklist_rule(*, is_filter_user_info: bool, keyword: str):
    kw = SimpleNamespace(
        keyword=keyword,
        is_regex=False,
        is_blacklist=True,
    )
    return SimpleNamespace(
        id=42,
        is_filter_user_info=is_filter_user_info,
        forward_mode=ForwardMode.BLACKLIST,
        keywords=[kw],
        enable_reverse_blacklist=False,
        enable_reverse_whitelist=False,
    )


class FilterUserInfoKeywordsTest(unittest.IsolatedAsyncioTestCase):
    async def test_process_user_info_prefixes_personal_sender(self):
        event = _FakeEvent(sender=_FakeSender(first_name="Alice", last_name="Lee"))
        out = await common.process_user_info(event, 1, "body")
        self.assertEqual(out, "Alice Lee Alice Lee:\nbody")

    async def test_check_keywords_applies_sender_prefix_when_filter_enabled(self):
        event = _FakeEvent(sender=_FakeSender(first_name="Alice", last_name="Lee"))
        rule = _blacklist_rule(is_filter_user_info=True, keyword="Alice")
        allowed = await common.check_keywords(rule, "only body", event)
        self.assertFalse(allowed)

    async def test_check_keywords_without_filter_uses_raw_message_only(self):
        event = _FakeEvent(sender=_FakeSender(first_name="Alice", last_name="Lee"))
        rule = _blacklist_rule(is_filter_user_info=False, keyword="Alice")
        allowed = await common.check_keywords(rule, "Alice said hi", event)
        self.assertFalse(allowed)

        allowed_plain = await common.check_keywords(rule, "no match here", event)
        self.assertTrue(allowed_plain)


if __name__ == "__main__":
    unittest.main()
