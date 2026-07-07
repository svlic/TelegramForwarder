# 代码清理落地记录

**日期**: 2026-07-06  
**范围**: `/code-cleaner` 后续确认项  
**原则**: 功能等价、只处理已确认清理项和静态检查暴露的真实运行时缺陷。

## 已落地

- `.dockerignore`: `**/test/` 改为 `**/tests/`，匹配仓库实际测试目录命名。
- `Dockerfile`: 删除 `/app/temp` 预创建层。运行时 `main.py` 和 `filters/media_filter.py` 已负责创建 `temp`，compose 挂载也会覆盖镜像内目录。
- `ai/__init__.py`: 移除包根 `BaseAIProvider` 导入；包根 API 继续只承诺 `get_ai_provider`。
- `ufb/requirements.txt`: 删除重复 manifest。UFB 当前作为主项目集成功能存在，根 `requirements.txt` 已包含 `websockets` 和 `python-dotenv`。
- 多处未使用 import/变量、无占位符 f-string 改为普通字符串。
- `handlers/button/settings_manager.py:create_buttons`: 删除未使用的 `get_db_session()` 包裹，仅保留按钮构造逻辑。
- `handlers/button/button_helpers.py:create_page_buttons`: 集中复制规则、规则选择、媒体扩展名、同步规则的上一页/页码/下一页按钮生成；callback payload 保持原格式。

## 静态检查确认并修复的缺陷

`pyflakes` 报告的 undefined-name 不是清理项，而是潜在运行时错误，已按现有来源补齐：

- `models/models.py`: 导入 `DATABASE_URL`。
- `utils/common.py`: 导入 `ChannelParticipantsAdmins` 和 `ForwardMode`。
- `handlers/button/callback/callback_handlers.py`: 导入 `get_db_ops`。
- `handlers/command_handlers.py`: 导入 `get_all_rules`、`check_and_clean_chats`，移除未使用 `get_bot_client`。
- `handlers/button/callback/other_callback.py`: 在复制规则覆盖字段前保存 `had_existing_sync = target_rule.enable_sync`，用于恢复/合并同步开关。

## requirements.txt 决策

保留根 `requirements.txt` 中的：

- `pyaes==1.6.1`: Telethon 1.38.1 的必需依赖。删除显式 pin 不会删除依赖，但会把版本控制交给 resolver，非纯清理。
- `cryptg==0.5.0.post0`: Telethon 的可选加密加速依赖。删除通常不破功能，但会改变性能特征，非行为等价清理。

若以后要简化依赖声明，可单独评估改成 `Telethon[cryptg]==1.38.1` 并接受 resolver 重新选择传递依赖版本。

## 验证

- `python -m compileall -q .`
- `python -m pyflakes $(git ls-files '*.py')`
- `git diff --check`

三项均通过。
