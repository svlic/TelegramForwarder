# Code Cleanup Report: TelegramForwarder v1.7.2

> **Scope**: 46 Python files + `requirements.txt`  
> **Method**: AST-based static analysis + cross-file reference verification + manual source review  
> **Constraint**: No behavior changes, no API breakage

---

## 1. 可直接清理（高置信度 · 零风险）

### 1.1 `models/models.py` — 冗余 `load_dotenv()`

| 项 | 内容 |
|---|---|
| **位置** | `models/models.py:7-9` |
| **类型** | 冗余初始化 |
| **原因** | `load_dotenv()` 已在 `utils/constants.py:5` 和 `main.py:29` 执行，此处重复加载无实际作用。 |
| **风险** | 无 — 多次调用 `load_dotenv()` 是幂等的，删除不影响行为。 |

```diff
--- a/models/models.py
+++ b/models/models.py
@@ -1,9 +1,6 @@
 from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Enum, UniqueConstraint, inspect, text
 from sqlalchemy.ext.declarative import declarative_base
 from sqlalchemy.orm import relationship, sessionmaker
 from enums.enums import ForwardMode, PreviewMode, MessageMode, AddMode, HandleMode
 import logging
 import os
-from dotenv import load_dotenv
-
-load_dotenv()
 Base = declarative_base()
```

---

### 1.2 `utils/media.py` — 死函数 `get_max_media_size()`

| 项 | 内容 |
|---|---|
| **位置** | `utils/media.py:31-37` |
| **类型** | 死代码（零引用） |
| **原因** | 函数定义后从未被任何文件调用；项目使用 `utils/constants.py` 中的 `DEFAULT_MAX_MEDIA_SIZE` 常量管理媒体大小限制。 |
| **风险** | 无 — 零 cross-file 引用，删除不影响任何逻辑。 |

```diff
--- a/utils/media.py
+++ b/utils/media.py
@@ -28,10 +28,3 @@
         logger.error(f'获取媒体大小时出错: {str(e)}')
 
     return 0
-
-async def get_max_media_size():
-    """获取媒体文件大小上限"""
-    max_media_size_str = os.getenv('MAX_MEDIA_SIZE')
-    if not max_media_size_str:
-        logger.warning('未设置 MAX_MEDIA_SIZE 环境变量，使用默认值 100MB')
-        return 100 * 1024 * 1024  # 默认100MB
-    return float(max_media_size_str) * 1024 * 1024  # 转换为字节，支持小数
```

---

### 1.3 `utils/common.py` — 死函数 `get_user_client()`

| 项 | 内容 |
|---|---|
| **位置** | `utils/common.py:49-52` |
| **类型** | 死代码（零引用） |
| **原因** | 定义后从未被调用；项目中直接通过 `main.user_client` 或 `main.bot_client` 访问客户端。 |
| **风险** | 无 — 零 cross-file 引用。 |

```diff
--- a/utils/common.py
+++ b/utils/common.py
@@ -46,11 +46,6 @@
     spec.loader.exec_module(main)
     return main
 
-async def get_user_client():
-    """获取用户客户端"""
-    main = await get_main_module()
-    return main.user_client
-
 async def get_bot_client():
     """获取机器人客户端"""
     main = await get_main_module()
```

---

## 2. 建议简化（低复杂度 · 可评估后执行）

### 2.1 全局冗余 `load_dotenv()` 调用（7 处）

| 项 | 内容 |
|---|---|
| **位置** | `main.py:29`, `message_listener.py:15`, `handlers/bot_handler.py:32`, `models/db_operations.py:14`, `models/models.py:9`, `utils/log_config.py:10`, `utils/constants.py:5` |
| **类型** | 重复初始化 |
| **原因** | `python-dotenv` 的 `load_dotenv()` 在首次调用后即填充 `os.environ`，后续调用无实际效果。保留 `main.py`（入口文件）和 `utils/constants.py`（配置集中地）即可覆盖所有模块的导入依赖。 |
| **风险** | 极低 — 需确认各模块是否独立运行（如测试、脚本），若是则需保留对应文件的 `load_dotenv()`。 |
| **建议** | 删除 `message_listener.py`, `handlers/bot_handler.py`, `models/db_operations.py`, `models/models.py`, `utils/log_config.py` 中的调用，仅保留 `main.py` 和 `utils/constants.py`。 |

```diff
--- a/message_listener.py
+++ b/message_listener.py
@@ -12,9 +12,6 @@
 from utils.constants import BOT_MESSAGE_DELETE_TIMEOUT
 from utils.log_config import get_message_link
 import logging
-from dotenv import load_dotenv
-
-load_dotenv()
 
 # ...
 
--- a/handlers/bot_handler.py
+++ b/handlers/bot_handler.py
@@ -29,9 +29,6 @@
 from models.models import get_db_session
 from utils.common import normalize_channel_id
 import logging
-from dotenv import load_dotenv
-
-load_dotenv()
 
 # ...
 
--- a/models/db_operations.py
+++ b/models/db_operations.py
@@ -11,9 +11,6 @@
 from models.models import Chat, ForwardRule, ReplaceRule, Keyword, get_db_session
 import logging
 import asyncio
-from dotenv import load_dotenv
-
-load_dotenv()
 
 # ...
 
--- a/utils/log_config.py
+++ b/utils/log_config.py
@@ -7,9 +7,6 @@
 import logging
 import os
 from datetime import datetime
-from dotenv import load_dotenv
-
-load_dotenv()
 
 # ...
```

---

### 2.2 `requirements.txt` — 未使用的 AI Provider 依赖

| 项 | 内容 |
|---|---|
| **位置** | `requirements.txt` |
| **类型** | 未使用依赖 |
| **原因** | 根据 `ai/AGENTS.md` 和源码确认，项目**仅支持 OpenAI 兼容接口**（`CustomOpenAIProvider`），未使用 Anthropic、Gemini、DashScope 的官方 SDK。以下包可安全移除： |
| **可移除** | `anthropic==0.46.0`, `google-generativeai==0.8.4`, `dashscope==1.22.1`, `google==3.0.0`, `google-ai-generativelanguage==0.6.15`, `google-api-core==2.24.1`, `google-api-python-client==2.161.0`, `google-auth==2.38.0`, `google-auth-httplib2==0.2.0`, `googleapis-common-protos==1.67.0`, `grpcio==1.70.0`, `grpcio-status==1.70.0` |
| **风险** | 低 — 需确认是否有其他模块（如未扫描的脚本）直接使用这些包。建议先执行 `grep -r "anthropic\|google.generativeai\|dashscope" --include="*.py" .` 二次确认。 |

```diff
--- a/requirements.txt
+++ b/requirements.txt
@@ -19,18 +19,6 @@
 
 # AI Providers
 openai==1.63.2
-anthropic==0.46.0
-google-generativeai==0.8.4
-dashscope==1.22.1
-
-# Google (Gemini)
-google==3.0.0
-google-ai-generativelanguage==0.6.15
-google-api-core==2.24.1
-google-api-python-client==2.161.0
-google-auth==2.38.0
-google-auth-httplib2==0.2.0
-googleapis-common-protos==1.67.0
-grpcio==1.70.0
-grpcio-status==1.70.0
 
 # Config & Utils
 python-dotenv==1.0.0
```

---

## 3. 需确认（潜在清理项 · 需进一步验证）

### 3.1 `ai/__init__.py` — `model` 参数

| 项 | 内容 |
|---|---|
| **位置** | `ai/__init__.py:9` |
| **类型** | 疑似死参数 |
| **现状** | `get_ai_provider(model=None)` 接受 `model` 参数，对其做 truthiness 检查后丢弃，始终返回 `CustomOpenAIProvider()`。 |
| **疑问** | 移除参数或放宽校验会改变行为（不再对 `None` 抛出 `ValueError`）。需确认所有调用点是否依赖该异常作为前置校验。 |
| **建议** | 搜索 `get_ai_provider(` 的所有调用点，确认是否始终传入非空 `model`；若是，可安全移除参数和校验。 |

### 3.2 `ufb/ufb_client.py` — 重复定义 `get_main_module()` / `get_db_ops()`

| 项 | 内容 |
|---|---|
| **位置** | `ufb/ufb_client.py:14-33` |
| **类型** | 重复代码 |
| **现状** | `ufb_client.py` 内嵌了与 `utils/common.py:35-64` 完全相同的 `get_main_module()` 和 `get_db_ops()` 实现，并在内部使用（`line 77: db_ops = await get_db_ops()`）。 |
| **疑问** | `ufb_client.py` 未从 `utils.common` 导入这两个函数。直接替换为导入可能引入循环导入或模块路径问题（`ufb/` 与 `utils/` 的相对路径关系）。 |
| **建议** | 测试将 `ufb/ufb_client.py` 中的内嵌定义替换为 `from utils.common import get_main_module, get_db_ops`，验证启动无异常后再清理。 |

### 3.3 `main.py` — `types` 导入

| 项 | 内容 |
|---|---|
| **位置** | `main.py:1` |
| **类型** | 疑似未使用导入 |
| **现状** | `from telethon import TelegramClient, types` 导入了 `types` 模块，但 `main.py` 中仅使用 `types.BotCommandScopeDefault()`（`line 295`）和一处被注释掉的代码（`line 130`）。而 `BotCommand` 已从 `telethon.tl.types` 单独导入（`line 2`）。 |
| **疑问** | `types.BotCommandScopeDefault()` 是否必须？Telethon 中 `BotCommandScopeDefault` 也可从 `telethon.tl.types` 直接导入。需确认替换后是否等价。 |
| **建议** | 若确认 `from telethon.tl.types import BotCommandScopeDefault` 可用，可移除 `main.py:1` 中的 `types` 导入。 |

---

## 4. 排除项（分析后确认无需清理）

以下项目经人工复核后**确认活跃使用**，不构成清理项：

| 文件 | 项目 | 复核结果 |
|---|---|---|
| `ai/base.py:2` | `Optional`, `Dict`, `List` | 用于抽象方法签名，活跃使用 |
| `ai/openai_base_provider.py:1` | `Optional`, `List`, `Dict` | 用于方法签名，活跃使用 |
| `ai/__init__.py:3` | `BaseAIProvider` | 在 `__all__` 中显式导出，为公共 API |
| `scheduler/summary_scheduler.py:7` | `TelegramClient` | 用于 `__init__` 类型注解 |
| `scheduler/chat_updater.py:5` | `TelegramClient` | 用于 `__init__` 类型注解 |
| `utils/common.py:8` | `re` | 在 `line 487` 和 `line 490` 活跃使用 |
| `utils/common.py:5` | `ChannelParticipantsAdmins` | 在 `line 179` 活跃使用 |
| `models/models.py:1` | `inspect`, `text` | 在数据库迁移逻辑中活跃使用 |
| `models/db_operations.py:6-7` | `json`, `time` | 在配置读写和 WebSocket 消息中活跃使用 |
| `handlers/command_handlers.py:3` | `traceback` | 在 `line 173` 和 `line 881` 活跃使用 |
| `main.py:1` | `glob`, `shutil` | 在临时目录清理逻辑中活跃使用 |
| `handlers/command_handlers.py:4` | `shlex` | 在 `line 30` 活跃使用 |

---

## 5. 清理优先级建议

1. **P0（立即执行）**: 1.1, 1.2, 1.3 — 零风险删除
2. **P1（验证后执行）**: 2.1 — 需确认模块独立运行场景
3. **P2（评估后执行）**: 2.2 — 建议二次 grep 确认无其他使用者
4. **P3（需决策）**: 3.1, 3.2, 3.3 — 需用户确认是否接受微小结构调整

---

*报告完成。请确认后执行清理。*
