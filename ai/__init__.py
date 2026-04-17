import logging

from .base import BaseAIProvider
from .openai_base_provider import CustomOpenAIProvider

logger = logging.getLogger(__name__)


async def get_ai_provider(model=None):
    if not model:
        raise ValueError("未指定AI模型。请在规则中配置 ai_model 字段。")

    return CustomOpenAIProvider()


__all__ = [
    'BaseAIProvider',
    'CustomOpenAIProvider',
    'get_ai_provider'
]
