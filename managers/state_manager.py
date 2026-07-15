import logging
import asyncio
from typing import Dict, Tuple, Optional
from telethon.tl.custom import Message
from utils.common import normalize_state_chat_id

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self):
        self._states: Dict[Tuple[int, int], Tuple[str, Optional[Message], Optional[str]]] = {}
        self._timeout_tasks: Dict[Tuple[int, int], asyncio.Task] = {}
        self._lock = asyncio.Lock()
        logger.info("StateManager 初始化")
    
    async def set_state(self, user_id: int, chat_id: int, state: str, message: Optional[Message] = None, state_type: Optional[str] = None, timeout_minutes: int = 5) -> None:
        key = (int(user_id), normalize_state_chat_id(chat_id))
        async with self._lock:
            self._states[key] = (state, message, state_type)
            if key in self._timeout_tasks:
                self._timeout_tasks[key].cancel()
            self._timeout_tasks[key] = asyncio.create_task(self._timeout_clear(key, timeout_minutes))
        logger.info(f"设置状态 - key: {key}, state: {state}, type: {state_type}")
        logger.debug(f"当前所有状态: {self._states}")
    
    async def _timeout_clear(self, key: Tuple[int, int], timeout_minutes: int) -> None:
        try:
            await asyncio.sleep(timeout_minutes * 60)
            async with self._lock:
                if self._states.pop(key, None) is not None:
                    logger.info(f"状态超时自动清除 - key: {key}")
                self._timeout_tasks.pop(key, None)
        except asyncio.CancelledError:
            pass
    
    async def get_state(self, user_id: int, chat_id: int) -> Optional[Tuple[str, Optional[Message], Optional[str]]]:
        key = (int(user_id), normalize_state_chat_id(chat_id))
        async with self._lock:
            state_data = self._states.get(key)
        if state_data:
            state, message, state_type = state_data
            logger.info(f"获取状态 - key: {key}, state: {state}, type: {state_type}")
            return state, message, state_type
        return None, None, None
    
    async def clear_state(self, user_id: int, chat_id: int) -> None:
        key = (int(user_id), normalize_state_chat_id(chat_id))
        async with self._lock:
            if self._states.pop(key, None) is not None:
                logger.info(f"清除状态 - key: {key}")
            task = self._timeout_tasks.pop(key, None)
            if task is not None:
                task.cancel()
        logger.debug(f"当前所有状态: {self._states}")

# 创建全局实例
state_manager = StateManager()
logger.info("StateManager 全局实例已创建")