# PROJECT KNOWLEDGE BASE

**Generated:** 2026-04-15
**Commit:** 96093f9
**Branch:** main

## OVERVIEW
TelegramForwarder v1.7.2 - Telegram消息转发机器人，支持关键词过滤、正则替换、AI处理。

## STRUCTURE
```
./
├── main.py              # 入口 - 双客户端启动 (user + bot)
├── message_listener.py  # 消息监听器
├── models/              # SQLAlchemy ORM
├── handlers/            # 命令/按钮处理
├── filters/             # 过滤器链 (16个过滤器)
├── ai/                  # AI提供商 (OpenAI/Claude/Gemini等)
├── utils/               # 工具函数
├── scheduler/           # 定时任务
├── managers/            # 状态管理
├── enums/               # 枚举定义
└── ufb/                 # UniversalForumBlock联动
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| 消息过滤逻辑 | `filters/process.py` | 过滤器入口 |
| 命令处理 | `handlers/command_handlers.py` | 所有/command |
| 按钮回调 | `handlers/button/` | 菜单交互 |
| AI调用 | `ai/` | Provider模式 |
| 转发处理 | `handlers/user_handler.py` | 用户模式转发 |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `process_forward_rule` | function | `filters/process.py` | 过滤器链主入口 |
| `handle_command` | function | `handlers/bot_handler.py` | 命令分发 |
| `DBOperations` | class | `models/db_operations.py` | 数据库操作 |
| `FilterChain` | class | `filters/filter_chain.py` | 过滤器编排 |
| `SummaryScheduler` | class | `scheduler/summary_scheduler.py` | AI定时总结 |

## FILTER FLOW (执行顺序)
```
消息 → init_filter → keyword_filter → replace_filter → 
ai_filter → media_filter → reply_filter → sender_filter → 
comment_button_filter → info_filter → delay_filter → 
edit_filter → delete_original_filter
```

## CONVENTIONS
- **日志**: 使用`logging.getLogger(__name__)`
- **异步**: `async/await` + `asyncio`; 同步调用用`loop.run_until_complete()`
- **状态管理**: `managers/state_manager.py` 单例模式
- **DB会话**: `models/models.py` 的 `get_session()` 获取会话
- **媒体组**: 用 `grouped_id` 检测，`PROCESSED_GROUPS` 缓存防重
- **频道ID**: Telegram频道ID需加`100`前缀
- **双客户端**: `user_client` 转发 + `bot_client` 处理命令

## ANTI-PATTERNS (THIS PROJECT)
- **禁止**: 在过滤器外直接操作数据库会话 - 用过滤器方法
- **禁止**: 修改`PROCESSED_GROUPS`外部清除 - 用`clear_group_cache()`
- **禁止**: 同步调用Telethon方法 - 必须`await`

## COMMANDS
```bash
# 开发运行
python main.py

# Docker运行
docker-compose up -d

# 首次验证
docker-compose run -it telegram-forwarder
```

## NOTES
- Bot模式下编辑消息需是管理员
- 媒体组处理需防重 (5分钟缓存)
- AI Provider使用统一`BaseProvider`接口
