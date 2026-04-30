import logging

from .base import BaseAIProvider
from .openai_base_provider import CustomOpenAIProvider

logger = logging.getLogger(__name__)


async def get_ai_provider():
    return CustomOpenAIProvider()


__all__ = [
    'BaseAIProvider',
    'CustomOpenAIProvider',
    'get_ai_provider'
]
