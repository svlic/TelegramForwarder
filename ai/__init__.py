from .base import BaseAIProvider
from .openai_base_provider import CustomOpenAIProvider


async def get_ai_provider():
    return CustomOpenAIProvider()


__all__ = [
    'BaseAIProvider',
    'CustomOpenAIProvider',
    'get_ai_provider'
]
