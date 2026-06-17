import logging
import os
import asyncio
from filters.base_filter import BaseFilter
from enums.enums import PreviewMode
from telethon.errors import FloodWaitError
from utils.common import normalize_channel_id, extract_channel_id_for_url

logger = logging.getLogger(__name__)

class SenderFilter(BaseFilter):
    """
    消息发送过滤器，用于发送处理后的消息
    """

    async def _process(self, context):
        """
        发送处理后的消息

        Args:
            context: 消息上下文

        Returns:
            bool: 是否继续处理
        """
        rule = context.rule
        client = context.client
        event = context.event

        if not context.should_forward:
            logger.info('消息不满足转发条件，跳过发送')
            return False

        # 获取目标聊天信息
        target_chat = rule.target_chat
        target_chat_id = int(target_chat.telegram_chat_id)

        # Normalize channel ID to standard format
        target_chat_id = normalize_channel_id(target_chat_id)

        # 预先获取目标聊天实体
        try:
            await client.get_entity(target_chat_id)
            logger.info(f'成功获取目标聊天实体: {target_chat.name} (ID: {target_chat_id})')
        except Exception as e:
            logger.warning(f'获取目标聊天实体时出错: {str(e)}')

        # 设置消息格式
        parse_mode = rule.message_mode.value  # 使用枚举的值（字符串）
        logger.info(f'使用消息格式: {parse_mode}')

        try:
            # 处理媒体组消息
            if context.is_media_group or (context.media_group_messages and context.skipped_media):
                logger.info(f'准备发送媒体组消息')
                await self._send_media_group(context, target_chat_id, parse_mode)
            # 处理单条媒体消息
            elif context.media_files or context.skipped_media:
                logger.info(f'准备发送单条媒体消息')
                await self._send_single_media(context, target_chat_id, parse_mode)
            # 处理纯文本消息
            else:
                logger.info(f'准备发送纯文本消息')
                await self._send_text_message(context, target_chat_id, parse_mode)

            logger.info(f'消息已发送到: {target_chat.name} ({target_chat_id})')
            return True
        except FloodWaitError as e:
            wait_time = e.seconds
            max_wait = 300
            if wait_time > max_wait:
                logger.error(f'发送消息频率限制等待时间过长({wait_time}秒)，放弃重试')
                context.errors.append(f"发送消息频率限制，需等待 {wait_time} 秒，已放弃")
                return False
            logger.warning(f'发送消息频率限制，等待 {wait_time} 秒后重试')
            await asyncio.sleep(wait_time)
            try:
                if context.is_media_group or (context.media_group_messages and context.skipped_media):
                    await self._send_media_group(context, target_chat_id, parse_mode)
                elif context.media_files or context.skipped_media:
                    await self._send_single_media(context, target_chat_id, parse_mode)
                else:
                    await self._send_text_message(context, target_chat_id, parse_mode)
                logger.info(f'FloodWait重试成功，消息已发送到: {target_chat_id}')
                return True
            except Exception as retry_error:
                logger.error(f'FloodWait重试失败: {str(retry_error)}')
                context.errors.append(f"重试发送失败: {str(retry_error)}")
                return False
        except Exception as e:
            logger.error(f'发送消息时出错: {str(e)}')
            context.errors.append(f"发送消息错误: {str(e)}")
            return False

    async def _send_media_group(self, context, target_chat_id, parse_mode):
        """发送媒体组消息"""
        rule = context.rule
        client = context.client
        event = context.event
        # 初始化转发消息列表
        context.forwarded_messages = []

        # if not context.media_group_messages:
        #     logger.info(f'所有媒体都超限，发送文本和提示')
        #     # 构建提示信息
        #     text_to_send = context.message_text or ''

        #     # 设置原始消息链接
        #     context.original_link = f"\n原始消息: https://t.me/c/{str(event.chat_id)[4:]}/{event.message.id}"

        #     # 添加每个超限文件的信息
        #     for message, size, name in context.skipped_media:
        #         text_to_send += f"\n\n⚠️ 媒体文件 {name if name else '未命名文件'} ({size}MB) 超过大小限制"

        #     # 组合完整文本
        #     text_to_send = context.sender_info + text_to_send + context.time_info + context.original_link

        #     await client.send_message(
        #         target_chat_id,
        #         text_to_send,
        #         parse_mode=parse_mode,
        #         link_preview=True,
        #         buttons=context.buttons
        #     )
        #     logger.info(f'媒体组所有文件超限，已发送文本和提示')
        #     return

        # 如果有可以发送的媒体，作为一个组发送
        files = []
        try:
            for message in context.media_group_messages:
                if message.media:
                    file_path = await message.download_media(os.path.join(os.getcwd(), 'temp'))
                    if file_path:
                        files.append(file_path)

            # 修改：保存下载的文件路径到context.media_files
            if files:
                # 初始化 media_files 如果它不存在
                if not hasattr(context, 'media_files') or context.media_files is None:
                    context.media_files = []
                # 将当前下载的文件添加到列表中
                context.media_files.extend(files)
                logger.info(f'已将 {len(files)} 个下载的媒体文件路径保存到context.media_files')

                # 添加发送者信息和消息文本
                caption_text = context.sender_info + context.message_text

                # 如果有超限文件，添加提示信息
                for message, size, name in context.skipped_media:
                    caption_text += f"\n\n⚠️ 媒体文件 {name if name else '未命名文件'} ({size}MB) 超过大小限制"

                if context.skipped_media:
                    channel_id_for_url = extract_channel_id_for_url(event.chat_id)
                    primary_message_id = getattr(context.primary_message, 'id', None) or event.message.id
                    context.original_link = f"\n原始消息: https://t.me/c/{channel_id_for_url}/{primary_message_id}"
                # 添加时间信息和原始链接
                caption_text += context.time_info + context.original_link

                # 作为一个组发送所有文件
                sent_messages = await client.send_file(
                    target_chat_id,
                    files,
                    caption=caption_text,
                    parse_mode=parse_mode,
                    buttons=context.buttons,
                    link_preview={
                        PreviewMode.ON: True,
                        PreviewMode.OFF: False,
                        PreviewMode.FOLLOW: context.event.message.media is not None
                    }[rule.is_preview]
                )
                # 保存发送的消息到上下文
                if isinstance(sent_messages, list):
                    context.forwarded_messages = sent_messages
                else:
                    context.forwarded_messages = [sent_messages]

                logger.info(f'媒体组消息已发送，保存了 {len(context.forwarded_messages)} 条已转发消息')
            else:
                if context.skipped_media and rule.is_send_over_media_size_message:
                    logger.info('媒体组所有媒体超限且开启提醒，发送超限提示')
                    caption_text = context.sender_info + (context.message_text or '')
                    for _message, size, name in context.skipped_media:
                        caption_text += f"\n\n媒体文件 {name if name else '未命名文件'} ({size}MB) 超过大小限制"
                    caption_text += context.time_info + context.original_link
                    sent_message = await client.send_message(
                        target_chat_id,
                        caption_text,
                        parse_mode=parse_mode,
                        link_preview=True,
                        buttons=context.buttons
                    )
                    context.forwarded_messages = [sent_message]
                elif context.message_text:
                    logger.info('媒体组所有媒体被屏蔽但有文本，降级发送纯文本消息')
                    await self._send_text_message(context, target_chat_id, parse_mode)
                else:
                    logger.info('媒体组所有媒体被屏蔽且无文本内容，不发送消息')
        except Exception as e:
            logger.error(f'发送媒体组消息时出错: {str(e)}')
            raise
        finally:
            # 删除临时文件
            for file_path in files:
                try:
                    os.remove(file_path)
                    logger.info(f'删除临时文件: {file_path}')
                except Exception as e:
                    logger.error(f'删除临时文件失败: {str(e)}')

    async def _send_single_media(self, context, target_chat_id, parse_mode):
        """发送单条媒体消息"""
        rule = context.rule
        client = context.client
        event = context.event

        logger.info(f'发送单条媒体消息')

        # 检查是否所有媒体都超限
        if context.skipped_media and not context.media_files:
            # 构建提示信息
            file_size = context.skipped_media[0][1]
            file_name = context.skipped_media[0][2]
            channel_id_for_url = extract_channel_id_for_url(event.chat_id)
            primary_message_id = getattr(context.primary_message, 'id', None) or event.message.id
            original_link = f"\n原始消息: https://t.me/c/{channel_id_for_url}/{primary_message_id}"

            text_to_send = context.message_text or ''
            text_to_send += f"\n\n⚠️ 媒体文件 {file_name} ({file_size}MB) 超过大小限制"
            text_to_send = context.sender_info + text_to_send + context.time_info

            text_to_send += original_link

            sent_message = await client.send_message(
                target_chat_id,
                text_to_send,
                parse_mode=parse_mode,
                link_preview=True,
                buttons=context.buttons
            )
            context.forwarded_messages = [sent_message]
            logger.info(f'媒体文件超过大小限制，仅转发文本')
            return

        # 确保context.media_files存在
        if not hasattr(context, 'media_files') or context.media_files is None:
            context.media_files = []

        # 发送媒体文件
        for file_path in context.media_files:
            try:
                caption = (
                    context.sender_info +
                    context.message_text +
                    context.time_info +
                    context.original_link
                )

                sent_message = await client.send_file(
                    target_chat_id,
                    file_path,
                    caption=caption,
                    parse_mode=parse_mode,
                    buttons=context.buttons,
                    link_preview={
                        PreviewMode.ON: True,
                        PreviewMode.OFF: False,
                        PreviewMode.FOLLOW: context.event.message.media is not None
                    }[rule.is_preview]
                )
                context.forwarded_messages = [sent_message]
                logger.info(f'媒体消息已发送')
            except Exception as e:
                logger.error(f'发送媒体消息时出错: {str(e)}')
                raise
            finally:
                try:
                    os.remove(file_path)
                    logger.info(f'删除临时文件: {file_path}')
                except Exception as e:
                    logger.error(f'删除临时文件失败: {str(e)}')

    async def _send_text_message(self, context, target_chat_id, parse_mode):
        """发送纯文本消息"""
        rule = context.rule
        client = context.client

        # 组合消息文本
        message_text = context.sender_info + context.message_text + context.time_info + context.original_link
        if not message_text:
            logger.info('没有文本内容，不发送消息')
            return

        # 根据预览模式设置 link_preview
        link_preview = {
            PreviewMode.ON: True,
            PreviewMode.OFF: False,
            PreviewMode.FOLLOW: context.event.message.media is not None  # 跟随原消息
        }[rule.is_preview]

        sent_message = await client.send_message(
            target_chat_id,
            str(message_text),
            parse_mode=parse_mode,
            link_preview=link_preview,
            buttons=context.buttons
        )
        context.forwarded_messages = [sent_message]
        logger.info(f'{"带预览的" if link_preview else "无预览的"}文本消息已发送')