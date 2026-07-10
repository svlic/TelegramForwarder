"""Regression tests for review fixes: clear_all, media cleanup, regex safety, keyword ops, InitFilter."""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from filters.context import MessageContext
from filters.filter_chain import FilterChain
from filters.base_filter import BaseFilter
from filters.init_filter import InitFilter
from filters.replace_filter import ReplaceFilter
from handlers.command_handlers import perform_clear_all
from models.db_operations import DBOperations
from utils.common import check_keyword_match
from utils.regex_safety import (
    MAX_REGEX_PATTERN_LENGTH,
    RegexTimeoutError,
    safe_re_search,
)


class _AbortFilter(BaseFilter):
    async def _process(self, context):
        return False


class _RaiseFilter(BaseFilter):
    async def _process(self, context):
        raise RuntimeError("boom")


class ClearAllTests(unittest.IsolatedAsyncioTestCase):
    async def test_perform_clear_all_deletes_child_tables_first(self):
        session = MagicMock()
        query = MagicMock()
        session.query.return_value = query
        query.delete.return_value = 1

        await perform_clear_all(session)

        deleted_models = [call.args[0].__name__ for call in session.query.call_args_list]
        self.assertEqual(
            deleted_models,
            [
                "MediaTypes",
                "MediaExtensions",
                "RuleSync",
                "ReplaceRule",
                "Keyword",
                "ForwardRule",
                "Chat",
            ],
        )
        self.assertEqual(query.delete.call_count, 7)
        session.commit.assert_called_once()


class MediaCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_filter_chain_cleans_media_on_abort(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = tmp.name
            tmp.write(b"x")

        chain = FilterChain()
        chain.add_filter(_AbortFilter())
        event = SimpleNamespace(message=SimpleNamespace(text="hi", buttons=None, grouped_id=None))
        rule = SimpleNamespace()

        original_init = MessageContext.__init__

        def _init_with_media(self, client, event, chat_id, rule):
            original_init(self, client, event, chat_id, rule)
            self.media_files = [path]

        with patch.object(MessageContext, "__init__", _init_with_media):
            result = await chain.process(None, event, 1, rule)

        self.assertFalse(result)
        self.assertFalse(os.path.exists(path))

    async def test_filter_chain_cleans_media_on_exception(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = tmp.name
            tmp.write(b"x")

        chain = FilterChain()
        chain.add_filter(_RaiseFilter())
        event = SimpleNamespace(message=SimpleNamespace(text="hi", buttons=None, grouped_id=None))
        rule = SimpleNamespace()

        original_init = MessageContext.__init__

        def _init_with_media(self, client, event, chat_id, rule):
            original_init(self, client, event, chat_id, rule)
            self.media_files = [path]

        with patch.object(MessageContext, "__init__", _init_with_media):
            result = await chain.process(None, event, 1, rule)

        self.assertFalse(result)
        self.assertFalse(os.path.exists(path))


class RegexSafetyTests(unittest.IsolatedAsyncioTestCase):
    def test_rejects_oversized_pattern(self):
        with self.assertRaises(Exception):
            safe_re_search("a" * (MAX_REGEX_PATTERN_LENGTH + 1), "a")

    def test_search_match(self):
        match = safe_re_search(r"foo", "xxfooyy")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0), "foo")

    async def test_check_keyword_match_uses_safe_search(self):
        keyword = SimpleNamespace(keyword=r"abc", is_regex=True, is_blacklist=False)
        self.assertTrue(await check_keyword_match(keyword, "xxabcyy"))

    async def test_check_keyword_match_timeout_whitelist_rejects(self):
        keyword = SimpleNamespace(keyword=r"(a+)+$", is_regex=True, is_blacklist=False)
        with patch(
            "utils.common.safe_re_search",
            side_effect=RegexTimeoutError("timeout"),
        ):
            self.assertFalse(await check_keyword_match(keyword, "aaaaaaaa!"))

    async def test_check_keyword_match_timeout_blacklist_matches(self):
        keyword = SimpleNamespace(keyword=r"(a+)+$", is_regex=True, is_blacklist=True)
        with patch(
            "utils.common.safe_re_search",
            side_effect=RegexTimeoutError("timeout"),
        ):
            self.assertTrue(await check_keyword_match(keyword, "aaaaaaaa!"))

    async def test_replace_filter_uses_safe_sub(self):
        replace_filter = ReplaceFilter()
        rule = SimpleNamespace(
            is_replace=True,
            replace_rules=[SimpleNamespace(pattern=r"foo", content="bar")],
        )
        context = SimpleNamespace(
            rule=rule,
            message_text="xxfooyy",
            check_message_text="xxfooyy",
            errors=[],
        )
        await replace_filter._process(context)
        self.assertEqual(context.message_text, "xxbaryy")


class KeywordOpsTests(unittest.IsolatedAsyncioTestCase):
    async def test_add_keywords_allows_same_text_different_is_regex(self):
        ops = DBOperations()
        session = MagicMock()
        rule = SimpleNamespace(id=1, enable_sync=False)
        session.get.return_value = rule

        query = MagicMock()
        session.query.return_value = query
        query.filter.return_value = query
        query.first.return_value = None

        with patch.object(ops, "sync_to_server", new_callable=AsyncMock):
            success, duplicate = await ops.add_keywords(
                session, 1, ["hello"], is_regex=True, is_blacklist=False
            )

        filter_exprs = query.filter.call_args.args
        expr_repr = " ".join(str(e) for e in filter_exprs)
        self.assertIn("is_regex", expr_repr)
        self.assertEqual(success, 1)
        self.assertEqual(duplicate, 0)
        session.add.assert_called_once()

    async def test_delete_keywords_dedups_and_sorts_indices(self):
        ops = DBOperations()
        session = MagicMock()
        rule = SimpleNamespace(id=1, enable_sync=False, add_mode=SimpleNamespace(name="WHITELIST"))
        # add_mode compared to AddMode.BLACKLIST
        from enums.enums import AddMode
        rule.add_mode = AddMode.WHITELIST
        session.get.return_value = rule

        kw1 = SimpleNamespace(keyword="a", is_regex=False, is_blacklist=False)
        kw2 = SimpleNamespace(keyword="b", is_regex=False, is_blacklist=False)
        kw3 = SimpleNamespace(keyword="c", is_regex=False, is_blacklist=False)
        keywords = [kw1, kw2, kw3]

        with patch.object(ops, "get_keywords", new_callable=AsyncMock, return_value=keywords), \
             patch.object(ops, "sync_to_server", new_callable=AsyncMock):
            deleted, remaining = await ops.delete_keywords(session, 1, [1, 3, 3, 1])

        self.assertEqual(deleted, 2)
        deleted_objs = [c.args[0] for c in session.delete.call_args_list]
        # high index first (3 then 1) so 1-based positions stay stable
        self.assertEqual(deleted_objs, [kw3, kw1])

    async def test_delete_replace_rules_dedups_and_sorts_indices(self):
        ops = DBOperations()
        session = MagicMock()
        rule = SimpleNamespace(id=1, enable_sync=False)
        session.get.return_value = rule

        r1 = SimpleNamespace(pattern="a", content="")
        r2 = SimpleNamespace(pattern="b", content="")
        r3 = SimpleNamespace(pattern="c", content="")
        rules = [r1, r2, r3]

        with patch.object(ops, "get_replace_rules", new_callable=AsyncMock, return_value=rules):
            deleted, remaining = await ops.delete_replace_rules(session, 1, [2, 2, 1])

        self.assertEqual(deleted, 2)
        deleted_objs = [c.args[0] for c in session.delete.call_args_list]
        self.assertEqual(deleted_objs, [r2, r1])


class InitFilterTests(unittest.IsolatedAsyncioTestCase):
    async def test_init_filter_propagates_outer_exception(self):
        init_filter = InitFilter()
        # Accessing event.message.grouped_id on a broken event must not be swallowed
        event = SimpleNamespace()
        # no message attribute -> AttributeError
        context = SimpleNamespace(rule=SimpleNamespace(media_caption_filter=False), event=event)

        with self.assertRaises(AttributeError):
            await init_filter._process(context)

    async def test_init_filter_returns_true_for_non_group(self):
        init_filter = InitFilter()
        event = SimpleNamespace(message=SimpleNamespace(grouped_id=None))
        context = SimpleNamespace(rule=SimpleNamespace(media_caption_filter=False), event=event)
        self.assertTrue(await init_filter._process(context))


if __name__ == "__main__":
    unittest.main()
