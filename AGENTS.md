# TelegramForwarder Agent Guide

## 项目

Python 3.11 的异步 Telegram 消息转发器。`user_client` 监听源聊天，`bot_client` 处理命令并向目标聊天发送消息；规则和状态分别存于 SQLAlchemy 与内存状态管理器。

## 先看这里

| 任务 | 入口 |
| --- | --- |
| 启动与客户端生命周期 | `main.py` |
| 消息监听、规则查询、媒体组去重 | `message_listener.py` |
| 转发过滤链 | `filters/process.py`、`filters/context.py` |
| Bot 命令与按钮 | `handlers/bot_handler.py`、`handlers/command_handlers.py`、`handlers/button/` |
| 数据模型与会话 | `models/models.py`、`models/db_operations.py` |
| AI 处理与定时总结 | `ai/`、`scheduler/summary_scheduler.py` |
| 状态与聊天 ID 工具 | `managers/state_manager.py`、`utils/common.py` |

消息处理顺序和领域约束见 [`kb/docs/message-processing.md`](kb/docs/message-processing.md)。面向用户的功能和配置以 [`README.md`](README.md) 为准。

## 必须遵守

- Telethon 调用必须 `await`；不要在事件循环中加入阻塞 I/O。
- 数据库会话统一使用 `get_db_session()`；不要让会话跨越 Telethon 或 AI 网络调用。
- 状态键统一由 `get_state_identity(event)` 生成。
- 持久化聊天 ID 使用 `get_telegram_chat_db_id()`；只对频道或超级群组使用 `normalize_channel_id()`，不要给私聊 ID 添加 `-100` 前缀。
- 过滤器通过 `MessageContext` 传递状态。新增或调整步骤时在 `filters/process.py` 注册，并同步更新领域文档。
- EDIT 模式必须保留前置过滤结果，尤其是 `should_forward`、`media_blocked` 和 `skipped_media`。
- 媒体组去重由 `message_listener.py` 管理；临时媒体由过滤链上下文清理，不要另建平行缓存或清理路径。
- `ai` 包根只导出 `get_ai_provider`；具体 provider 从其定义模块导入。
- `pyaes` 是 Telethon 的必需依赖，`cryptg` 是加密加速依赖；不要按“未直接导入”删除。

## 代码约定

- 日志使用 `logging.getLogger(__name__)`。
- 优先小而直接的改动，复用现有函数和过滤器；不要为单次需求新增抽象层。
- 用户交流使用中文；代码注释使用英文，仅解释原因或约束。
- 不提交 `.env`、session、数据库、日志、下载文件等运行时数据。

## 验证

```bash
python -m pytest -q
python main.py

docker compose run --rm telegram-forwarder  # 首次登录
docker compose up -d
```

运行 `main.py` 需要完整 `.env` 和 Telegram 凭据。无法做真实 Telegram 验证时，至少运行相关测试并说明未验证项。

## 文档维护

- 用户可见行为或配置变化：更新 `README.md`。
- 稳定的业务流程或跨模块约束：更新 `kb/docs/`。
- 架构决策或非显然 trade-off：在 `docs/ai/context/` 留记录；普通小改动无需建文档。
- 不在本文件记录版本号、提交号、固定文件数量等易漂移信息。
