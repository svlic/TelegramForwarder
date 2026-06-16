import logging
import unicodedata
from filters.base_filter import BaseFilter

logger = logging.getLogger(__name__)

ZERO_WIDTH_CHARACTERS = {
    '\u200b',
    '\u200c',
    '\u200d',
    '\ufeff',
    '\u2060',
}


def normalize_message_text(text):
    if not text:
        return text

    normalized_text = unicodedata.normalize('NFKC', text)
    return ''.join(char for char in normalized_text if char not in ZERO_WIDTH_CHARACTERS)


class TextNormalizeFilter(BaseFilter):

    async def _process(self, context):
        original_text = context.message_text
        normalized_text = normalize_message_text(original_text)

        if normalized_text != original_text:
            logger.info('消息文本已完成预标准化处理')

        context.original_message_text = normalized_text
        context.message_text = normalized_text
        context.check_message_text = normalized_text
        return True
