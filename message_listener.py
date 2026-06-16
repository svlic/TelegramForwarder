from telethon import events
from models.models import get_db_session, Chat, ForwardRule
import logging
from handlers import bot_handler
from handlers.prompt_handlers import handle_prompt_setting
from handlers.command_handlers import perform_clear_all, CLEAR_ALL_CONFIRM_TEXT
from utils.common import is_admin
import asyncio
from managers.state_manager import state_manager
from filters.process import process_forward_rule
from utils.common import get_telegram_chat_db_id, get_state_identity
from utils.auto_delete import async_delete_user_message, reply_and_delete

# 加载环境变量
logger = logging.getLogger(__name__)

PROCESSED_GROUPS = {}
_PROCESSED_GROUPS_LOCK = asyncio.Lock()
_GROUP_CACHE_TTL = 300

BOT_ID = None


async def handle_clear_all_confirmation(event, sender_id, state_chat_id):
    await state_manager.clear_state(sender_id, state_chat_id)
    await async_delete_user_message(event.client, event.message.chat_id, event.message.id, 0)

    if (event.raw_text or '').strip() != CLEAR_ALL_CONFIRM_TEXT:
        logger.info('clear_all 已取消，确认文本不匹配')
        await reply_and_delete(event, '已取消 clear_all 操作')
        return True

    if not await is_admin(event):
        logger.warning('clear_all confirmation rejected for non-admin sender=%s chat=%s', sender_id, state_chat_id)
        await reply_and_delete(event, '只有管理员可以执行 clear_all')
        return True

    with get_db_session() as session:
        chat_count, rule_count, keyword_count, replace_count = await perform_clear_all(session)

    logger.warning(
        'clear_all executed by sender=%s chat=%s',
        sender_id,
        state_chat_id,
    )
    await reply_and_delete(
        event,
        '已清空所有数据:\n'
        f'- {chat_count} 个聊天\n'
        f'- {rule_count} 条转发规则\n'
        f'- {keyword_count} 个关键字\n'
        f'- {replace_count} 条替换规则'
    )
    return True


async def setup_listeners(user_client, bot_client):
    """
    设置消息监听器
    
    Args:
        user_client: 用户客户端（用于监听消息）
        bot_client: 机器人客户端（用于处理命令和转发）
    """
    global BOT_ID
    
    # 直接获取机器人ID
    try:
        me = await bot_client.get_me()
        BOT_ID = me.id
        logger.info(f"获取到机器人ID: {BOT_ID} (类型: {type(BOT_ID)})")
    except Exception as e:
        logger.error(f"获取机器人ID时出错: {str(e)}")
    
    # 过滤器，排除机器人自己的消息
    async def not_from_bot(event):
        if BOT_ID is None:
            return True  # 如果未获取到机器人ID，不进行过滤
        
        sender = event.sender_id
        try:
            sender_id = int(sender) if sender is not None else None
            is_not_bot = sender_id != BOT_ID
            if not is_not_bot:
                logger.info(f"过滤器识别到机器人消息，忽略处理: {sender_id}")
            return is_not_bot
        except (ValueError, TypeError):
            return True  # 转换失败时不过滤
    
    # 用户客户端监听器 - 使用过滤器，避免处理机器人消息
    @user_client.on(events.NewMessage(func=not_from_bot))
    async def user_message_handler(event):
        await handle_user_message(event, bot_client)
    
    # 机器人客户端监听器 - 使用过滤器
    @bot_client.on(events.NewMessage(func=not_from_bot))
    async def bot_message_handler(event):
        await handle_bot_message(event, bot_client)
        
    # 注册机器人回调处理器
    bot_client.add_event_handler(bot_handler.callback_handler)

async def handle_user_message(event, bot_client):
    """处理用户客户端收到的消息"""
    
    chat = await event.get_chat()
    chat_id = abs(chat.id)
    sender_id, state_chat_id = get_state_identity(event)

    # 检查用户状态
    current_state, message, _state_type = await state_manager.get_state(sender_id, state_chat_id)

    if current_state:
        # 处理提示词设置
        if await handle_prompt_setting(event, bot_client, sender_id, state_chat_id, current_state, message):
            return

        if current_state == 'clear_all_confirm':
            await handle_clear_all_confirmation(event, sender_id, state_chat_id)
            return

    # 检查是否是媒体组消息
    if event.message.grouped_id:
        group_key = f"{chat_id}:{event.message.grouped_id}"
        async with _PROCESSED_GROUPS_LOCK:
            now = asyncio.get_running_loop().time()
            expired_keys = [key for key, expires_at in PROCESSED_GROUPS.items() if expires_at <= now]
            for expired_key in expired_keys:
                PROCESSED_GROUPS.pop(expired_key, None)

            if PROCESSED_GROUPS.get(group_key, 0) > now:
                return
            PROCESSED_GROUPS[group_key] = now + _GROUP_CACHE_TTL
    
    # 首先检查数据库中是否有该聊天的转发规则
    with get_db_session() as session:
        # 查询源聊天
        source_chat = session.query(Chat).filter(
            Chat.telegram_chat_id == get_telegram_chat_db_id(chat)
        ).first()
        
        if not source_chat:
            return
            
        # 添加日志：查询转发规则
        logger.info(f'找到源聊天: {source_chat.name} (ID: {source_chat.id})')
        
        # 查找以当前聊天为源的规则
        rules = session.query(ForwardRule).filter(
            ForwardRule.source_chat_id == source_chat.id
        ).all()
        
        if not rules:
            logger.info(f'聊天 {source_chat.name} 没有转发规则')
            return
        
        # 有转发规则时，才记录消息信息
        if event.message.grouped_id:
            logger.info(f'收到媒体组消息 来自聊天: {source_chat.name} ({chat_id}) 组ID: {event.message.grouped_id}')
        else:
            content_length = len(event.message.text or '')
            logger.info(f'收到新消息 来自聊天: {source_chat.name} ({chat_id}) 文本长度: {content_length}')
            
        # 添加日志：处理规则
        logger.info(f'找到 {len(rules)} 条转发规则')
        
        # 处理每条转发规则
        for rule in rules:
            target_chat = rule.target_chat
            if not rule.enable_rule:
                logger.info(f'规则 {rule.id} 未启用')
                continue
            logger.info(f'处理转发规则 ID: {rule.id} (从 {source_chat.name} 转发到: {target_chat.name})')
            # 使用过滤器链处理并转发消息
            await process_forward_rule(bot_client, event, str(chat_id), rule)

async def handle_bot_message(event, bot_client):
    """处理机器人客户端收到的消息（命令）"""
    try:
        sender_id, state_chat_id = get_state_identity(event)

        # 检查用户状态
        current_state, message, _state_type = await state_manager.get_state(sender_id, state_chat_id)

        # 处理提示词设置
        if current_state:
            if await handle_prompt_setting(event, bot_client, sender_id, state_chat_id, current_state, message):
                return

            if current_state == 'clear_all_confirm':
                await handle_clear_all_confirmation(event, sender_id, state_chat_id)
                return

        # 如果没有特殊状态，则处理常规命令
        await bot_handler.handle_command(bot_client, event)
    except Exception as e:
        logger.error(f'处理机器人命令时发生错误: {str(e)}')
        logger.exception(e)

async def clear_group_cache(group_key, delay=300):
    await asyncio.sleep(delay)
    async with _PROCESSED_GROUPS_LOCK:
        PROCESSED_GROUPS.pop(group_key, None)
