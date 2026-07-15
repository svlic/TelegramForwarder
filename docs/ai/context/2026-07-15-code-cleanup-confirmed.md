# 代码清理落地记录（已确认项）

**日期**: 2026-07-15  
**范围**: 审查报告中「可直接清理 / 建议简化 / 需确认 1·2」  
**原则**: 功能等价、最小 diff、不改外部行为

## 已落地

### 1. `managers/state_manager.py`
- 删除 `get_state` 中 2-tuple 旧格式兼容分支；状态统一为 `(state, message, state_type)` 3-tuple。
- `clear_state` / `_timeout_clear` 删除改用 `dict.pop()`，避免 `in` + `del` 双查。

### 2. `scheduler/summary_scheduler.py`
- 删除分页循环中不可达的 `else: break`（空批次已在上游 `break`）。
- `next_offset_id` 推进逻辑不再包在 `if messages_batch` 内。

### 3. Telegram 配置统一入口
- `main.py`: 在导入 `utils.constants` **之前**调用 `load_dotenv()`，再从 constants 读取 `API_ID` / `API_HASH` / `BOT_TOKEN` / `PHONE_NUMBER`。
- `utils/constants.py`: 删除从未被 import 的 `USER_ID`、`ADMINS`（`utils/common.py` 仍直接 `os.getenv`）。
- 保留 constants 中的 Telegram 四项，作为统一配置入口。

### 4. bare `return` 清理
- `handlers/button/callback/ai_callback.py`: 删除 10 处函数末尾无意义 `return`。
- `handlers/button/callback/other_callback.py`: 删除 21 处函数末尾无意义 `return`。
- 仅处理函数体最后一条「无返回值 return」，保留早退 guard。

### 5. 未引用图片（需确认 1）
删除 `images/` 下 6 张无代码/文档引用的资源：
- `1 (2).png`
- `1 (3).png`
- `Fluent_Reader_rrt59DN9LZ.png`
- `image.png`
- `settings_media_sub1.png`
- `settings_other.png`

保留 README 引用图：`flow_chart.png`、`settings_*.png`（main/ai/media）、`user_spy.png`、`logo/`。

## 未改（有意保留）
- `utils/common.py` 中 `USER_ID` / `ADMINS` 的 `os.getenv` 读取路径（运行时仍需要）。
- `requirements.txt` 中 `pyaes` / `cryptg`（见 2026-07-06 followup 决策）。

## 验证
- `.venv/bin/python -m compileall -q`（改动文件）通过
- `.venv/bin/python -m pytest -q` → **21 passed**
