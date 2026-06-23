import asyncio
import logging
from utils.constants import BOT_MESSAGE_DELETE_TIMEOUT, USER_MESSAGE_DELETE_ENABLE
logger = logging.getLogger(__name__)

# 从环境变量获取默认超时时间

async def delete_after(message, seconds):
    """等待指定秒数后删除消息
    
    参数:
        message: 要删除的消息
        seconds: 等待多少秒后删除, 0表示立即删除, -1表示不删除
    """
    if seconds == -1:  # -1 表示不删除
        return
    
    if seconds > 0:  # 正数表示等待指定秒数再删除
        await asyncio.sleep(seconds)
        
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"删除消息失败: {e}")

async def _send_and_delete(send_coro, delete_after_seconds):
    deletion_timeout = delete_after_seconds if delete_after_seconds is not None else BOT_MESSAGE_DELETE_TIMEOUT
    message = await send_coro()
    if deletion_timeout != -1:
        asyncio.create_task(delete_after(message, deletion_timeout))
    return message

async def reply_and_delete(event, text, delete_after_seconds=None, **kwargs):
    return await _send_and_delete(lambda: event.reply(text, **kwargs), delete_after_seconds)

async def respond_and_delete(event, text, delete_after_seconds=None, **kwargs):
    return await _send_and_delete(lambda: event.respond(text, **kwargs), delete_after_seconds)

async def send_message_and_delete(client, entity, text, delete_after_seconds=None, **kwargs):
    return await _send_and_delete(lambda: client.send_message(entity, text, **kwargs), delete_after_seconds)

# 删除用户消息
async def async_delete_user_message(client, chat_id, message_id, seconds):
    """删除用户消息
    
    参数:
        client: bot客户端
        chat_id: 聊天ID
        message_id: 消息ID
        seconds: 等待多少秒后删除, 0表示立即删除, -1表示不删除
    """
    if not USER_MESSAGE_DELETE_ENABLE:
        return
    
    if seconds == -1:  # -1 表示不删除
        return
        
    if seconds > 0:  # 正数表示等待指定秒数再删除
        await asyncio.sleep(seconds)
        
    try:
        await client.delete_messages(chat_id, message_id)
    except Exception as e:
        logger.error(f"删除用户消息失败: {e}")

