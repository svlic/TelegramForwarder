"""Regression: extension whitelist must not fail-open on missing document/filename."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from enums.enums import AddMode
from filters.media_filter import MediaFilter


def _rule(*, mode=AddMode.WHITELIST):
    return SimpleNamespace(
        id=1,
        enable_extension_filter=True,
        extension_filter_mode=mode,
    )


def _document_media(*, file_name=None):
    attrs = []
    if file_name is not None:
        attrs.append(SimpleNamespace(file_name=file_name))
    document = SimpleNamespace(attributes=attrs)
    return SimpleNamespace(document=document)


class MediaExtensionWhitelistTests(unittest.IsolatedAsyncioTestCase):
    async def test_whitelist_rejects_media_without_document(self):
        media_filter = MediaFilter()
        rule = _rule(mode=AddMode.WHITELIST)
        media = SimpleNamespace(document=None)

        allowed = await media_filter._is_media_extension_allowed(rule, media)

        self.assertFalse(allowed)

    async def test_blacklist_allows_media_without_document(self):
        media_filter = MediaFilter()
        rule = _rule(mode=AddMode.BLACKLIST)
        media = SimpleNamespace(document=None)

        allowed = await media_filter._is_media_extension_allowed(rule, media)

        self.assertTrue(allowed)

    @patch("filters.media_filter.get_db_session")
    @patch("filters.media_filter.get_db_ops", new_callable=AsyncMock)
    async def test_whitelist_rejects_document_without_filename(
        self, mock_get_db_ops, mock_get_db_session
    ):
        mock_db_ops = MagicMock()
        mock_db_ops.get_media_extensions = AsyncMock(return_value=[{"extension": "pdf"}])
        mock_get_db_ops.return_value = mock_db_ops

        session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = session

        media_filter = MediaFilter()
        rule = _rule(mode=AddMode.WHITELIST)
        media = _document_media(file_name=None)

        allowed = await media_filter._is_media_extension_allowed(rule, media)

        self.assertFalse(allowed)

    @patch("filters.media_filter.get_db_session")
    @patch("filters.media_filter.get_db_ops", new_callable=AsyncMock)
    async def test_whitelist_allows_explicit_no_extension_entry(
        self, mock_get_db_ops, mock_get_db_session
    ):
        mock_db_ops = MagicMock()
        mock_db_ops.get_media_extensions = AsyncMock(
            return_value=[{"extension": "无扩展名"}]
        )
        mock_get_db_ops.return_value = mock_db_ops

        session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = session

        media_filter = MediaFilter()
        rule = _rule(mode=AddMode.WHITELIST)
        media = _document_media(file_name="README")

        allowed = await media_filter._is_media_extension_allowed(rule, media)

        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()