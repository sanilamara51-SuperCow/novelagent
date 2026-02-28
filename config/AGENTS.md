# CONFIG KNOWLEDGE BASE

**Parent:** `../AGENTS.md`

## OVERVIEW
配置目录，包含YAML主配置和7个Agent的System Prompt。

## STRUCTURE
```
config/
├── settings.yaml          # 主配置(LLM/Agent/RAG/工作流)
└── prompts/
    ├── world_builder.txt
    ├── plot_designer.txt
    ├── writer.txt
    ├── sandbox_debater.txt
    ├── consistency_checker.txt
    ├── style_polisher.txt
    └── emotion_risk_control.txt
```

## SETTINGS.YAML

### 关键段
- `llm.models` — LiteLLM格式的模型配置
- `agents.{name}` — 各Agent的模型和参数
- `rag` — ChromaDB配置
- `memory` — 记忆系统参数
- `workflow` — 工作流设置(auto_mode等)

### 环境变量
所有API Key通过`${ENV_VAR}`注入：
- `ARK_API_KEY` — 火山方舟(Kimi)
- `DEEPSEEK_API_KEY` — DeepSeek
- `OPENAI_API_KEY` — OpenAI
- `OPENROUTER_API_KEY` — OpenRouter

## PROMPT格式
每个`.txt`文件是一个完整System Prompt，支持Jinja2风格变量(如`{{ era }}`)。

## ANTI-PATTERNS
- **勿提交含Key的配置**: 用`.env`+`${}`占位符
- **勿修改默认temperature**: 如需调整在代码中覆盖
- **勿删除prompt注释**: 保留Prompt内的说明注释
