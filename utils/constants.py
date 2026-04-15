import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 目录配置
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

RULES_PER_PAGE = int(os.getenv('RULES_PER_PAGE', 20))

DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'Asia/Shanghai')
PROJECT_NAME = os.getenv('PROJECT_NAME', 'TG Forwarder')

# 默认AI模型
DEFAULT_AI_MODEL = os.getenv('DEFAULT_AI_MODEL', 'gpt-4o')
# 默认AI总结提示词
DEFAULT_SUMMARY_PROMPT = os.getenv('DEFAULT_SUMMARY_PROMPT', '请总结以下频道/群组24小时内的消息。')
# 默认AI提示词
DEFAULT_AI_PROMPT = os.getenv('DEFAULT_AI_PROMPT', '请尊重原意，保持原有格式不变，用简体中文重写下面的内容：')

# 分页配置
MODELS_PER_PAGE = int(os.getenv('AI_MODELS_PER_PAGE', 10))
KEYWORDS_PER_PAGE = int(os.getenv('KEYWORDS_PER_PAGE', 50))

# 按钮布局配置
SUMMARY_TIME_ROWS = int(os.getenv('SUMMARY_TIME_ROWS', 10))
SUMMARY_TIME_COLS = int(os.getenv('SUMMARY_TIME_COLS', 6))

DELAY_TIME_ROWS = int(os.getenv('DELAY_TIME_ROWS', 10))
DELAY_TIME_COLS = int(os.getenv('DELAY_TIME_COLS', 6))

MEDIA_SIZE_ROWS = int(os.getenv('MEDIA_SIZE_ROWS', 10))
MEDIA_SIZE_COLS = int(os.getenv('MEDIA_SIZE_COLS', 6))

MEDIA_EXTENSIONS_ROWS = int(os.getenv('MEDIA_EXTENSIONS_ROWS', 6))
MEDIA_EXTENSIONS_COLS = int(os.getenv('MEDIA_EXTENSIONS_COLS', 6))

LOG_MAX_SIZE_MB = 10
LOG_BACKUP_COUNT = 3

# 默认消息删除时间 (秒)
BOT_MESSAGE_DELETE_TIMEOUT = int(os.getenv("BOT_MESSAGE_DELETE_TIMEOUT", 300))

# 自动删除用户发送的指令消息
USER_MESSAGE_DELETE_ENABLE = os.getenv("USER_MESSAGE_DELETE_ENABLE", "false")

# 是否启用UFB
UFB_ENABLED = os.getenv("UFB_ENABLED", "false")

# 菜单标题
AI_SETTINGS_TEXT = """
当前AI提示词：

`{ai_prompt}`

当前总结提示词：

`{summary_prompt}`
"""

# 媒体设置文本
MEDIA_SETTINGS_TEXT = """
媒体设置：
"""
