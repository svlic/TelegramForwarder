import asyncio
import logging
from telethon import TelegramClient
from models.models import get_db_session, Chat
import traceback
from utils.constants import CHAT_UPDATE_INTERVAL_SECONDS
logger = logging.getLogger(__name__)

class ChatUpdater:
    def __init__(self, user_client: TelegramClient):
        self.user_client = user_client
        self.task = None
        self.update_interval_seconds = CHAT_UPDATE_INTERVAL_SECONDS
    
    async def start(self):
        """启动定时更新任务"""
        logger.info("开始启动聊天信息更新器...")
        try:
            # 创建定时任务
            self.task = asyncio.create_task(self._run_update_task())
            logger.info("聊天信息更新器启动完成，每20分钟检查一次")
        except Exception as e:
            logger.error(f"启动聊天信息更新器时出错: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")

    async def _run_update_task(self):
        """运行更新任务"""
        while True:
            try:
                await asyncio.sleep(self.update_interval_seconds)

                # 执行更新任务
                await self._update_all_chats()

            except asyncio.CancelledError:
                logger.info("聊天信息更新任务已取消")
                break
            except Exception as e:
                logger.error(f"聊天信息更新任务出错: {str(e)}")
                logger.error(f"错误详情: {traceback.format_exc()}")
                await asyncio.sleep(60)  # 出错后等待一分钟再重试
    
    async def _update_all_chats(self):
        """更新所有聊天信息"""
        logger.info("开始更新所有聊天信息...")
        with get_db_session() as session:
            chats = [
                (chat.id, chat.telegram_chat_id, chat.name)
                for chat in session.query(Chat).all()
            ]
            total_chats = len(chats)
            logger.info(f"找到 {total_chats} 个聊天需要更新信息")

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for i, (chat_row_id, chat_id, old_chat_name) in enumerate(chats, 1):
            try:
                if i % 10 == 0 or i == total_chats:
                    logger.info(f"进度: {i}/{total_chats} ({i/total_chats*100:.1f}%)")

                try:
                    chat_id_int = int(chat_id)
                except ValueError:
                    logger.warning(f"聊天ID '{chat_id}' 不是有效的数字格式")
                    skipped_count += 1
                    continue

                entity = await self.user_client.get_entity(chat_id_int)
                new_name = entity.title if hasattr(entity, 'title') else (
                    f"{entity.first_name} {entity.last_name}" if hasattr(entity, 'last_name') and entity.last_name
                    else entity.first_name if hasattr(entity, 'first_name')
                    else "私聊"
                )

                if old_chat_name != new_name:
                    with get_db_session() as session:
                        chat = session.get(Chat, chat_row_id)
                        if chat is None:
                            skipped_count += 1
                            continue
                        chat.name = new_name
                        session.commit()
                    logger.info(f"已更新聊天 {chat_id}: {old_chat_name or '未命名'} -> {new_name}")
                    updated_count += 1
                else:
                    skipped_count += 1
            except ValueError as e:
                logger.warning(f"无法获取聊天 {chat_id} 的信息: 无效的ID格式 - {str(e)}")
                skipped_count += 1
            except Exception as e:
                logger.warning(f"无法获取聊天 {chat_id} 的信息: {str(e)}")
                error_count += 1

            await asyncio.sleep(1)

        logger.info(f"聊天信息更新完成。总计: {total_chats}, 更新: {updated_count}, 跳过: {skipped_count}, 错误: {error_count}")

    async def stop(self):
        """停止定时任务"""
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None
            logger.info("聊天信息更新任务已停止")
