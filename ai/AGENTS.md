# ai/

## OVERVIEW
AI提供商抽象层，支持多厂商API调用。

## STRUCTURE
```
ai/
├── __init__.py           # get_ai_provider 入口
├── base.py               # BaseAIProvider 抽象类
├── openai_base_provider.py # OpenAI兼容基类
├── openai_provider.py    # OpenAI
├── claude_provider.py    # Anthropic Claude
├── gemini_provider.py    # Google Gemini
├── deepseek_provider.py  # DeepSeek
├── qwen_provider.py      # 通义千问
└── grok_provider.py      # xAI Grok
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| 添加新提供商 | `base.py` | 继承BaseAIProvider |
| 获取提供商 | `__init__.py` | get_ai_provider(model) |
| 模型配置 | `config/ai_models.json` | 自定义模型名 |

## CONVENTIONS
- 所有Provider继承`BaseAIProvider`
- 必须实现`process_message()`和`initialize()`
- OpenAI兼容API继承`openai_base_provider.py`
- API Key从环境变量读取

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `BaseAIProvider` | class | base.py | 抽象基类 |
| `get_ai_provider` | function | __init__.py | 工厂函数 |
