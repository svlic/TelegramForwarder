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
edit_filter
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

## 通用偏好

- 用中文回复，代码注释用英文，注释写 why 不写 how
- 简洁直接，不要多余总结和解释
- 直接写代码，不需要每次确认后再生成

## 代码风格

- 函数式优先，组合优于继承，TS/JS 中避免 OOP
- 新功能优先复用/重构现有代码，不堆砌
- KISS, DRY — 最简可行方案
- 写代码时遵循 ai-coding-discipline 规则
- 发现设计不合理：小问题直接重构，大问题原地加 TODO 并说明原因

## 架构与设计

- 从第一性原理解构问题 — 先明确什么是必须的，再决定怎么做
- 警惕 XY 问题 — 多角度审视方案，先确认真正要解决的是什么，主动提出替代方案
- 解决根本问题，不要 workaround — 如果现有架构不支持，重构它
- 质疑不合理的需求和方向 — 发现问题立刻指出，不要等我问才说，不要奉承或无脑赞同
- 架构设计时参考 ddia-principles 和 software-design-philosophy 规则
- 技术选型推荐业内最佳实践 — 不确定时先 research，不要给过时的信息

## 文档与上下文

- 所有改动、上下文、tradeoff、背景信息都保存到项目的 `docs/ai/context/` 目录
- 进行修改、架构设计、技术选型时同步更新或新建文档
- 思考和决策也要落实到项目的 AGENTS.md，保留上下文记忆
- 如果项目没有 `docs/ai/context/` 目录，先询问是否创建

## NOTES
- Bot模式下编辑消息需是管理员
- 媒体组处理需防重 (5分钟缓存)
- AI Provider使用统一`BaseProvider`接口
