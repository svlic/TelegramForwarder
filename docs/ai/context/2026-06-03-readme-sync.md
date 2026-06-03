# README 功能同步记录

日期：2026-06-03

## 背景

用户要求完整更新 README，使其与当前代码功能保持一致。更新前 README 对部分最新功能覆盖不足，且部分说明与代码中的实际过滤链、设置项、环境变量和命令列表不完全一致。

## 更新范围

更新 `/opt/ocode/tgf2604/TelegramForwarder/README.md`，以当前代码为准同步用户可见功能：

- 环境变量说明同步 `.env.example`：必填项、管理员、数据库、默认时区、AI 模型与 OpenAI 兼容接口、UFB 配置。
- 过滤流程同步 `filters/process.py` 的实际顺序：`init_filter` → `delay_filter` → `keyword_filter` → `replace_filter` → `media_filter` → `ai_filter` → `info_filter` → `comment_button_filter` → `edit_filter` → `sender_filter` → `reply_filter`。
- 设置说明同步 `handlers/button/settings_manager.py`：主设置、AI 设置、媒体设置、其他设置。
- AI 功能补充模型列表、图片上传、AI 后二次关键词过滤、上下文占位符、定时总结、总结置顶和立即总结。
- 媒体功能补充媒体类型、大小、扩展名黑白名单、caption 过滤、媒体被过滤时放行文本。
- 链接转发补充公开链接、私有 `t.me/c/...` 链接、媒体组、按钮和 caption。
- UFB 联动补充 `.env` 配置、绑定/解绑和同步类型切换。
- 命令列表同步当前命令实现，并修正重复 `/copy_rule` 说明。
- 配置文件自定义项补充 `config/summary_times.txt`、`config/delay_times.txt`、`config/max_media_size.txt`、`config/media_extensions.txt`。

## 同步的上下文记忆

`AGENTS.md` 中的 FILTER FLOW 曾保留旧顺序，本次同步为当前代码和 README 使用的真实过滤链，避免后续维护时继续引用过时流程。

## 验证

已检查 README 关键功能覆盖，包括 AI 后二次关键词过滤、UFB 同步、配置文件自定义项、链接转发、命令列表和 `/copy_rule` 唯一说明。

README 为 Markdown 文档，无需 Python 编译验证。后续如修改过滤链或设置菜单，应同时更新 README、`docs/ai/context/` 和 `AGENTS.md`。
