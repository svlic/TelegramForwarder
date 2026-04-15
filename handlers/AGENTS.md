# handlers/

## OVERVIEW
命令处理器、按钮回调、用户消息处理。

## STRUCTURE
```
handlers/
├── bot_handler.py       # 命令分发入口
├── command_handlers.py  # 所有 /command 处理函数
├── user_handler.py      # 用户模式转发处理
├── list_handlers.py     # 列表显示处理
├── link_handlers.py     # 链接转发功能
├── prompt_handlers.py   # 提示词设置处理
└── button/
    ├── callback/         # 按钮回调处理
    ├── settings_manager.py
    └── ...
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| 添加新命令 | `bot_handler.py` | command_handlers字典 |
| 命令实现 | `command_handlers.py` | handle_*_command函数 |
| 按钮回调 | `button/callback/` | callback_handlers.py |
| 用户模式转发 | `user_handler.py` | process_forward_rule |

## CONVENTIONS
- 命令处理函数: `handle_*_command(event, ...)`
- 使用`async_delete_user_message`删除用户消息
- 使用`reply_and_delete`回复并删除
- 数据库操作后`session.commit()`
- 使用`shlex.split()`处理带引号的参数

## ANTI-PATTERNS
- **禁止**: 同步调用Telethon方法
- **禁止**: 直接`session.commit()`后不处理异常
