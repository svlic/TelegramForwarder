from .openai_base_provider import CustomOpenAIProvider

_provider = None

async def get_ai_provider():
    global _provider
    if _provider is None:
        _provider = CustomOpenAIProvider()
    return _provider


__all__ = ['get_ai_provider']
