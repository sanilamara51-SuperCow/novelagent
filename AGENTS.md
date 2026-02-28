# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-28 (Updated)
**Project:** novelagent — 北魏历史小说智能体
**Version:** 2.0 (Multi-Model Support)

## OVERVIEW
多智能体AI小说生成系统，专注于北魏历史小说创作。支持穿越/架空两种模式，具备史料知识库、沙盒辩论、质量风控等高级功能。

**最新更新:** 已支持 DeepSeek + 豆包 + Kimi K2 多模型协作

## STACK
- **Language:** Python 3.11+
- **LLM:** Multi-Model (DeepSeek + 豆包 + Kimi K2)
- **LLM Client:** OpenAI SDK (兼容火山引擎)
- **Vector DB:** ChromaDB + BAAI/bge-m3
- **CLI:** Click + Rich
- **State Machine:** python-statemachine

## STRUCTURE
```
novelagent/
├── src/                    # 核心源码
│   ├── agents/            # 7个专用Agent
│   ├── memory/            # 三层记忆系统
│   ├── knowledge/         # RAG/Embedding
│   ├── models/            # LLM客户端 (已修复多模型支持)
│   ├── utils/             # 工具
│   ├── main.py            # CLI入口
│   ├── orchestrator.py    # 编排核心
│   ├── state_machine.py   # 状态机
│   └── context_assembler.py
├── config/                # 配置+Prompts
│   ├── settings.yaml      # 主配置
│   └── prompts/           # Agent system prompts
├── data/                  # 知识库/小说存储
│   ├── knowledge_base/    # 史料 (通鉴151-156)
│   └── novels/            # 生成的小说
│       └── qiewei_001/    # 《窃魏》项目
├── scripts/               # 工具脚本
├── drafts/                # 创作草稿
└── requirements.txt
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| 添加新Agent | `src/agents/` | 继承`BaseAgent`, 实现`process()` |
| 修改工作流 | `src/state_machine.py` + `src/orchestrator.py` | 状态转换在此处定义 |
| 调整Prompt | `config/prompts/*.txt` | 按Agent名对应 |
| 多模型调用 | `src/models/llm_client.py` | MultiModelClient类 |
| 知识库操作 | `src/knowledge/` + `scripts/setup_kb.py` | ChromaDB相关 |
| 记忆系统 | `src/memory/` | 短期/长期/RAG三层架构 |
| 小说项目 | `data/novels/{novel_id}/` | 世界设定/大纲/章节 |

## CODE MAP

### Core Classes
| Symbol | File | Role |
|--------|------|------|
| `NovelStateMachine` | `state_machine.py` | 工作流状态机(13状态) |
| `Orchestrator` | `orchestrator.py` | Agent编排核心 |
| `BaseAgent` | `agents/base_agent.py` | Agent抽象基类 |
| `MultiModelClient` | `models/llm_client.py` | 多模型客户端(新增) |
| `ContextAssembler` | `context_assembler.py` | LLM上下文组装 |
| `MemoryManager` | `memory/memory_manager.py` | 三层记忆协调 |

### Multi-Model Client (新增)
```python
from src.models.llm_client import MultiModelClient

client = MultiModelClient()

# DeepSeek - 战略/骨架/历史考据
await client.call_deepseek(messages)

# 豆包 - 情感/细节/环境描写  
await client.call_doubao(messages)

# Kimi K2 - 对话/口语化/人物塑造
await client.call_kimi(messages)
```

### Agents (7个)
| Agent | File | 职责 |
|-------|------|------|
| WorldBuilder | `world_builder.py` | 世界观构建 |
| PlotDesigner | `plot_designer.py` | 大纲设计 |
| Writer | `writer.py` | 主笔创作 |
| SandboxDebater | `sandbox_debater.py` | 沙盒辩论(NPC多轮) |
| ConsistencyChecker | `consistency_checker.py` | 一致性审查 |
| StylePolisher | `style_polisher.py` | 风格润色 |
| EmotionRiskControl | `emotion_risk_control.py` | 情绪风控 |

## CONVENTIONS

### Agent实现
- 必须继承`BaseAgent`
- 必须实现`async def process(self, input_data: AgentInput) -> AgentOutput`
- System prompt放`config/prompts/{agent_name}.txt`
- 模型配置在`settings.yaml`的`agents:`段

### 多模型协作 (新增)
- DeepSeek: 战略、权谋、历史考据、骨架设计
- 豆包: 情感、细节、环境、女性角色
- Kimi K2: 对话、口语化、人物塑造、配角
- 人工整合: 去AI指纹、统一风格、调整节奏

### 状态机
- 使用`python-statemachine`库
- 状态转换通过`Orchestrator._safe_transition()`触发
- 状态持久化到`sm_state.json`

### 数据流
- 小说数据存`data/novels/{novel_id}/`
- 章节:`chapters/{chapter_id}.md`
- 角色:`characters/{char_id}.json`
- 世界设定:`world_setting.json`
- 大纲:`outline.json`

## ANTI-PATTERNS (THIS PROJECT)
- **勿用`as any`或`@ts-ignore`** — Python项目，无类型错误压制
- **勿阻塞asyncio** — 所有Agent调用必须异步
- **勿直接调用LLM** — 统一通过`MultiModelClient`或`BaseAgent._call_llm()`
- **勿跳过状态机** — 所有工作流转换必须经过`state_machine`
- **勿硬编码模型名** — 从`config.agents.{agent}.model`读取
- **勿用破折号堆砌** — AI写作指纹，改用动作打断
- **勿解释性句子** — "这意味着..."是AI特征，直接写感受

## UNIQUE STYLES

### Import Pattern
```python
from __future__ import annotations  # 文件首行
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.config import AppConfig  # 避免循环导入
```

### Multi-Model Writing Pattern (新增)
```python
# Step 1: DeepSeek写骨架
skeleton = await client.call_deepseek([
    ("system", "你是历史学家，设计权谋剧情"),
    ("user", "写第3章大纲...")
])

# Step 2: Kimi写对话  
dialogues = await client.call_kimi([
    ("system", "你是口语化作家，写人物对话"),
    ("user", "写阴世师试探魏渊的对话...")
])

# Step 3: 豆包写情感
emotion = await client.call_doubao([
    ("system", "你是女作家，写细腻情感"),
    ("user", "写李娥姿缝衣服的场景...")
])

# Step 4: 人工整合
# - 删掉破折号和解释句
# - 加口头禅和废话
# - 统一人称和节奏
```

### Agent Pattern
```python
class MyAgent(BaseAgent):
    async def process(self, input_data: AgentInput) -> AgentOutput:
        response = await self._call_llm(
            messages=self._build_messages([
                ("system", self.system_prompt),
                ("user", input_data.context),
            ]),
            model=self.config.model,
            max_tokens=self.config.max_tokens,
        )
        return AgentOutput(
            agent_name=self.name,
            success=True,
            content=response.content,
            metadata={...},
        )
```

## COMMANDS
```bash
# 运行CLI
cd novelagent
python -m src.main

# 或直接用
python src/main.py

# 安装依赖
pip install -r requirements.txt

# 设置知识库
python scripts/setup_kb.py

# 测试多模型
python test_multi.py
```

## PROJECT STATS
- **Files:** 70 total
- **Python LOC:** ~13,762
- **Max Depth:** 3 levels
- **AGENTS.md:** 6 files
- **Novel Project:** 《窃魏》(200+章规划)

## NOTES
- **入口非标准**: `main.py`在`src/`下，非项目根目录
- **无测试目录**: pytest在requirements.txt但无`tests/`
- **无pyproject.toml**: 仅用requirements.txt
- **双目录嵌套**: 项目实际在`novel/novelagent/`
- **TODO标记**: `main.py`有多个TODO待实现
- **模型配置**: 默认全用`deepseek-chat`（可通过settings.yaml切换）
- **多模型密钥**: DeepSeek从.env读取，火山引擎密钥硬编码在llm_client.py
- **编码问题**: Windows终端有UTF-8显示问题，但文件写入正常

## WORKFLOW
```
idle → init → world_building → world_review → outline_design 
  → outline_review → chapter_writing → [debate] → consistency_check 
  → style_polish → emotion_risk → chapter_review → memory_update 
  → (loop chapter_writing or → completed)
```

## 当前项目:《窃魏》
- **Status:** 已生成200+章大纲，写完第1-2章
- **Models:** DeepSeek(骨架) + 豆包(情感) + Kimi(对话)
- **Next:** 第三章《洛阳来使》多模型协作创作
