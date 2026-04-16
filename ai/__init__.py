import logging

from .base import BaseAIProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .deepseek_provider import DeepSeekProvider
from .qwen_provider import QwenProvider
from .grok_provider import GrokProvider
from .claude_provider import ClaudeProvider

logger = logging.getLogger(__name__)

PROVIDER_MAP = {
    'gpt': OpenAIProvider,
    'o1': OpenAIProvider,
    'o3': OpenAIProvider,
    'chatgpt': OpenAIProvider,
    'claude': ClaudeProvider,
    'gemini': GeminiProvider,
    'deepseek': DeepSeekProvider,
    'qwen': QwenProvider,
    'qwq': QwenProvider,
    'qvq': QwenProvider,
    'grok': GrokProvider,
}


async def get_ai_provider(model=None):
    if not model:
        raise ValueError("未指定AI模型。请在规则中配置 ai_model 字段。")

    model_lower = model.lower()

    for prefix, provider_cls in PROVIDER_MAP.items():
        if model_lower.startswith(prefix):
            logger.info(f"模型 '{model}' 匹配 provider: {provider_cls.__name__}")
            return provider_cls()

    raise ValueError(f"无法识别模型 '{model}'。支持的模型前缀: {', '.join(PROVIDER_MAP.keys())}")


__all__ = [
    'BaseAIProvider',
    'OpenAIProvider',
    'GeminiProvider',
    'DeepSeekProvider',
    'QwenProvider',
    'GrokProvider',
    'ClaudeProvider',
    'get_ai_provider'
]
