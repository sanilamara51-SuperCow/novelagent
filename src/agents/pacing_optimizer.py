"""节奏优化器 Agent (通用小说写作).

职责:
- 检测并调整节奏密度 (根据写作模式：quality/volume/hybrid)
- 优化章节结尾悬念 (根据 cliffhanger_mode: soft/hard)
- 识别拖沓内容并提供删减建议
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.config import AppConfig, AgentsConfig
from src.models.llm_client import LLMClient

if TYPE_CHECKING:
    pass


class PacingOptimizerAgent(BaseAgent):
    """节奏优化器 Agent (通用，支持多种写作模式)."""

    def __init__(self, config: AgentsConfig, llm_client: LLMClient) -> None:
        """Initialize the pacing optimizer agent.

        Args:
            config: Configuration for agents.
            llm_client: The LLM client for making API calls.
        """
        super().__init__(
            name="pacing_optimizer",
            config=config,
            llm_client=llm_client,
            system_prompt_path="config/prompts/pacing_optimizer.txt",
        )
        # Use pacing_optimizer config if available
        try:
            self.optimizer_config = config.pacing_optimizer
        except AttributeError:
            self.optimizer_config = config.writer

    async def analyze(
        self,
        chapter_content: str,
        chapter_number: int,
        writing_mode: str = "quality",
    ) -> AgentOutput:
        """分析章节节奏，返回报告（不修改内容）.

        Args:
            chapter_content: The chapter content.
            chapter_number: 章节编号.
            writing_mode: 写作模式 (quality/volume/hybrid).

        Returns:
            AgentOutput with analysis metrics.
        """
        try:
            # Load mode-specific configuration
            mode_config = self._get_mode_config(writing_mode)

            analysis_context = f"""## 待分析章节

第{chapter_number}章

{chapter_content}

## 当前写作模式：{writing_mode}

### 模式要求
- 目标字数：{mode_config.get('chapter_word_min', 2000)}-{mode_config.get('chapter_word_max', 3000)} 字
- 节奏密度：{mode_config.get('pacing_target', 0.5)} 次冲突/千字
- 卡点模式：{mode_config.get('cliffhanger_mode', 'soft')}

## 分析要求

1. **节奏密度分析**: 统计冲突爆发点数量
2. **字数评估**: 当前字数是否在目标范围内
3. **卡点强度评估**: 评估章节结尾的悬念强度
4. **拖沓内容识别**: 标记可删除的内容

冲突类型包括：{', '.join(mode_config.get('conflict_types', []))}

请按照以下 JSON 格式输出:
```json
{{
    "word_count": 字数，
    "word_count_target": "{mode_config.get('chapter_word_min', 2000)}-{mode_config.get('chapter_word_max', 3000)}",
    "word_count_status": "ok/short/long",
    "conflict_count": 冲突数量，
    "conflict_per_1000": 每千字冲突次数，
    "conflict_target": {mode_config.get('pacing_target', 0.5)},
    "conflict_details": [
        {{"type": "冲突类型", "location": "段落位置", "description": "描述"}}
    ],
    "cliffhanger_score": 卡点强度评分 (1-10),
    "cliffhanger_mode_expected": "{mode_config.get('cliffhanger_mode', 'soft')}",
    "cliffhanger_analysis": "卡点分析",
    "cliffhanger_suggestions": ["改进建议 1", "建议 2", ...],
    "draggy_paragraphs": ["拖沓段落摘要 1", ...],
    "overall_assessment": "整体评价",
    "optimization_required": true/false
}}
```
"""

            messages = self._build_messages([
                ("system", self.system_prompt or "You are a novel pacing analysis expert. Analyze chapter rhythm and provide feedback."),
                ("user", analysis_context),
            ])

            response = await self._call_llm(
                messages=messages,
                model=self.optimizer_config.model,
                max_tokens=4096,
                temperature=0.7,
                agent_id="pacing_analyzer",
            )

            content = response.content if hasattr(response, "content") else str(response)
            analysis_result = self._extract_json(content)

            metadata = {
                "chapter_number": chapter_number,
                "writing_mode": writing_mode,
                "word_count": analysis_result.get("word_count", 0),
                "conflict_count": analysis_result.get("conflict_count", 0),
                "conflict_per_1000": analysis_result.get("conflict_per_1000", 0.0),
                "cliffhanger_score": analysis_result.get("cliffhanger_score", 0.0),
                "cliffhanger_suggestions": analysis_result.get("cliffhanger_suggestions", []),
                "draggy_paragraphs": analysis_result.get("draggy_paragraphs", []),
                "overall_assessment": analysis_result.get("overall_assessment", ""),
                "optimization_required": analysis_result.get("optimization_required", False),
            }

            token_usage = {}
            cost = 0.0
            if hasattr(response, "usage") and response.usage:
                token_usage = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                }
            if hasattr(response, "cost"):
                cost = response.cost

            return AgentOutput(
                agent_name=self.name,
                success=True,
                content=json.dumps(analysis_result, ensure_ascii=False, indent=2),
                metadata=metadata,
                token_usage=token_usage,
                cost=cost,
            )

        except Exception as e:
            self.logger.error(f"Pacing optimizer agent failed to analyze: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                content="",
                error=str(e),
            )

    async def optimize(
        self,
        chapter_content: str,
        chapter_number: int,
        writing_mode: str = "volume",
    ) -> AgentOutput:
        """优化章节节奏 (仅在 volume/hybrid 模式下使用).

        Args:
            chapter_content: The chapter content.
            chapter_number: 章节编号.
            writing_mode: 写作模式.

        Returns:
            AgentOutput with optimized content and metrics.
        """
        try:
            mode_config = self._get_mode_config(writing_mode)

            optimization_context = f"""## 待优化章节

第{chapter_number}章

{chapter_content}

## 写作模式：{writing_mode}

### 目标要求
- 字数：{mode_config.get('chapter_word_min', 1500)}-{mode_config.get('chapter_word_max', 2000)} 字
- 节奏密度：{mode_config.get('pacing_target', 1.0)} 次冲突/千字
- 卡点模式：{mode_config.get('cliffhanger_mode', 'hard')}

## 优化要求

1. **增强节奏密度**: 增加/强化冲突爆发点
2. **优化卡点**: 根据{mode_config.get('cliffhanger_mode', 'hard')}模式调整结尾
3. **删减拖沓**: 删除冗余描写

请按照以下 JSON 格式输出:
```json
{{
    "original_word_count": 原文字数，
    "optimized_word_count": 优化后字数，
    "conflict_count": 冲突数量，
    "conflict_per_1000": 每千字冲突次数，
    "conflict_details": ["冲突 1 描述", "冲突 2 描述", ...],
    "cliffhanger_score": 卡点强度评分 (1-10),
    "cliffhanger_type": "soft/hard",
    "trimmed_summary": "删减内容总结",
    "optimized_content": "优化后的完整章节内容",
    "optimization_summary": "优化总结"
}}
```
"""

            messages = self._build_messages([
                ("system", self.system_prompt or "You are a novel pacing optimization expert. Optimize chapter rhythm based on the target mode."),
                ("user", optimization_context),
            ])

            response = await self._call_llm(
                messages=messages,
                model=self.optimizer_config.model,
                max_tokens=self.optimizer_config.max_tokens,
                temperature=0.7,
                agent_id="pacing_optimizer",
            )

            content = response.content if hasattr(response, "content") else str(response)
            optimization_result = self._extract_json(content)

            metadata = {
                "chapter_number": chapter_number,
                "writing_mode": writing_mode,
                "original_word_count": optimization_result.get("original_word_count", 0),
                "optimized_word_count": optimization_result.get("optimized_word_count", 0),
                "conflict_count": optimization_result.get("conflict_count", 0),
                "conflict_per_1000": optimization_result.get("conflict_per_1000", 0.0),
                "cliffhanger_score": optimization_result.get("cliffhanger_score", 0.0),
                "cliffhanger_type": optimization_result.get("cliffhanger_type", "soft"),
                "optimization_summary": optimization_result.get("optimization_summary", ""),
            }

            token_usage = {}
            cost = 0.0
            if hasattr(response, "usage") and response.usage:
                token_usage = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                }
            if hasattr(response, "cost"):
                cost = response.cost

            return AgentOutput(
                agent_name=self.name,
                success=True,
                content=optimization_result.get("optimized_content", ""),
                metadata=metadata,
                token_usage=token_usage,
                cost=cost,
            )

        except Exception as e:
            self.logger.error(f"Pacing optimizer agent failed to optimize: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                content="",
                error=str(e),
            )

    def _get_mode_config(self, writing_mode: str) -> dict:
        """Get mode-specific configuration."""
        # Default configurations per mode
        defaults = {
            "quality": {
                "chapter_word_min": 2500,
                "chapter_word_max": 3500,
                "pacing_target": 0.5,
                "cliffhanger_mode": "soft",
                "conflict_types": ["智斗", "反转", "揭秘", "危机解除"],
            },
            "volume": {
                "chapter_word_min": 1500,
                "chapter_word_max": 2000,
                "pacing_target": 1.0,
                "cliffhanger_mode": "hard",
                "conflict_types": ["打脸", "反转", "金手指", "碾压", "危机解除"],
            },
            "hybrid": {
                "chapter_word_min": 2000,
                "chapter_word_max": 2800,
                "pacing_target": 0.7,
                "cliffhanger_mode": "soft",
                "conflict_types": ["打脸", "智斗", "反转", "金手指", "危机解除"],
            },
        }
        return defaults.get(writing_mode, defaults["quality"])

    def _extract_json(self, content: str) -> dict:
        """Extract JSON from response content."""
        content = content.strip()

        # Try direct parse first
        try:
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass

        # Try regex extraction
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        self.logger.warning("Failed to extract JSON from response")
        return {}

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process the input data and return output.

        Args:
            input_data: The input data for the agent to process.

        Returns:
            The output from the agent processing.
        """
        # Default to analyze mode
        chapter_content = input_data.context
        chapter_number = 1

        # Parse chapter number from instruction if present
        match = re.search(r'第 (\d+) 章', input_data.instruction)
        if match:
            chapter_number = int(match.group(1))

        return await self.analyze(chapter_content, chapter_number)
