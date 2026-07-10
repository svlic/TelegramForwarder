import importlib
import os
import sys
import logging
from telethon.tl import types
from telethon.tl.types import ChannelParticipantsAdmins
from enums.enums import ForwardMode
from models.models import Chat, ForwardRule
from typing import Iterable
import re
from utils.auto_delete import reply_and_delete
from datetime import datetime, timedelta
import asyncio

from utils.constants import AI_SETTINGS_TEXT,MEDIA_SETTINGS_TEXT
from utils.regex_safety import RegexTimeoutError, safe_re_search

logger = logging.getLogger(__name__)


def get_telegram_chat_db_id(entity_or_chat_id):
    if isinstance(entity_or_chat_id, types.Channel):
        return str(normalize_channel_id(entity_or_chat_id.id))

    if hasattr(entity_or_chat_id, 'id'):
        entity_or_chat_id = entity_or_chat_id.id

    chat_id = int(entity_or_chat_id)
    if str(chat_id).startswith('-100'):
        return str(chat_id)
    if str(chat_id).startswith('100'):
        return str(normalize_channel_id(chat_id))
    if chat_id < 0:
        return str(chat_id)
    return str(chat_id)


def normalize_channel_id(chat_id):
    """Normalize channel/supergroup ID to -100XXXXXXXXX format"""
    chat_id_str = str(chat_id)
    if chat_id_str.startswith('-100'):
        return int(chat_id_str)
    elif chat_id_str.startswith('100'):
        return int(f'-{chat_id_str}')
    elif not chat_id_str.startswith('-'):
        return int(f'-100{chat_id_str}')
    return int(chat_id_str)


def normalize_state_chat_id(chat_id):
    chat_id_int = int(chat_id)
    chat_id_str = str(chat_id_int)
    if chat_id_str.startswith('-100') or chat_id_str.startswith('100'):
        return normalize_channel_id(chat_id_int)
    if chat_id_int < 0:
        return chat_id_int
    return abs(chat_id_int)


def get_state_identity(event):
    chat_id = getattr(event, 'chat_id', None)
    if chat_id is None:
        raise ValueError('event.chat_id is required for state identity')

    normalized_chat_id = normalize_state_chat_id(chat_id)
    chat = getattr(event, 'chat', None)
    sender_id = getattr(event, 'sender_id', None)

    if isinstance(chat, types.Channel):
        if sender_id is not None:
            return sender_id, normalize_channel_id(normalized_chat_id)

        user_id = os.getenv('USER_ID')
        if not user_id:
            raise ValueError('USER_ID is required when channel sender_id is unavailable')
        return int(user_id), normalize_channel_id(normalized_chat_id)

    if sender_id is None:
        raise ValueError('event.sender_id is required for non-channel state identity')
    return sender_id, normalized_chat_id


def extract_channel_id_for_url(chat_id):
    """Extract pure channel ID for t.me/c/{id} URLs (strips -100 prefix)"""
    normalized = normalize_channel_id(chat_id)
    normalized_str = str(normalized)
    if normalized_str.startswith('-100'):
        return normalized_str[4:]
    return normalized_str


async def collect_media_group_messages(client, chat_id, grouped_id, *, wait_seconds=1.5, max_empty_polls=3):
    if not grouped_id:
        return []

    collected = {}
    empty_polls = 0

    for _ in range(max_empty_polls):
        await asyncio.sleep(wait_seconds)
        batch = await client.get_messages(chat_id, limit=100)
        matched = [message for message in batch if getattr(message, 'grouped_id', None) == grouped_id]

        if not matched:
            empty_polls += 1
            continue

        empty_polls = 0
        for message in matched:
            collected[message.id] = message

        if len(matched) < 10:
            break

    return sorted(collected.values(), key=lambda message: message.id)


def select_primary_media_group_message(messages, *, require_caption=False):
    if not messages:
        return None

    candidates = [message for message in messages if getattr(message, 'text', None)]
    if require_caption:
        return candidates[0] if candidates else None
    return candidates[0] if candidates else messages[0]

async def get_main_module():
    """获取 main 模块"""
    try:
        return sys.modules['__main__']
    except KeyError:
        # 如果找不到 main 模块，尝试手动导入
        spec = importlib.util.spec_from_file_location(
            "main",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")
        )
        main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main)
        return main

async def get_bot_client():
    """获取机器人客户端"""
    main = await get_main_module()
    return main.bot_client

async def get_db_ops():
    """获取 main.py 中的 db_ops 实例"""
    main = await get_main_module()
    if main.db_ops is None:
        main.db_ops = await main.init_db_ops()
    return main.db_ops


def _chat_display_name(entity):
    if hasattr(entity, 'title') and entity.title:
        return entity.title
    first = getattr(entity, 'first_name', None) or ''
    last = getattr(entity, 'last_name', None) or ''
    combined = f'{first} {last}'.strip()
    return combined or '私聊'


async def resolve_bind_chat_ref(client, ref: str):
    """Resolve /bind argument to Telethon entity."""
    ref = (ref or '').strip()
    if not ref:
        raise ValueError('聊天引用不能为空')

    if ref.lstrip('-').isdigit():
        return await client.get_entity(int(ref))

    if ref.startswith('https://') or ref.startswith('http://'):
        return await client.get_entity(ref)

    if ref.startswith('t.me/'):
        return await client.get_entity(f'https://{ref}')

    return await client.get_entity(ref)


def get_or_create_chat_row(session, entity) -> Chat:
    """Persist Chat row using the same telegram_chat_id format as /bind and listeners."""
    telegram_chat_id = get_telegram_chat_db_id(entity)
    chat_row = session.query(Chat).filter(Chat.telegram_chat_id == telegram_chat_id).first()
    if chat_row:
        name = _chat_display_name(entity)
        if name and chat_row.name != name:
            chat_row.name = name
        return chat_row

    chat_row = Chat(
        telegram_chat_id=telegram_chat_id,
        name=_chat_display_name(entity),
    )
    session.add(chat_row)
    session.flush()
    return chat_row


async def get_user_id():
    """获取用户ID，确保环境变量已加载"""
    user_id_str = os.getenv('USER_ID')
    if not user_id_str:
        logger.error('未设置 USER_ID 环境变量')
        raise ValueError('必须在 .env 文件中设置 USER_ID')
    return int(user_id_str)


async def get_current_rule(session, event):
    """获取当前选中的规则"""
    try:
        # 获取当前聊天
        current_chat = await event.get_chat()
        logger.info(f'获取当前聊天: {current_chat.id}')

        current_chat_db = session.query(Chat).filter(
            Chat.telegram_chat_id == get_telegram_chat_db_id(current_chat)
        ).first()

        if not current_chat_db or not current_chat_db.current_add_id:
            logger.info('未找到当前聊天或未选择源聊天')
            await reply_and_delete(event,'请先使用 /switch 选择一个源聊天')
            return None

        logger.info(f'当前选中的源聊天ID: {current_chat_db.current_add_id}')

        # 查找对应的规则
        source_chat = session.query(Chat).filter(
            Chat.telegram_chat_id == current_chat_db.current_add_id
        ).first()

        if source_chat:
            logger.info(f'找到源聊天: {source_chat.name}')
        else:
            logger.error('未找到源聊天')
            return None

        rule = session.query(ForwardRule).filter(
            ForwardRule.source_chat_id == source_chat.id,
            ForwardRule.target_chat_id == current_chat_db.id
        ).first()

        if not rule:
            logger.info('未找到对应的转发规则')
            await reply_and_delete(event,'转发规则不存在')
            return None

        logger.info(f'找到转发规则 ID: {rule.id}')
        return rule, source_chat
    except Exception as e:
        logger.error(f'获取当前规则时出错: {str(e)}')
        logger.exception(e)
        await reply_and_delete(event,'获取当前规则时出错，请检查日志')
        return None


async def get_all_rules(session, event):
    """获取当前聊天的所有规则"""
    try:
        # 获取当前聊天
        current_chat = await event.get_chat()
        logger.info(f'获取当前聊天: {current_chat.id}')

        current_chat_db = session.query(Chat).filter(
            Chat.telegram_chat_id == get_telegram_chat_db_id(current_chat)
        ).first()

        if not current_chat_db:
            logger.info('未找到当前聊天')
            await reply_and_delete(event,'当前聊天没有任何转发规则')
            return None

        logger.info(f'找到当前聊天数据库记录 ID: {current_chat_db.id}')

        # 查找所有以当前聊天为目标的规则
        rules = session.query(ForwardRule).filter(
            ForwardRule.target_chat_id == current_chat_db.id
        ).all()

        if not rules:
            logger.info('未找到任何转发规则')
            await reply_and_delete(event,'当前聊天没有任何转发规则')
            return None

        logger.info(f'找到 {len(rules)} 条转发规则')
        return rules
    except Exception as e:
        logger.error(f'获取所有规则时出错: {str(e)}')
        logger.exception(e)
        await reply_and_delete(event,'获取规则时出错，请检查日志')
        return None


async def get_manageable_rules(session, event):
    current_chat = await event.get_chat()
    current_chat_db = session.query(Chat).filter(
        Chat.telegram_chat_id == get_telegram_chat_db_id(current_chat)
    ).first()

    if not current_chat_db:
        return []

    return session.query(ForwardRule).filter(
        ForwardRule.target_chat_id == current_chat_db.id
    ).all()


async def rule_belongs_to_current_chat(session, event, rule_id):
    try:
        normalized_rule_id = int(rule_id)
    except (TypeError, ValueError):
        return False

    manageable_rule_ids = {
        rule.id for rule in await get_manageable_rules(session, event)
    }
    return normalized_rule_id in manageable_rule_ids


async def all_rules_belong_to_current_chat(session, event, rule_ids: Iterable[int]):
    try:
        normalized_rule_ids = {int(rule_id) for rule_id in rule_ids}
    except (TypeError, ValueError):
        return False

    manageable_rule_ids = {
        rule.id for rule in await get_manageable_rules(session, event)
    }
    return normalized_rule_ids.issubset(manageable_rule_ids)


# 添加缓存字典
_admin_cache = {}
_admin_cache_lock = asyncio.Lock()
_CACHE_DURATION = timedelta(minutes=30)  # 缓存30分钟



async def get_channel_admins(client, chat_id):
    """获取频道管理员列表，带缓存机制"""
    current_time = datetime.now()

    async with _admin_cache_lock:
        if chat_id in _admin_cache:
            cache_data = _admin_cache[chat_id]
            if current_time - cache_data['timestamp'] < _CACHE_DURATION:
                return cache_data['admin_ids'].copy()

        try:
            admins = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
            admin_ids = [admin.id for admin in admins]

            _admin_cache[chat_id] = {
                'admin_ids': admin_ids,
                'timestamp': current_time
            }
            return admin_ids
        except Exception as e:
            logger.error(f'获取频道管理员列表失败: {str(e)}')
            return None

async def is_admin(event):
    """检查用户是否为频道/群组管理员

    Args:
        event: 事件对象
    Returns:
        bool: 是否是管理员
    """
    try:
        # 获取所有机器人管理员列表
        bot_admins = get_admin_list()

        # 检查是否有message属性
        if not hasattr(event, 'message'):
            # 没有message属性,是回调处理
            if event.sender_id in bot_admins:
                return True
            else:
                logger.info(f'用户 {event.sender_id} 非管理员，操作已被忽略')
                return False

        message = event.message
        main = await get_main_module()
        client = main.user_client



        if message.is_channel and not message.is_group:
            user_id = getattr(event, 'sender_id', None)
            if user_id is None:
                logger.info('频道事件缺少 sender_id，拒绝管理员操作')
                return False

            if user_id not in bot_admins:
                logger.info(f'用户 {user_id} 不在管理员列表中，已忽略')
                return False

            # 获取频道管理员列表（使用缓存）
            channel_admins = await get_channel_admins(client, event.chat_id)
            if channel_admins is None:
                return False

            if user_id not in channel_admins:
                logger.info(f'用户 {user_id} 不在频道管理员列表中，已忽略')
                return False
            return True
        else:
            # 检查发送者ID
            user_id = event.sender_id  # 使用 sender_id 作为主要ID来源
            logger.info(f'发送者ID：{user_id}')

            bot_admins = get_admin_list()
            # 检查是否是机器人管理员
            if user_id not in bot_admins:
                logger.info('非管理员的消息，已忽略')
                return False
            return True
    except Exception as e:
        logger.error(f"检查管理员权限时出错: {str(e)}")
        return False

async def get_media_settings_text():
    """生成媒体设置页面的文本"""
    return MEDIA_SETTINGS_TEXT

async def get_ai_settings_text(rule):
    """生成AI设置页面的文本"""
    ai_prompt = rule.ai_prompt or os.getenv('DEFAULT_AI_PROMPT', '未设置')
    summary_prompt = rule.summary_prompt or os.getenv('DEFAULT_SUMMARY_PROMPT', '未设置')

    def summarize_prompt(prompt_value):
        if not prompt_value or prompt_value == '未设置':
            return '未设置'
        return f'已配置（长度 {len(prompt_value)}）'

    return AI_SETTINGS_TEXT.format(
        ai_prompt=summarize_prompt(ai_prompt),
        summary_prompt=summarize_prompt(summary_prompt)
    )

async def get_sender_info(event, rule_id):
    """Resolve display name for keyword matching when is_filter_user_info is enabled."""
    try:
        logger.info("开始获取发送者信息")
        sender_name = None

        if hasattr(event.message, 'sender_chat') and event.message.sender_chat:
            sender = event.message.sender_chat
            sender_name = sender.title if hasattr(sender, 'title') else None
            logger.info(f"使用频道信息: {sender_name}")

        elif event.sender:
            sender = event.sender
            sender_name = getattr(sender, 'title', None) or (
                f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip()
            )
            logger.info(f"使用发送者信息: {sender_name}")

        elif hasattr(event.message, 'peer_id') and event.message.peer_id:
            peer = event.message.peer_id
            if hasattr(peer, 'channel_id'):
                try:
                    channel = await event.client.get_entity(peer)
                    sender_name = channel.title if hasattr(channel, 'title') else None
                    logger.info(f"使用peer_id信息: {sender_name}")
                except Exception as ce:
                    logger.error(f'获取频道信息失败: {str(ce)}')

        if sender_name:
            return sender_name
        logger.warning(f"规则 ID: {rule_id} - 无法获取发送者信息")
        return None

    except Exception as e:
        logger.error(f'获取发送者信息出错: {str(e)}')
        return None

async def check_and_clean_chats(session, rule=None):
    """
    检查并清理不再与任何规则关联的聊天记录

    Args:
        session: 数据库会话
        rule: 被删除的规则对象（可选），如果提供则从中获取聊天ID

    Returns:
        int: 删除的聊天记录数量
    """
    deleted_count = 0

    try:
        # 获取所有聊天ID
        chat_ids_to_check = set()

        # 如果提供了规则，先检查这些受影响的聊天
        if rule:
            if rule.source_chat_id:
                chat_ids_to_check.add(rule.source_chat_id)
            if rule.target_chat_id:
                chat_ids_to_check.add(rule.target_chat_id)
        else:
            # 如果没有提供规则，则获取所有聊天
            all_chats = session.query(Chat.id).all()
            chat_ids_to_check = set(chat[0] for chat in all_chats)

        # 对每个聊天ID进行检查
        for chat_id in chat_ids_to_check:
            # 检查此聊天是否还被任何规则引用
            as_source = session.query(ForwardRule).filter(
                ForwardRule.source_chat_id == chat_id
            ).count()

            as_target = session.query(ForwardRule).filter(
                ForwardRule.target_chat_id == chat_id
            ).count()

            # 如果聊天不再被任何规则引用
            if as_source == 0 and as_target == 0:
                chat = session.get(Chat, chat_id)
                if chat:
                    # 获取telegram_chat_id以便日志记录
                    telegram_chat_id = chat.telegram_chat_id
                    name = chat.name or "未命名聊天"

                    # 清理所有引用此聊天作为current_add_id的记录
                    chats_using_this = session.query(Chat).filter(
                        Chat.current_add_id == telegram_chat_id
                    ).all()

                    for other_chat in chats_using_this:
                        other_chat.current_add_id = None
                        logger.info(f'清除聊天 {other_chat.name} 的current_add_id设置')

                    # 删除聊天记录
                    session.delete(chat)
                    logger.info(f'删除未使用的聊天: {name} (ID: {telegram_chat_id})')
                    deleted_count += 1

        # 如果有删除操作，提交更改
        if deleted_count > 0:
            session.commit()
            logger.info(f'共清理了 {deleted_count} 个未使用的聊天记录')

        return deleted_count

    except Exception as e:
        logger.error(f'检查和清理聊天记录时出错: {str(e)}')
        session.rollback()
        return 0

def get_admin_list():
    """获取管理员ID列表，如果ADMINS为空则使用USER_ID"""
    admin_str = os.getenv('ADMINS', '')
    if not admin_str:
        user_id = os.getenv('USER_ID')
        if not user_id:
            logger.error('未设置 USER_ID 环境变量')
            raise ValueError('必须在 .env 文件中设置 USER_ID')
        return [int(user_id)]
    return [int(admin.strip()) for admin in admin_str.split(',') if admin.strip()]




async def check_keywords(rule, message_text, event = None):
    # Handle None or empty message text
    if not message_text:
        message_text = ""

    # 处理用户信息过滤
    if rule.is_filter_user_info and event:
        message_text = await process_user_info(event, rule.id, message_text)

    logger.info("开始检查关键字规则")
    logger.info(f"当前转发模式: {rule.forward_mode}")
    forward_mode = rule.forward_mode

    # 计算有效的白名单和黑名单关键词（反转=类型翻转合并到同级）
    base_whitelist = [k for k in rule.keywords if not k.is_blacklist]
    base_blacklist = [k for k in rule.keywords if k.is_blacklist]

    # 反转逻辑：反转后合并到同级，不再双层
    if rule.enable_reverse_blacklist:
        # 黑名单反转为白名单，合并到白名单
        effective_whitelist = base_whitelist + base_blacklist
        effective_blacklist = []
        logger.info(f"黑名单已反转并合并到白名单，有效白名单数量: {len(effective_whitelist)}")
    elif rule.enable_reverse_whitelist:
        # 白名单反转为黑名单，合并到黑名单
        effective_whitelist = []
        effective_blacklist = base_blacklist + base_whitelist
        logger.info(f"白名单已反转并合并到黑名单，有效黑名单数量: {len(effective_blacklist)}")
    else:
        effective_whitelist = base_whitelist
        effective_blacklist = base_blacklist
        logger.info(f"有效白名单关键词数量: {len(effective_whitelist)}")
        logger.info(f"有效黑名单关键词数量: {len(effective_blacklist)}")

    # 仅白名单模式
    if forward_mode == ForwardMode.WHITELIST:
        return await process_whitelist_mode(effective_whitelist, message_text)

    # 仅黑名单模式
    elif forward_mode == ForwardMode.BLACKLIST:
        return await process_blacklist_mode(effective_blacklist, message_text)

    # 先白后黑模式
    elif forward_mode == ForwardMode.WHITELIST_THEN_BLACKLIST:
        return await process_whitelist_then_blacklist_mode(effective_whitelist, effective_blacklist, message_text)

    # 先黑后白模式
    elif forward_mode == ForwardMode.BLACKLIST_THEN_WHITELIST:
        return await process_blacklist_then_whitelist_mode(effective_blacklist, effective_whitelist, message_text)

    logger.error(f"未知的转发模式: {forward_mode}")
    return False

async def process_whitelist_mode(whitelist_keywords, message_text):
    """处理仅白名单模式"""
    logger.info("进入仅白名单模式")

    if not whitelist_keywords:
        logger.info("白名单为空，不转发")
        return False

    for keyword in whitelist_keywords:
        if await check_keyword_match(keyword, message_text):
            logger.info("匹配到白名单关键词，允许转发")
            return True

    logger.info("未匹配到任何白名单关键词，不转发")
    return False

async def process_blacklist_mode(blacklist_keywords, message_text):
    """处理仅黑名单模式"""
    logger.info("进入仅黑名单模式")

    for keyword in blacklist_keywords:
        if await check_keyword_match(keyword, message_text):
            logger.info("匹配到黑名单关键词，不转发")
            return False

    logger.info("未匹配到任何黑名单关键词，允许转发")
    return True

async def check_keyword_match(keyword, message_text):
    """检查单个关键词是否匹配"""
    logger.info(f"检查关键字，正则模式: {keyword.is_regex}")
    if keyword.is_regex:
        try:
            if safe_re_search(keyword.keyword, message_text):
                logger.info("正则匹配成功")
                return True
        except RegexTimeoutError:
            logger.error("正则表达式超时: %s", keyword.keyword)
            return bool(keyword.is_blacklist)
        except re.error:
            logger.error("正则表达式错误: %s", keyword.keyword)
            return bool(keyword.is_blacklist)
    else:
        if keyword.keyword.lower() in message_text.lower():
            logger.info("关键字匹配成功")
            return True
    return False

async def process_user_info(event, rule_id, message_text):
    """Prefix message text with sender info for keyword matching."""
    username = await get_sender_info(event, rule_id)
    name = None

    if hasattr(event.message, 'sender_chat') and event.message.sender_chat:
        sender = event.message.sender_chat
        name = sender.title if hasattr(sender, 'title') else None
    elif event.sender:
        sender = event.sender
        name = getattr(sender, 'title', None) or (
            f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip()
        )

    if username and name:
        logger.info(f"成功获取用户信息: {username} {name}")
        return f"{username} {name}:\n{message_text}"
    if username:
        logger.info(f"成功获取用户信息: {username}")
        return f"{username}:\n{message_text}"
    if name:
        logger.info(f"成功获取用户信息: {name}")
        return f"{name}:\n{message_text}"
    logger.warning(f"规则 ID: {rule_id} - 无法获取发送者信息")
    return message_text


async def process_whitelist_then_blacklist_mode(whitelist_keywords, blacklist_keywords, message_text):
    logger.info("进入先白后黑模式")

    whitelist_match = False
    for keyword in whitelist_keywords:
        if await check_keyword_match(keyword, message_text):
            whitelist_match = True
            break

    if not whitelist_match:
        logger.info("未匹配到白名单关键词，不转发")
        return False

    for keyword in blacklist_keywords:
        if await check_keyword_match(keyword, message_text):
            logger.info("匹配到黑名单关键词，不转发")
            return False

    logger.info("所有条件都满足，允许转发")
    return True

async def process_blacklist_then_whitelist_mode(blacklist_keywords, whitelist_keywords, message_text):
    logger.info("进入先黑后白模式")

    for keyword in blacklist_keywords:
        if await check_keyword_match(keyword, message_text):
            logger.info("匹配到黑名单关键词，不转发")
            return False

    whitelist_match = False
    for keyword in whitelist_keywords:
        if await check_keyword_match(keyword, message_text):
            whitelist_match = True
            break

    if not whitelist_match:
        logger.info("未匹配到白名单关键词，不转发")
        return False

    logger.info("所有条件都满足，允许转发")
    return True
