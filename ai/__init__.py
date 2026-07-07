from .openai_base_provider import CustomOpenAIProvider


async def get_ai_provider():
    return CustomOpenAIProvider()


__all__ = ['get_ai_provider']
