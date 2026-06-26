# 2026-06-27 Bug-finder 修复记录

## 范围
用户要求修复审查项：1, 2, 6, 8, 9, 14, 15, 21, 22（未改代码的审查报告对应编号）。

## 已实施

| # | 项 | 改动 |
|---|-----|------|
| 1 | `handle_settings_command` 缺失 | `handlers/command_handlers.py` 新增：无参列规则按钮；`/settings <id>` 经 `rule_belongs_to_current_chat` 后展示 `create_settings_text` + `create_buttons` |
| 2 | `/bind` 不创建规则 | 重写 `handle_bind_command`：`resolve_bind_chat_ref` + `get_or_create_chat_row` 创建 `ForwardRule`；已存在则提示并设 `current_add_id` |
| 6 | 迁移缺 UFB 列 | `models/models.py` `forward_rules_new_columns` 增加 `is_ufb`, `ufb_domain`, `ufb_item` |
| 8 | KeywordFilter 不写 `should_forward` | `filters/keyword_filter.py` 同步 `context.should_forward` |
| 9 | 坏正则静默 | `utils/common.py` `check_keyword_match`：`re.error` 时黑名单视为匹配（不转发），白名单视为不匹配 |
| 14 | 链完成≠转发 | `filters/filter_chain.py` 结束时返回 `context.should_forward` 并区分日志 |
| 15 | AI 失败仍转发 | `filters/ai_filter.py` 超时与异常时 `should_forward=False` 并中断链 |
| 21 | EditFilter | 已为预期行为（尊重 `should_forward`/`media_blocked`），无代码变更 |
| 22 | 命令权限 | `/settings [id]` 已加 `rule_belongs_to_current_chat`；`delete_rule`/`copy_*` 原有校验保持 |

## 新增工具
- `utils/common.py`: `resolve_bind_chat_ref`, `get_or_create_chat_row`, `_chat_display_name`

## 验证
`python -m py_compile` 对上述改动文件通过（环境可无 telethon，仅语法检查）。