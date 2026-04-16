import os

from dotenv import load_dotenv

load_dotenv()

######### Telegram 配置 #########
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
BOT_TOKEN = os.getenv('BOT_TOKEN')
USER_ID = int(os.getenv('USER_ID', 0))

######### AI 配置 #########
# 用户配置的模型列表 (逗号分隔，如: gpt-4o,claude-3-sonnet,gemini-2.0-flash)
AI_MODELS = [m.strip() for m in os.getenv('AI_MODELS', '').split(',') if m.strip()]

DEFAULT_AI_PROMPT = '请尊重原意，保持原有格式不变，用简体中文重写下面的内容：'
DEFAULT_SUMMARY_PROMPT = '请总结以下频道/群组24小时内的消息。'

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', '')

# Claude
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
CLAUDE_API_BASE = os.getenv('CLAUDE_API_BASE', '')

# Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_API_BASE = os.getenv('GEMINI_API_BASE', '')

# DeepSeek
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_BASE = os.getenv('DEEPSEEK_API_BASE', '')

# Qwen
QWEN_API_KEY = os.getenv('QWEN_API_KEY', '')
QWEN_API_BASE = os.getenv('QWEN_API_BASE', '')

# Grok
GROK_API_KEY = os.getenv('GROK_API_KEY', '')
GROK_API_BASE = os.getenv('GROK_API_BASE', '')

######### 可选配置 #########
ADMINS = os.getenv('ADMINS', '')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./db/forward.db')
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'Asia/Shanghai')

# UFB 联动
UFB_ENABLED = os.getenv('UFB_ENABLED', 'false').lower() == 'true'
UFB_SERVER_URL = os.getenv('UFB_SERVER_URL', '')
UFB_TOKEN = os.getenv('UFB_TOKEN', '')

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
CHAT_UPDATE_TIME = 3  # 聊天列表更新间隔 (小时)
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
