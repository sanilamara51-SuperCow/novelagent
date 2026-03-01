# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent AI system for autonomous historical novel generation. The current project is 《窃魏》(qiewei_001) — a North Wei (北魏, 528-532 CE) time-travel fiction with 200+ chapters outlined.

## Setup & Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize knowledge base (run once)
python scripts/setup_kb.py --raw-dir data/knowledge_base/raw

# CLI entry point (in src/, not project root)
python -m src.main new --title "Title" --novel-id novel_id
python -m src.main write --novel-id qiewei_001 --range 1-10 --auto
python -m src.main resume --novel-id qiewei_001
python -m src.main status
python -m src.main export qiewei_001 --format txt

# Direct scripts (bypass CLI)
python create_qiewei.py
python multi_model_ch3.py
```

No Makefile, pyproject.toml, or test suite exists. `pytest` is in requirements but there is no `tests/` directory.

## Architecture

### Workflow (13-State Machine)
`state_machine.py` drives the full pipeline:
```
idle → init → world_building → world_review → outline_design
  → outline_review → chapter_writing → [debate] → consistency_check
  → style_polish → emotion_risk → chapter_review → memory_update → (loop)
```

### Core Components

| File | Role |
|------|------|
| `src/orchestrator.py` | Central coordinator — manages all agents, state transitions, error recovery |
| `src/state_machine.py` | `NovelStateMachine` with 13 states |
| `src/context_assembler.py` | Builds LLM context from memory + RAG |
| `src/agents/base_agent.py` | Abstract base; all agents inherit this |
| `src/models/llm_client.py` | `ModelRegistry` — config-driven multi-model LLM client |
| `src/memory/memory_manager.py` | Coordinates 3-layer memory (short-term, long-term SQLite, summarizer) |
| `src/utils/persistence.py` | `NovelStorage` — JSON chapters/outlines + SQLite long-term memory |
| `config/settings.yaml` | All model assignments, RAG params, memory window sizes |

### 7 Specialized Agents (`src/agents/`)
- **WorldBuilder** — world setting, timeline, factions
- **PlotDesigner** — chapter outlines
- **Writer** — chapter content (3000–5000 words)
- **SandboxDebater** — multi-NPC debate simulation (configurable rounds)
- **ConsistencyChecker** — plot/character validation
- **StylePolisher** — prose refinement
- **EmotionRiskControl** — content risk assessment

### Memory System (`src/memory/`)
- **Short-term**: 3-chapter sliding window
- **Long-term**: SQLite (`memory.sqlite`) for character states and timeline events
- **Summarizer**: Generates chapter summaries after each write

### RAG System (`src/knowledge/`)
- ChromaDB vector DB with BAAI/bge-m3 embeddings
- Ingests 资治通鉴 volumes 151–156 from `data/knowledge_base/raw/`
- Top-k=5 retrieval, chunk_size=800, overlap=150

## Configuration

`config/settings.yaml` controls everything — model assignments per agent, RAG params, memory window. Agent system prompts live in `config/prompts/*.txt`.

**LLM Backends** (OpenAI-compatible):
- 火山方舟 (Volcano Ark): Kimi K2.5 — primary model for all agents
- DeepSeek: strategic/structural tasks
- Doubao: emotional depth, female character perspectives

API keys in `.env` (see `.env.example`). 火山方舟 endpoint is configured in `llm_client.py`.

## Data Layout

```
data/novels/{novel_id}/
  world_setting.json   # WorldSetting Pydantic model
  outline.json         # ChapterOutline list
  characters/          # Character cards
  chapters/            # Generated .md chapter files
  summaries/           # Chapter summaries
  memory.sqlite        # Long-term memory DB
```

State machine persists to `sm_state.json` at project root.

## Key Conventions

**Agent implementation pattern:**
```python
class MyAgent(BaseAgent):
    async def process(self, input_data: AgentInput) -> AgentOutput:
        response = await self._call_llm(
            messages=self._build_messages([...]),
            model=self.config.model,
            max_tokens=self.config.max_tokens,
        )
        return AgentOutput(agent_name=self.name, success=True, content=response.content)
```

**Avoid:**
- Direct LLM calls — always go through `ModelRegistry`/`MultiModelClient`
- Hardcoded model names — use config
- Bypassing the state machine
- Blocking asyncio calls
- Em-dashes and explanatory filler sentences in generated prose (AI fingerprints)

**Circular import prevention:**
```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.config import AppConfig
```

**JSON parsing** in `persistence.py` has graceful fallback: tries direct parse → fenced code block extraction → regex extraction.
