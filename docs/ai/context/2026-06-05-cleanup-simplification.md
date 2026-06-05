# 2026-06-05 代码清理与简化记录

## 背景

本次修复来自代码清理与简化审查。目标是在不改变业务行为的前提下，删除可证明未使用或无效的代码，优先低风险、最小改动。

## 修复内容

1. 删除未使用导入：
   - `handlers/command_handlers.py`：删除未引用的 `IntegrityError`、`ForwardMode`、`get_main_module`、`normalize_channel_id`、`create_settings_text`、`create_buttons`。
   - `handlers/button/callback/other_callback.py`：删除未引用的 `os`。
   - `managers/state_manager.py`：删除未引用的 `Union`。
2. 删除无效 Docker 日志环境变量：
   - `main.py` 删除 `DOCKER_LOG_MAX_SIZE` / `DOCKER_LOG_MAX_FILE` 默认值设置。
   - `Dockerfile` 删除同名 `ENV`。
   这些变量只进入容器环境，不会配置 Docker logging driver；保留会造成“已配置日志轮转”的误导。
3. 删除未使用的定时总结批量执行入口：
   - `scheduler/summary_scheduler.py` 删除 `SummaryScheduler.execute_all_summaries()`。
   - 当前仓库内只存在定义，无调用点；立即总结仍通过现有规则级 `_execute_summary(..., is_now=True)` 流程处理。
4. 删除未使用的 UFB 配置更新回调扩展点：
   - `ufb/ufb_client.py` 删除 `on_config_update_callbacks`、`on_config_update()`、`notify_config_update()` 以及内部通知调用。
   - 当前仓库内没有注册者；删除后仍保留收到服务器消息后的 `save_config()` / `sync_from_json()` 主流程。

## 验证

已运行：

```bash
python -m py_compile $(git ls-files '*.py')
```

结果：通过，无输出。

LSP 诊断不可用，原因是当前环境缺少 `basedpyright-langserver`。

模块导入 smoke test 因宿主环境未安装项目依赖 `sqlalchemy` 失败；`requirements.txt` 已声明 `SQLAlchemy==2.0.37`，失败点是环境依赖缺失，不是本次语法或引用改动。

Oracle 已做只读风险复核，结论：PASS。

## 后续注意

如后续需要 Docker 日志轮转，应在 `docker-compose.yml` 或运行时 Docker logging options 中配置，而不是在应用进程或 Dockerfile 内设置普通环境变量。

如后续需要 UFB 配置变更通知，重新引入时应同时提交实际注册者和测试，避免保留无调用扩展点。
