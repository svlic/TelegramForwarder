import logging
from filters.base_filter import BaseFilter
from utils.common import collect_media_group_messages, select_primary_media_group_message

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

        if event.message.grouped_id:
            try:
                media_group_messages = await collect_media_group_messages(
                    event.client,
                    event.chat_id,
                    event.message.grouped_id,
                )
                if media_group_messages:
                    context.media_group_messages = media_group_messages

                primary_message = select_primary_media_group_message(
                    media_group_messages or [event.message],
                    require_caption=rule.media_caption_filter,
                ) or event.message

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

        return True
