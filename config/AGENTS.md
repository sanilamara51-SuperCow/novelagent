# CONFIG KNOWLEDGE BASE

**Parent:** `../AGENTS.md`

## OVERVIEW
配置目录，包含 YAML 主配置和 8 个 Agent 的 System Prompt（支持 3 种写作模式）。

## STRUCTURE
```
config/
├── settings.yaml          # 主配置 (LLM/Agent/RAG/工作流/写作模式)
└── prompts/
    ├── world_builder.txt
    ├── plot_designer.txt
    ├── writer.txt
    ├── sandbox_debater.txt
    ├── consistency_checker.txt
    ├── style_polisher.txt
    ├── emotion_risk_control.txt
    └── pacing_optimizer.txt    # 节奏优化器
```

## SETTINGS.YAML

### 关键段
- `llm.models` — LiteLLM 格式的模型配置
- `agents.{name}` — 各 Agent 的模型和参数
- `rag` — ChromaDB 配置
- `memory` — 记忆系统参数
- `workflow` — 工作流设置 (auto_mode 等)
- `project.writing_mode` — 当前写作模式 (quality/volume/hybrid)
- `writing_modes` — 各模式的详细配置 (字数/节奏密度/卡点模式)

### 环境变量
所有 API Key 通过 `${ENV_VAR}` 注入：
- `ARK_API_KEY` — 火山方舟 (Kimi)
- `DEEPSEEK_API_KEY` — DeepSeek
- `OPENAI_API_KEY` — OpenAI
- `OPENROUTER_API_KEY` — OpenRouter

## PROMPT 格式
每个 `.txt` 文件是一个完整 System Prompt，支持 Jinja2 风格变量 (如 `{{ era }}`)。

## 写作模式

| 模式 | 字数 | 冲突密度 | 卡点 | 质量检查 |
|------|------|----------|------|----------|
| quality | 2500-3500 字 | 0.5 次/千字 | soft | 完整 pipeline |
| volume | 1500-2000 字 | 1.0 次/千字 | hard | 快速模式 |
| hybrid | 2000-2800 字 | 0.7 次/千字 | soft | 标准 pipeline |

## ANTI-PATTERNS
- **勿提交含 Key 的配置**: 用 `.env`+`${}` 占位符
- **勿修改默认 temperature**: 如需调整在代码中覆盖
- **勿删除 prompt 注释**: 保留 Prompt 内的说明注释
