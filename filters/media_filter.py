import logging
import os
import asyncio
from utils.media import get_media_size
from utils.constants import TEMP_DIR
from utils.common import get_db_ops, collect_media_group_messages, select_primary_media_group_message
from filters.base_filter import BaseFilter
from models.models import MediaTypes
from models.models import get_db_session
from enums.enums import AddMode
logger = logging.getLogger(__name__)

class MediaFilter(BaseFilter):
    """
    媒体过滤器，处理消息中的媒体内容
    """

    async def _process(self, context):
        """
        处理媒体内容

        Args:
            context: 消息上下文

        Returns:
            bool: 是否继续处理
        """
        # 确保临时目录存在
        os.makedirs(TEMP_DIR, exist_ok=True)

        event = context.event

        # 如果是媒体组消息
        if event.message.grouped_id:
            await self._process_media_group(context)
        else:
            await self._process_single_media(context)

        return True

    async def _process_media_group(self, context):
        """处理媒体组消息"""
        event = context.event
        rule = context.rule

        logger.info(f'处理媒体组消息 组ID: {event.message.grouped_id}')

        media_group_messages = await collect_media_group_messages(
            event.client,
            event.chat_id,
            event.message.grouped_id,
        )

        # 获取媒体类型设置
        media_types = None
        if rule.enable_media_type_filter:
            with get_db_session() as session:
                media_types = session.query(MediaTypes).filter_by(rule_id=rule.id).first()

        context.media_group_messages = []
        context.ai_media_messages = []

        # 收集媒体组的所有消息
        total_media_count = 0  # 总媒体数量
        blocked_media_count = 0  # 被屏蔽的媒体数量
        try:
            for message in media_group_messages:
                if message.media:
                    total_media_count += 1
                    if rule.enable_media_type_filter and media_types and message.media:
                        if await self._is_media_type_blocked(message.media, media_types):
                            logger.info(f'媒体类型被屏蔽，跳过消息 ID={message.id}')
                            context.blocked_media_message_ids.add(message.id)
                            blocked_media_count += 1
                            continue

                    if rule.enable_extension_filter and message.media:
                        if not await self._is_media_extension_allowed(rule, message.media):
                            logger.info(f'媒体扩展名被屏蔽，跳过消息 ID={message.id}')
                            context.blocked_media_message_ids.add(message.id)
                            blocked_media_count += 1
                            continue

                if message.media:
                    file_size = await get_media_size(message.media)
                    file_size = round(file_size/1024/1024, 2)
                    logger.info(f'媒体文件大小: {file_size}MB')
                    logger.info(f'规则最大媒体大小: {rule.max_media_size}MB')
                    logger.info(f'是否启用媒体大小过滤: {rule.enable_media_size_filter}')
                    logger.info(f'是否发送媒体大小超限提醒: {rule.is_send_over_media_size_message}')

                    if rule.max_media_size and (file_size > rule.max_media_size) and rule.enable_media_size_filter:
                        context.blocked_media_message_ids.add(message.id)
                        file_name = ''
                        if hasattr(message.media, 'document') and message.media.document:
                            for attr in message.media.document.attributes:
                                if hasattr(attr, 'file_name'):
                                    file_name = attr.file_name
                                    break
                        logger.info(f'媒体文件 {file_name} 超过大小限制 ({rule.max_media_size}MB)')
                        context.skipped_media.append((message, file_size, file_name))
                        continue

                if rule.media_caption_filter and not message.text:
                    logger.info(f'Caption过滤开启，消息无caption，跳过 ID={message.id}')
                    context.blocked_media_message_ids.add(message.id)
                    blocked_media_count += 1
                    continue

                context.media_group_messages.append(message)
                if message.photo or (message.document and getattr(message.document, 'mime_type', '').startswith('image/')):
                    context.ai_media_messages.append(message)
                logger.info(f'找到媒体组消息: ID={message.id}, 类型={type(message.media).__name__ if message.media else "无媒体"}')
        except Exception as e:
            logger.error(f'收集媒体组消息时出错: {str(e)}')
            context.errors.append(f"收集媒体组消息错误: {str(e)}")

        logger.info(f'共找到 {len(context.media_group_messages)} 条媒体组消息，{len(context.skipped_media)} 条超限')

        if context.media_group_messages:
            primary_message = select_primary_media_group_message(
                context.media_group_messages,
                require_caption=rule.media_caption_filter,
            ) or context.media_group_messages[0]
            context.primary_message = primary_message
            primary_text = primary_message.text or ''
            context.message_text = primary_text
            context.check_message_text = primary_text
            context.buttons = primary_message.buttons if hasattr(primary_message, 'buttons') else None

        # 如果所有媒体都被屏蔽，设置不转发
        if total_media_count > 0 and total_media_count == blocked_media_count:
            logger.info('媒体组中所有媒体都被屏蔽，设置不转发')
            # 检查是否允许文本通过
            if rule.media_allow_text:
                logger.info('媒体被屏蔽但允许文本通过')
                context.media_blocked = True  # 标记媒体被屏蔽
            else:
                context.should_forward = False
            return True

        # 如果所有媒体都超限且不发送超限提醒，则设置不转发
        if context.skipped_media and len(context.media_group_messages) == 0 and not rule.is_send_over_media_size_message:
            # 检查是否允许文本通过
            if rule.media_allow_text:
                logger.info('媒体超限但允许文本通过')
                context.media_blocked = True  # 标记媒体被屏蔽
            else:
                context.should_forward = False
                logger.info('所有媒体都超限且不发送超限提醒，设置不转发')

    async def _process_single_media(self, context):
        """处理单条媒体消息"""
        event = context.event
        rule = context.rule
        # logger.info(f'context属性: {context.rule.__dict__}')
        # 检查是否是纯链接预览消息
        is_pure_link_preview = (
            event.message.media and
            hasattr(event.message.media, 'webpage') and
            not any([
                getattr(event.message.media, 'photo', None),
                getattr(event.message.media, 'document', None),
                getattr(event.message.media, 'video', None),
                getattr(event.message.media, 'audio', None),
                getattr(event.message.media, 'voice', None)
            ])
        )

        # 检查是否有实际媒体
        has_media = (
            event.message.media and
            any([
                getattr(event.message.media, 'photo', None),
                getattr(event.message.media, 'document', None),
                getattr(event.message.media, 'video', None),
                getattr(event.message.media, 'audio', None),
                getattr(event.message.media, 'voice', None)
            ])
        )

        # 处理实际媒体
        if has_media:
            # 检查媒体类型是否被屏蔽
            if rule.enable_media_type_filter:
                with get_db_session() as session:
                    media_types = session.query(MediaTypes).filter_by(rule_id=rule.id).first()
                    if media_types and await self._is_media_type_blocked(event.message.media, media_types):
                        logger.info(f'媒体类型被屏蔽，跳过消息 ID={event.message.id}')
                        context.blocked_media_message_ids.add(event.message.id)
                        # 检查是否允许文本通过
                        if rule.media_allow_text:
                            logger.info('媒体被屏蔽但允许文本通过')
                            context.media_blocked = True  # 标记媒体被屏蔽
                        else:
                            context.should_forward = False
                        return True

            # 检查媒体扩展名
            if rule.enable_extension_filter and event.message.media:
                if not await self._is_media_extension_allowed(rule, event.message.media):
                    logger.info(f'媒体扩展名被屏蔽，跳过消息 ID={event.message.id}')
                    context.blocked_media_message_ids.add(event.message.id)
                    # 检查是否允许文本通过
                    if rule.media_allow_text:
                        logger.info('媒体被屏蔽但允许文本通过')
                        context.media_blocked = True  # 标记媒体被屏蔽
                    else:
                        context.should_forward = False
                    return True

            if rule.media_caption_filter and not event.message.text:
                logger.info(f'Caption过滤开启，单条媒体消息无caption，跳过 ID={event.message.id}')
                context.blocked_media_message_ids.add(event.message.id)
                context.should_forward = False
                return True

            # 检查媒体大小
            file_size = await get_media_size(event.message.media)
            file_size = round(file_size/1024/1024, 2)
            logger.info(f'event.message.document: {event.message.document}')

            logger.info(f'媒体文件大小: {file_size}MB')
            logger.info(f'规则最大媒体大小: {rule.max_media_size}MB')

            logger.info(f'是否启用媒体大小过滤: {rule.enable_media_size_filter}')
            if rule.max_media_size and (file_size > rule.max_media_size) and rule.enable_media_size_filter:
                context.blocked_media_message_ids.add(event.message.id)
                file_name = ''
                if event.message.document:
                    # 正确地从文档属性中获取文件名
                    for attr in event.message.document.attributes:
                        if hasattr(attr, 'file_name'):
                            file_name = attr.file_name
                            break

                logger.info(f'媒体文件超过大小限制 ({rule.max_media_size}MB)')
                context.skipped_media.append((event.message, file_size, file_name))
                if rule.is_send_over_media_size_message:
                    logger.info(f'是否发送媒体大小超限提醒: {rule.is_send_over_media_size_message}')
                    context.should_forward = True
                else:
                    # 检查是否允许文本通过
                    if rule.media_allow_text:
                        logger.info('媒体超限但允许文本通过')
                        context.media_blocked = True  # 标记媒体被屏蔽
                    else:
                        context.should_forward = False
                return True  # 跳过后续的媒体下载
            else:
                try:
                    # 下载媒体文件
                    file_path = await event.message.download_media(TEMP_DIR)
                    if file_path:
                        context.media_files.append(file_path)
                        logger.info(f'媒体文件已下载到: {file_path}')
                except Exception as e:
                    logger.error(f'下载媒体文件时出错: {str(e)}')
                    context.errors.append(f"下载媒体文件错误: {str(e)}")
        elif is_pure_link_preview:
            # 记录这是纯链接预览消息
            context.is_pure_link_preview = True
            logger.info('这是一条纯链接预览消息')

    async def _is_media_type_blocked(self, media, media_types):
        if getattr(media, 'photo', None) and media_types.photo:
            logger.info('媒体类型为图片，已被屏蔽')
            return True

        document = getattr(media, 'document', None)
        if not document:
            return False

        has_specific_media_type = False
        for attr in getattr(document, 'attributes', []):
            attr_type = type(attr).__name__
            if attr_type == 'DocumentAttributeVideo':
                has_specific_media_type = True
                if media_types.video:
                    logger.info('媒体类型为视频，已被屏蔽')
                    return True
            if attr_type == 'DocumentAttributeAudio':
                has_specific_media_type = True
                if getattr(attr, 'voice', None) and media_types.voice:
                    logger.info('媒体类型为语音，已被屏蔽')
                    return True
                if not getattr(attr, 'voice', None) and media_types.audio:
                    logger.info('媒体类型为音频，已被屏蔽')
                    return True

        if has_specific_media_type:
            return False

        if media_types.document:
            logger.info('媒体类型为文档，已被屏蔽')
            return True

        return False

    async def _is_media_extension_allowed(self, rule, media):
        if not rule.enable_extension_filter:
            return True

        if not getattr(media, 'document', None):
            logger.info("媒体没有document属性，跳过扩展名检查")
            return True

        file_name = None

        for attr in media.document.attributes:
            if hasattr(attr, 'file_name'):
                file_name = attr.file_name
                break


        if not file_name:
            logger.info("无法获取文件名，无法判断扩展名")
            return True

        # 提取扩展名
        _, extension = os.path.splitext(file_name)
        extension = extension.lstrip('.').lower()  # 移除点号并转为小写

        # 特殊处理：如果文件没有扩展名，将extension设为特殊值"无扩展名"
        if not extension:
            logger.info(f"文件 {file_name} 没有扩展名")
            extension = "无扩展名"
        else:
            logger.info(f"文件 {file_name} 的扩展名: {extension}")

        # 获取规则中保存的扩展名列表
        db_ops = await get_db_ops()
        allowed = True
        try:
            with get_db_session() as session:
                # 使用db_operations中的函数获取扩展名列表
                extensions = await db_ops.get_media_extensions(session, rule.id)
                extension_list = [ext["extension"].lower() for ext in extensions]

                # 判断是否允许该扩展名
                if rule.extension_filter_mode == AddMode.BLACKLIST:
                    # 黑名单模式：如果扩展名在列表中，则不允许
                    if extension in extension_list:
                        logger.info(f"扩展名 {extension} 在黑名单中，不允许")
                        allowed = False
                    else:
                        logger.info(f"扩展名 {extension} 不在黑名单中，允许")
                        allowed = True
                else:
                    # 白名单模式：如果扩展名不在列表中，则不允许
                    if extension in extension_list:
                        logger.info(f"扩展名 {extension} 在白名单中，允许")
                        allowed = True
                    else:
                        logger.info(f"扩展名 {extension} 不在白名单中，不允许")
                        allowed = False
        except Exception as e:
            logger.error(f"检查媒体扩展名时出错: {str(e)}")
            allowed = False  # 出错时默认拒绝，保障安全

        return allowed

