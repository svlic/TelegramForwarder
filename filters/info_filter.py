import logging
import os
import pytz
from filters.base_filter import BaseFilter
from utils.common import extract_channel_id_for_url

logger = logging.getLogger(__name__)

class InfoFilter(BaseFilter):

    async def _process(self, context):
        rule = context.rule
        event = context.event

        if rule.is_original_link:
            chat_id = getattr(event, 'chat_id', None)
            message = context.primary_message if context.primary_message else getattr(event, 'message', None)
            message_id = getattr(message, 'id', None) if message else None

            if chat_id is not None and message_id is not None:
                channel_id_for_url = extract_channel_id_for_url(chat_id)
                original_link = f"https://t.me/c/{channel_id_for_url}/{message_id}"

                if hasattr(rule, 'original_link_template') and rule.original_link_template:
                    try:
                        link_info = rule.original_link_template
                        link_info = link_info.replace("{original_link}", original_link)

                        context.original_link = f"\n\n{link_info}"
                    except Exception as le:
                        logger.error(f'使用自定义链接模板出错: {str(le)}，使用默认格式')
                        context.original_link = f"\n\n原始消息: {original_link}"
                else:
                    context.original_link = f"\n\n原始消息: {original_link}"

                logger.info(f'添加原始链接: {context.original_link}')

        if rule.is_original_sender:
            try:
                logger.info("开始获取发送者信息")
                sender_name = "Unknown Sender"
                sender_id = "Unknown"

                message = getattr(event, 'message', None)

                if message and hasattr(message, 'sender_chat') and message.sender_chat:
                    sender = message.sender_chat
                    sender_name = sender.title if hasattr(sender, 'title') else "Unknown Channel"
                    sender_id = sender.id
                    logger.info(f"使用频道信息: {sender_name} (ID: {sender_id})")

                elif getattr(event, 'sender', None):
                    sender = event.sender
                    sender_name = (
                        sender.title if hasattr(sender, 'title')
                        else f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                    )
                    sender_id = sender.id
                    logger.info(f"使用发送者信息: {sender_name} (ID: {sender_id})")

                elif message and hasattr(message, 'peer_id') and message.peer_id:
                    peer = message.peer_id
                    if hasattr(peer, 'channel_id'):
                        sender_id = peer.channel_id
                        try:
                            client = getattr(event, 'client', None)
                            if client:
                                channel = await client.get_entity(peer)
                                sender_name = channel.title if hasattr(channel, 'title') else "Unknown Channel"
                        except Exception as ce:
                            logger.error(f'获取频道信息失败: {str(ce)}')
                            sender_name = "Unknown Channel"
                    logger.info(f"使用peer_id信息: {sender_name} (ID: {sender_id})")

                # 检查是否有用户自定义模板
                if hasattr(rule, 'userinfo_template') and rule.userinfo_template:
                    # 替换模板中的变量
                    user_info = rule.userinfo_template
                    user_info = user_info.replace("{name}", sender_name)
                    user_info = user_info.replace("{id}", str(sender_id))

                    context.sender_info = f"{user_info}\n\n"
                else:
                    # 使用默认格式
                    context.sender_info = f"{sender_name}\n\n"

                logger.info(f'添加发送者信息: {context.sender_info}')
            except Exception as e:
                logger.error(f'获取发送者信息出错: {str(e)}')

        if rule.is_original_time:
            try:
                timezone = pytz.timezone(os.getenv('DEFAULT_TIMEZONE', 'Asia/Shanghai'))
                message = getattr(event, 'message', None)
                if message and hasattr(message, 'date'):
                    local_time = message.date.astimezone(timezone)
                    formatted_time = local_time.strftime('%Y-%m-%d %H:%M:%S')

                    if hasattr(rule, 'time_template') and rule.time_template:
                        try:
                            time_info = rule.time_template.replace("{time}", formatted_time)
                            context.time_info = f"\n\n{time_info}"
                        except Exception as te:
                            logger.error(f'使用自定义时间模板出错: {str(te)}，使用默认格式')
                            context.time_info = f"\n\n{formatted_time}"
                    else:
                        context.time_info = f"\n\n{formatted_time}"

                    logger.info(f'添加时间信息: {context.time_info}')
            except Exception as e:
                logger.error(f'处理时间信息时出错: {str(e)}')

        return True