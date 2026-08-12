# 消息处理契约

本文记录跨模块且容易被局部修改破坏的约束。实现以代码为准；修改过滤链或相关状态时同步更新本文。

## 入口与职责

1. `main.py` 启动用户客户端和 Bot 客户端，注册监听器，并启动总结与聊天更新任务。
2. `message_listener.py` 接收源消息，用数据库保存的原始聊天 ID 查找规则，并对每条启用规则调用 `process_forward_rule()`。
3. `filters/process.py` 创建 `MessageContext` 并按固定顺序执行过滤器。
4. `SenderFilter` 仅负责转发模式发送；`EditFilter` 负责编辑模式；`ReplyFilter` 处理发送后的回复关联。

## 过滤顺序

```text
InitFilter
→ DelayFilter
→ TextNormalizeFilter
→ KeywordFilter
→ ReplaceFilter
→ MediaFilter
→ AIFilter
→ InfoFilter
→ CommentButtonFilter
→ EditFilter
→ SenderFilter
→ ReplyFilter
```

顺序具有语义：延迟后重新读取消息，文本标准化先于匹配，替换先于 AI，附加信息和评论按钮在最终编辑或发送前完成。过滤器返回 `False` 会中止后续步骤；异常也会阻止转发。过滤链退出时始终清理 `context.media_files`。

## 上下文状态

- `original_message_text` 保存初始文本；处理过程修改 `message_text` 和匹配用的 `check_message_text`。
- `should_forward` 是发送和编辑的总开关，后置过滤器不得绕过。
- `media_blocked`、`blocked_media_message_ids` 和 `skipped_media` 描述媒体过滤结果；EDIT 模式也必须尊重这些状态。
- `forwarded_messages` 供后续回复处理使用。
- `primary_message` 是媒体组 caption、链接和消息 ID 的基准。

## 媒体组

- 监听器按 `chat_id:grouped_id` 去重，缓存有效期为 5 分钟；缓存仅防止同一事件组重复进入规则处理。
- 同一媒体组的消息收集、主消息选择和临时文件生命周期应复用现有工具与 `MessageContext`。
- 不要在 `message_listener.py` 之外修改 `PROCESSED_GROUPS`，也不要引入第二套媒体组去重缓存。

## 聊天 ID 与状态

- 数据库查询必须保留 `/bind` 使用的 ID 表示，并通过 `get_telegram_chat_db_id()` 转换实体。
- Telegram 频道和超级群组统一为 `-100…`；普通群组负数 ID 和私聊正数 ID 保持原值。
- listener、command 和 callback 的状态读写都使用 `get_state_identity(event)`，避免频道缺少 `sender_id` 时产生不同的 `(user_id, chat_id)` 键。

## 异步与数据库边界

- 所有 Telethon API 都是异步调用。
- 用 `get_db_session()` 控制 SQLAlchemy 会话的提交、回滚与关闭。
- 查询出网络调用所需数据后先结束数据库会话，再执行 Telethon 或 AI 请求，避免长时间占用连接或使用失效 ORM 对象。
