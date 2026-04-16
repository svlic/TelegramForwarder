import logging
import asyncio
from typing import Dict, Tuple, Optional, Union
from telethon.tl.custom import Message

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self):
        self._states: Dict[Tuple[int, int], Tuple[str, Optional[Message], Optional[str]]] = {}
        self._timeout_tasks: Dict[Tuple[int, int], asyncio.Task] = {}
        self._lock = asyncio.Lock()
        logger.info("StateManager 初始化")
    
    async def set_state(self, user_id: int, chat_id: int, state: str, message: Optional[Message] = None, state_type: Optional[str] = None, timeout_minutes: int = 5) -> None:
        key = (user_id, chat_id)
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
                if key in self._states:
                    del self._states[key]
                    logger.info(f"状态超时自动清除 - key: {key}")
                if key in self._timeout_tasks:
                    del self._timeout_tasks[key]
        except asyncio.CancelledError:
            pass
    
    async def get_state(self, user_id: int, chat_id: int) -> Union[Tuple[str, Optional[Message], Optional[str]], Tuple[None, None, None]]:
        key = (user_id, chat_id)
        async with self._lock:
            state_data = self._states.get(key)
        if state_data:
            if len(state_data) == 3:
                state, message, state_type = state_data
                logger.info(f"获取状态 - key: {key}, state: {state}, type: {state_type}")
            else:
                state, message = state_data
                state_type = None
                logger.info(f"获取状态 - key: {key}, state: {state}, type: None (旧格式)")
            return state, message, state_type
        return None, None, None
    
    async def clear_state(self, user_id: int, chat_id: int) -> None:
        key = (user_id, chat_id)
        async with self._lock:
            if key in self._states:
                del self._states[key]
                logger.info(f"清除状态 - key: {key}")
            if key in self._timeout_tasks:
                self._timeout_tasks[key].cancel()
                del self._timeout_tasks[key]
        logger.debug(f"当前所有状态: {self._states}")
    
    def check_state(self) -> bool:
        """检查是否存在状态"""
        return bool(self._states)

# 创建全局实例
state_manager = StateManager()
logger.info("StateManager 全局实例已创建")