# filters/

## OVERVIEW
消息过滤器链 (16个过滤器)，负责消息的完整处理流程。

## STRUCTURE
```
filters/
├── base_filter.py       # 抽象基类
├── filter_chain.py      # 过滤器编排
├── context.py           # MessageContext 上下文
├── process.py           # 入口 - process_forward_rule
└── *_filter.py          # 16个具体过滤器
```

## FILTER EXECUTION ORDER
```
init_filter → delay_filter → keyword_filter → replace_filter → 
media_filter → ai_filter → info_filter → comment_button_filter → 
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| 添加新过滤器 | `base_filter.py` | 继承BaseFilter |
| 修改执行顺序 | `process.py` | FilterChain.add_filter顺序 |
| 过滤器中断逻辑 | `filter_chain.py` | 返回False中断处理链 |

## CONVENTIONS
- 过滤器必须继承`BaseFilter`抽象类
- 必须实现`_process(context)`异步方法
- 返回`False`中断处理链，返回`True`继续
- 使用`context.errors`记录错误
- 使用`logging.getLogger(__name__)`

## ANTI-PATTERNS
- **禁止**: 在过滤器外直接操作数据库会话
- **禁止**: 抛出未捕获的异常（用context.errors记录）
- **禁止**: 修改`PROCESSED_GROUPS`（用`clear_group_cache()`）

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `BaseFilter` | class | base_filter.py | 抽象基类 |
| `FilterChain` | class | filter_chain.py | 过滤器编排 |
| `MessageContext` | class | context.py | 消息上下文 |
| `process_forward_rule` | function | process.py | 入口函数 |
