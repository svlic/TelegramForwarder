from typing import Optional, List, Dict
from openai import AsyncOpenAI
from .base import BaseAIProvider
import os
import logging

logger = logging.getLogger(__name__)


class CustomOpenAIProvider(BaseAIProvider):

    def __init__(self, env_prefix: str = 'CUSTOM_AI'):
        super().__init__()
        self.env_prefix = env_prefix
        self.client = None
        self.model = None

    async def initialize(self, **kwargs) -> None:
        try:
            api_key = os.getenv(f'{self.env_prefix}_API_KEY')
            if not api_key:
                raise ValueError(f"未设置 {self.env_prefix}_API_KEY 环境变量")

            api_base = os.getenv(f'{self.env_prefix}_API_BASE', '').strip()
            if not api_base:
                raise ValueError(f"未设置 {self.env_prefix}_API_BASE 环境变量，必须指定兼容 OpenAI 的 API 地址")

            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=api_base
            )

            self.model = kwargs.get('model')
            if not self.model:
                raise ValueError("未指定 AI 模型，请在规则中配置 ai_model 字段")

            logger.info(f"初始化 CustomOpenAI 模型: {self.model}, API: {api_base}")

        except Exception as e:
            error_msg = f"初始化 {self.env_prefix} 客户端时出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise

    async def process_message(self,
                            message: str,
                            prompt: Optional[str] = None,
                            images: Optional[List[Dict[str, str]]] = None,
                            **kwargs) -> str:
        try:
            if not self.client:
                await self.initialize(**kwargs)

            messages = []
            if prompt:
                messages.append({"role": "system", "content": prompt})

            if images:
                content = []
                content.append({
                    "type": "text",
                    "text": message
                })

                for img in images:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img['mime_type']};base64,{img['data']}"
                        }
                    })
                    logger.info(f"已添加一张类型为 {img['mime_type']} 的图片，大小约 {len(img['data']) // 1000} KB")

                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "user", "content": message})

            logger.info(f"实际使用的模型: {self.model}")

            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )

            collected_content = ""
            collected_reasoning = ""

            async for chunk in completion:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
                    collected_reasoning += delta.reasoning_content

                if hasattr(delta, 'content') and delta.content is not None:
                    collected_content += delta.content

            if not collected_content and collected_reasoning:
                logger.warning("模型只返回了思考过程，没有最终回答")
                return "模型未能生成有效回答"

            return collected_content

        except Exception as e:
            logger.error(f"{self.env_prefix} API 调用失败: {str(e)}", exc_info=True)
            raise
