from telethon import TelegramClient, types
from telethon.tl.types import BotCommand
from telethon.tl.functions.bots import SetBotCommandsRequest
from dotenv import load_dotenv

# load_dotenv before utils.constants so env-backed values are populated at import
load_dotenv()

from models.models import dispose_db, init_db
from message_listener import setup_listeners
import os
import asyncio
import logging
import glob
import shutil
from models.db_operations import DBOperations
from scheduler.summary_scheduler import SummaryScheduler
from scheduler.chat_updater import ChatUpdater
from handlers.bot_handler import send_welcome_message
from ai import get_ai_provider
from utils.log_config import setup_logging
from utils.constants import TEMP_DIR, API_HASH, BOT_TOKEN, PHONE_NUMBER, validate_config

# 设置日志配置
setup_logging()

logger = logging.getLogger(__name__)

api_hash = API_HASH
bot_token = BOT_TOKEN
phone_number = PHONE_NUMBER

# 创建 DBOperations 实例
db_ops = None

scheduler = None
chat_updater = None
user_client = None
bot_client = None


async def init_db_ops():
    """初始化 DBOperations 实例"""
    global db_ops
    if db_ops is None:
        db_ops = DBOperations()
    return db_ops


# 创建文件夹
os.makedirs('./sessions', exist_ok=True)
os.makedirs('./temp', exist_ok=True)

# Clean up residual temp files from previous runs
for f in glob.glob(os.path.join(TEMP_DIR, '*')):
    try:
        if os.path.isfile(f):
            os.remove(f)
        elif os.path.isdir(f):
            shutil.rmtree(f)
    except Exception as e:
        logger.warning(f'清理临时文件失败: {f}, 错误: {e}')


async def start_clients():
    # 初始化 DBOperations
    global db_ops, scheduler, chat_updater, user_client, bot_client
    api_id = validate_config()
    user_client = TelegramClient('./sessions/user', api_id, api_hash)
    bot_client = TelegramClient('./sessions/bot', api_id, api_hash)

    try:
        init_db()
        db_ops = DBOperations()
        # 启动用户客户端
        await user_client.start(phone=phone_number)
        me_user = await user_client.get_me()
        logger.info(f'用户客户端已启动: {me_user.first_name} (@{me_user.username})')

        # 启动机器人客户端
        await bot_client.start(bot_token=bot_token)
        me_bot = await bot_client.get_me()
        logger.info(f'机器人客户端已启动: {me_bot.first_name} (@{me_bot.username})')

        # 设置消息监听器
        await setup_listeners(user_client, bot_client)

        # 注册命令
        await register_bot_commands(bot_client)

        # 创建并启动调度器
        scheduler = SummaryScheduler(user_client, bot_client)
        await scheduler.start()
        
        # 创建并启动聊天信息更新器
        chat_updater = ChatUpdater(user_client)
        await chat_updater.start()

        # 发送欢迎消息
        await send_welcome_message(bot_client)

        # 等待两个客户端都断开连接
        await asyncio.gather(
            user_client.run_until_disconnected(),
            bot_client.run_until_disconnected()
        )
    finally:
        # 停止调度器
        if scheduler:
            await scheduler.stop()
        # 停止聊天信息更新器
        if chat_updater:
            await chat_updater.stop()
        # 先停止新事件进入，再释放事件处理器共享的资源
        for client in (bot_client, user_client):
            if client and client.is_connected():
                await client.disconnect()
        # 关闭 AI HTTP 客户端
        provider = await get_ai_provider()
        await provider.close()
        # 关闭 DBOperations
        if db_ops and hasattr(db_ops, 'close'):
            await db_ops.close()
        dispose_db()


async def register_bot_commands(bot):
    """注册机器人命令"""
    commands = [
        # 基础命令
        BotCommand(
            command='start',
            description='开始使用'
        ),
        BotCommand(
            command='help',
            description='查看帮助'
        ),
        # 绑定和设置
        BotCommand(
            command='bind',
            description='绑定源聊天'
        ),
        BotCommand(
            command='settings',
            description='管理转发规则'
        ),
        BotCommand(
            command='switch',
            description='切换当前需要设置的聊天规则'
        ),
        # 关键字管理
        BotCommand(
            command='add',
            description='添加关键字'
        ),
        BotCommand(
            command='add_regex',
            description='添加正则关键字'
        ),
        BotCommand(
            command='add_all',
            description='添加普通关键字到所有规则'
        ),
        BotCommand(
            command='add_regex_all',
            description='添加正则表达式到所有规则'
        ),
        BotCommand(
            command='list_keyword',
            description='列出所有关键字'
        ),
        BotCommand(
            command='remove_keyword',
            description='删除关键字'
        ),
        BotCommand(
            command='remove_keyword_by_id',
            description='按ID删除关键字'
        ),
        BotCommand(
            command='remove_all_keyword',
            description='删除当前频道绑定的所有规则的指定关键字'
        ),
        # 替换规则管理
        BotCommand(
            command='replace',
            description='添加替换规则'
        ),
        BotCommand(
            command='replace_all',
            description='添加替换规则到所有规则'
        ),
        BotCommand(
            command='list_replace',
            description='列出所有替换规则'
        ),
        BotCommand(
            command='remove_replace',
            description='删除替换规则'
        ),
        # 导入导出功能
        BotCommand(
            command='export_keyword',
            description='导出当前规则的关键字'
        ),
        BotCommand(
            command='export_replace',
            description='导出当前规则的替换规则'
        ),
        BotCommand(
            command='import_keyword',
            description='导入普通关键字'
        ),
        BotCommand(
            command='import_regex_keyword',
            description='导入正则表达式关键字'
        ),
        BotCommand(
            command='import_replace',
            description='导入替换规则'
        ),
        BotCommand(
            command='clear_all_keywords',
            description='清除当前规则的所有关键字'
        ),
        BotCommand(
            command='clear_all_keywords_regex',
            description='清除当前规则的所有正则关键字'
        ),
        BotCommand(
            command='clear_all_replace',
            description='清除当前规则的所有替换规则'
        ),
        BotCommand(
            command='copy_keywords',
            description='复制参数规则的关键字到当前规则'
        ),
        BotCommand(
            command='copy_keywords_regex',
            description='复制参数规则的正则关键字到当前规则'
        ),
        BotCommand(
            command='copy_replace',
            description='复制参数规则的替换规则到当前规则'
        ),
        BotCommand(
            command='copy_rule',
            description='复制参数规则到当前规则'
        ),
        BotCommand(
            command='changelog',
            description='查看更新日志'
        ),
        BotCommand(
            command='list_rule',
            description='列出所有转发规则'
        ),
        BotCommand(
            command='delete_rule',
            description='删除转发规则'
        ),
    ]

    try:
        result = await bot(SetBotCommandsRequest(
            scope=types.BotCommandScopeDefault(),
            lang_code='',  # 空字符串表示默认语言
            commands=commands
        ))
        if result:
            logger.info('已成功注册机器人命令')
        else:
            logger.error('注册机器人命令失败')
    except Exception as e:
        logger.error(f'注册机器人命令时出错: {str(e)}')


if __name__ == '__main__':
    try:
        asyncio.run(start_clients())
    except KeyboardInterrupt:
        logger.info("正在关闭客户端...")
