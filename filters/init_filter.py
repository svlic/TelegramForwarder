import logging
from filters.base_filter import BaseFilter

logger = logging.getLogger(__name__)

class InitFilter(BaseFilter):
    """
    初始化过滤器，为context添加基本信息
    """

    async def _process(self, context):
        """
        添加原始链接和发送者信息

        Args:
            context: 消息上下文

        Returns:
            bool: 是否继续处理
        """
        rule = context.rule
        event = context.event

        # logger.info(f"InitFilter处理消息前，context: {context.__dict__}")
        try:
            if event.message.grouped_id:
                primary_message = event.message

                try:
                    async for message in event.client.iter_messages(
                        event.chat_id,
                        limit=20,
                        min_id=event.message.id - 10,
                        max_id=event.message.id + 10
                    ):
                        if message.grouped_id != event.message.grouped_id:
                            continue

                        if rule.media_caption_filter and not message.text:
                            continue

                        if message.text and (not primary_message.text or message.id < primary_message.id):
                            primary_message = message

                    context.primary_message = primary_message
                    primary_text = primary_message.text or ''
                    context.message_text = primary_text
                    context.original_message_text = primary_text
                    context.check_message_text = primary_text
                    context.buttons = primary_message.buttons if hasattr(primary_message, 'buttons') else None
                    logger.info(f'媒体组主消息已确定: ID={primary_message.id}, text={primary_text}')

                except Exception as e:
                    logger.error(f'收集媒体组消息时出错: {str(e)}')
                    context.errors.append(f"收集媒体组消息错误: {str(e)}")

        finally:
            # logger.info(f"InitFilter处理消息后，context: {context.__dict__}")
            return True
