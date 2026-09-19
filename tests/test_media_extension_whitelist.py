"""Regression: extension whitelist must not fail-open on missing document/filename."""

import unittest
from types import SimpleNamespace

from enums.enums import AddMode
from filters.media_filter import MediaFilter


def _rule(*, mode=AddMode.WHITELIST, extensions=()):
    return SimpleNamespace(
        id=1,
        enable_extension_filter=True,
        extension_filter_mode=mode,
        media_extensions=[SimpleNamespace(extension=value) for value in extensions],
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

    async def test_whitelist_rejects_document_without_filename(self):
        media_filter = MediaFilter()
        rule = _rule(mode=AddMode.WHITELIST, extensions=("pdf",))
        media = _document_media(file_name=None)

        allowed = await media_filter._is_media_extension_allowed(rule, media)

        self.assertFalse(allowed)

    async def test_whitelist_allows_explicit_no_extension_entry(self):
        media_filter = MediaFilter()
        rule = _rule(mode=AddMode.WHITELIST, extensions=("无扩展名",))
        media = _document_media(file_name="README")

        allowed = await media_filter._is_media_extension_allowed(rule, media)

        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
