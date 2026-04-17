# ai/

## OVERVIEW
仅支持用户指定的兼容 OpenAI API 接口。

## STRUCTURE
```
ai/
├── __init__.py              # get_ai_provider 入口
├── base.py                  # BaseAIProvider 抽象类
└── openai_base_provider.py  # CustomOpenAIProvider 实现
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| AI处理逻辑 | `openai_base_provider.py` | CustomOpenAIProvider |
| 获取提供商 | `__init__.py` | get_ai_provider(model) |

## CONVENTIONS
- 所有Provider继承`BaseAIProvider`
- 必须实现`process_message()`和`initialize()`
- API Key 和 API Base 必须从环境变量配置
- 不支持官方接口，只能用第三方兼容 OpenAI 的 API

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `BaseAIProvider` | class | base.py | 抽象基类 |
| `CustomOpenAIProvider` | class | openai_base_provider.py | 唯一Provider |
| `get_ai_provider` | function | __init__.py | 工厂函数 |
