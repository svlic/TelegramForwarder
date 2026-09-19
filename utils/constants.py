import os
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.engine import make_url

######### Telegram 配置 #########
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
BOT_TOKEN = os.getenv('BOT_TOKEN')

######### AI 配置 #########
# 用户配置的模型列表 (逗号分隔，如: gpt-4o,claude-3-sonnet,gemini-2.0-flash)
AI_MODELS = [m.strip() for m in os.getenv('AI_MODELS', '').split(',') if m.strip()]

DEFAULT_AI_PROMPT = '请尊重原意，保持原有格式不变，用简体中文重写下面的内容：'
DEFAULT_SUMMARY_PROMPT = '请总结以下频道/群组24小时内的消息。'

AI_SETTINGS_TEXT = """当前 AI 提示词：

`{ai_prompt}`

当前总结提示词：

`{summary_prompt}`
"""

MEDIA_SETTINGS_TEXT = """媒体设置见下方按钮。"""

# 自定义 OpenAI 兼容接口
CUSTOM_AI_API_KEY = os.getenv('CUSTOM_AI_API_KEY', '')
CUSTOM_AI_API_BASE = os.getenv('CUSTOM_AI_API_BASE', '')

######### 可选配置 #########
DATABASE_URL = os.getenv('DATABASE_URL') or 'sqlite:///./db/forward.db'
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE') or 'Asia/Shanghai'

######### 运行时默认值 (无需在 .env 中配置) #########

# -- 消息设置 --
BOT_MESSAGE_DELETE_TIMEOUT = 30
USER_MESSAGE_DELETE_ENABLE = True

# -- 媒体设置 --
DEFAULT_MAX_MEDIA_SIZE = 10
TEMP_DIR = os.path.join(os.getcwd(), 'temp')

# -- 分页设置 --
RULES_PER_PAGE = 5
KEYWORDS_PER_PAGE = 6
MODELS_PER_PAGE = 6

# -- 定时任务 --
CHAT_UPDATE_INTERVAL_SECONDS = 20 * 60
DEFAULT_SUMMARY_TIME = '07:00'  # 默认总结时间

# -- AI 总结批次 --
SUMMARY_BATCH_SIZE = 5
SUMMARY_BATCH_DELAY = 2  # 秒

# -- AI 超时 --
AI_PROCESS_TIMEOUT = 60  # 秒

# -- 内联键盘布局 --
SUMMARY_TIME_ROWS = 3
SUMMARY_TIME_COLS = 4
DELAY_TIME_ROWS = 3
DELAY_TIME_COLS = 4
MEDIA_SIZE_ROWS = 3
MEDIA_SIZE_COLS = 4
MEDIA_EXTENSIONS_ROWS = 3
MEDIA_EXTENSIONS_COLS = 4


def validate_config():
    """Validate environment-backed settings before creating external clients."""
    missing = [
        name
        for name, value in {
            'API_ID': API_ID,
            'API_HASH': API_HASH,
            'PHONE_NUMBER': PHONE_NUMBER,
            'BOT_TOKEN': BOT_TOKEN,
            'USER_ID': os.getenv('USER_ID'),
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"缺少必填环境变量: {', '.join(missing)}")

    try:
        api_id = int(API_ID)
    except (TypeError, ValueError) as exc:
        raise ValueError('API_ID 必须是整数') from exc

    try:
        ZoneInfo(DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f'DEFAULT_TIMEZONE 不是有效的 IANA 时区: {DEFAULT_TIMEZONE}') from exc

    try:
        int(os.environ['USER_ID'])
        for admin in os.getenv('ADMINS', '').split(','):
            if admin.strip():
                int(admin.strip())
    except ValueError as exc:
        raise ValueError('USER_ID 和 ADMINS 必须是整数 ID') from exc

    try:
        make_url(DATABASE_URL)
    except Exception as exc:
        raise ValueError('DATABASE_URL 格式无效') from exc

    ai_key = os.getenv('CUSTOM_AI_API_KEY', '').strip()
    ai_base = os.getenv('CUSTOM_AI_API_BASE', '').strip()
    if ai_key or ai_base or AI_MODELS:
        if not ai_key or not ai_base:
            raise ValueError('启用 AI 时必须同时设置 CUSTOM_AI_API_KEY 和 CUSTOM_AI_API_BASE')
        parsed_base = urlparse(ai_base)
        if parsed_base.scheme not in {'http', 'https'} or not parsed_base.netloc:
            raise ValueError('CUSTOM_AI_API_BASE 必须是有效的 HTTP(S) URL')

    return api_id
