# MODELS KNOWLEDGE BASE

**Parent:** `../src/AGENTS.md`

## OVERVIEW
多模型LLM客户端，支持DeepSeek/豆包/Kimi K2等模型动态路由。

## STRUCTURE
```
models/
├── llm_client.py      # MultiModelClient + ModelRegistry
├── llm_client_backup.py # 备份实现
├── data_models.py    # Pydantic数据模型
└── __init__.py
```

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `MultiModelClient` | Class | `llm_client.py` | 主客户端，聚合所有模型 |
| `ModelRegistry` | Class | `llm_client.py` | 配置驱动模型注册表 |
| `LLMResponse` | Dataclass | `llm_client.py` | 标准化响应 |

## USAGE

### 基础调用
```python
from src.models.llm_client import MultiModelClient

client = MultiModelClient()

# DeepSeek - 战略/骨架/历史考据
await client.call_deepseek(messages)

# 豆包 - 情感/细节/环境描写
await client.call_doubao(messages)

# Kimi K2 - 对话/口语化
await client.call_kimi(messages)
```

### 配置驱动
```python
registry = ModelRegistry(config)
model = await registry.acompletion(messages, model_name="deepseek-chat")
```

## CONVENTIONS
- API Key从环境变量读取：`DEEPSEEK_API_KEY`、`ARK_API_KEY`等
- 超时默认60s，重试3次
- 响应标准化为`LLMResponse`

## ANTI-PATTERNS
- **勿硬编码API Key**: 必须从环境变量或配置文件读取
- **勿直接实例化AsyncOpenAI**: 通过`ModelRegistry`统一管理
