# 代码清理与简化审查报告

**日期**: 2026-06-28  
**范围**: TelegramForwarder 全仓  
**原则**: 功能等价、最小改动。

**落地状态 (2026-06-28)**: 用户确认 D（全部 + 文档）+ 媒体短文案；已应用常量修复、media_filter import、`common` 无用 import 删除、建议简化 #1/#2/#4、AGENTS 修正。**未删除** `get_sender_info` / `process_user_info`：`check_keywords()` 在 `rule.is_filter_user_info` 时仍调用 `process_user_info`（审查 grep 漏检）。`python3 -m compileall` 通过。

---

## 一、可直接清理

| # | 类型 | 位置 | 原因 | 风险 | 建议 |
|---|------|------|------|------|------|
| 1 | 重复 import | `filters/media_filter.py` L7-8 | 两行 `models.models` 可合并 | 无 | 合并为一行 |
| 2 | 死代码 | `utils/common.py` `get_sender_info` (L441-491) | 全仓无外部引用；`InfoFilter` 内联发送者逻辑 | 低 | 删除整块 |
| 3 | 死代码 | `utils/common.py` `process_user_info` (L678-704) | 全仓无调用 | 低 | 删除整块（依赖 #2） |
| 4 | 冗余 `__all__` | `ai/__init__.py` | 运行时仅 `get_ai_provider` 被 `ai_filter` / `summary_scheduler` 引用 | 低 | 可选收窄为仅 `get_ai_provider` |
| 5 | 本地缓存 | `__pycache__/` | 已 gitignore | 无 | 本地删除，不入库 |

### Diff #1

```diff
-from models.models import MediaTypes
-from models.models import get_db_session
+from models.models import MediaTypes, get_db_session
```

---

## 二、建议简化

| # | 位置 | 原因 | 风险 | 建议 |
|---|------|------|------|------|
| 1 | `filters/filter_chain.py` `add_filter` `return self` | 仅 `process.py` 循环调用，无链式 | 极低 | 去掉 `return self` |
| 2 | `handlers/button/callback/other_callback.py` `cancel_state_after_timeout` | 与 `StateManager.set_state` 内 `_timeout_clear` 双路径 | 中 | 统一用 StateManager；删 create_task 路径（需手测模板设置） |
| 3 | `managers/state_manager.py` `get_state` 三元组兼容 | 旧 `(user_id, chat_id)` 形态 | 低 | 确认无旧内存态后删 else |
| 4 | `filters/process.py` | 12 次 `add_filter` | 低 | 可选 `FilterChain([...])` 构造注入 |
| 5 | `utils/common.py` ~748 LOC | 维护性 | — | **本次不拆分**（避免 scope 膨胀） |

---

## 三、需确认（含缺陷，非“删 import”）

| # | 位置 | 说明 | 建议 |
|---|------|------|------|
| 1 | **`utils/constants.py` vs `utils/common.py`** | `common` L15 导入 `AI_SETTINGS_TEXT`, `MEDIA_SETTINGS_TEXT`，当前 `constants.py` **未定义**；`14b5b50 refactor: simplify configuration` 移除了 `AI_SETTINGS_TEXT`（git 历史可见）。`get_media_settings_text()` 直接 `return MEDIA_SETTINGS_TEXT` | **优先修复**：在 `constants.py` 恢复模板，或改为固定短文案/从 settings 生成；`git show 937775b:utils/constants.py` 可找回 `AI_SETTINGS_TEXT` |
| 2 | `handlers/AGENTS.md` / 根 `AGENTS.md` | 提及 `user_handler.py`，仓库不存在 | 文档改为 `message_listener` + `filters/process.py` |
| 3 | `README.md` | 旧 callback 名（如 `menu_main`） | 与 `callback_handlers` 对齐 |
| 4 | 无单测 | 删符号仅靠 grep | 清理后 `python3 -m compileall .` + 手测 `/settings` AI/媒体页 |
| 5 | `get_db_ops` / `init_db_ops` | 懒加载，无 direct caller | **保留** |

### 历史 `AI_SETTINGS_TEXT`（937775b）

```python
AI_SETTINGS_TEXT = """
当前AI提示词：

`{ai_prompt}`

当前总结提示词：

`{summary_prompt}`
"""
```

`MEDIA_SETTINGS_TEXT`（`09038fc` 历史）为静态文案：

```python
MEDIA_SETTINGS_TEXT = """
媒体设置：
"""
```

---

## 落地顺序

1. 修复 #三-1（常量缺失）— 否则 AI/媒体设置页可能 `ImportError`  
2. 应用「一」#1-#3  
3. 可选「二」#1、#2（#2 需手测）  
4. 文档 #三-2、#三-3  

---

## 待你确认

- 是否允许应用「一」全部 diff？  
- `MEDIA_SETTINGS_TEXT` 期望文案：恢复历史 / 简化为「见下方按钮」/ 其它？