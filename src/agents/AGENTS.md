# AGENTS KNOWLEDGE BASE

**Parent:** `../src/AGENTS.md`

## OVERVIEW
7个专用Agent实现，各司其职完成小说创作流水线。

## AGENTS

| Agent | File | Model | 输入 | 输出 |
|-------|------|-------|------|------|
| WorldBuilder | `world_builder.py` | deepseek-chat | 用户创意 | world_setting.json |
| PlotDesigner | `plot_designer.py` | deepseek-chat | 世界观 | outline.json |
| Writer | `writer.py` | deepseek-chat | 大纲+上下文 | 章节正文 |
| SandboxDebater | `sandbox_debater.py` | NPC:deepseek-chat Host:deepseek-chat | 议题+NPC列表 | 辩论记录 |
| ConsistencyChecker | `consistency_checker.py` | deepseek-chat | 章节+设定 | 审查报告 |
| StylePolisher | `style_polisher.py` | deepseek-chat | 初稿 | 润色稿 |
| EmotionRiskControl | `emotion_risk_control.py` | deepseek-chat | 润色稿+大纲 | 风险评估 |

## IMPLEMENTATION

### 基础模板
```python
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput

class MyAgent(BaseAgent):
    def __init__(self, config, llm_client):
        super().__init__("my_agent", config, llm_client, "prompts/my_agent.txt")
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        messages = self._build_messages([
            ("system", self.system_prompt),
            ("user", input_data.context),
        ])
        response = await self._call_llm(
            messages=messages,
            model=self.config.model,
            max_tokens=self.config.max_tokens,
        )
        return AgentOutput(
            agent_name=self.name,
            success=True,
            content=response.content,
            metadata={"tokens": response.usage},
        )
```

### 特殊Agent
- **SandboxDebater**: 不使用标准`process()`，用`run_debate()`
- **ConsistencyChecker**: 用`check_with_retry()`，返回结构化报告
- **EmotionRiskControl**: 用`assess()`，返回风险评估对象

## PROMPT位置
`config/prompts/{agent_name}.txt`

## ANTI-PATTERNS
- **勿跳过BaseAgent**: 必须继承，统一处理LLM调用
- **勿硬编码模型**: 从`self.config.model`读取
- **勿同步调用**: LLM必须用`await self._call_llm()`
