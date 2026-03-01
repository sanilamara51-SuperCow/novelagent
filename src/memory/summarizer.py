from __future__ import annotations
import json
from typing import Any

from src.models.llm_client import LLMClient
from src.models.data_models import ChapterSummary, ChapterOutline, WorldSetting


class Summarizer:
    """Summarizer agent for chapter content and world settings."""

    def __init__(self, llm_client: LLMClient, model: str = "kimi") -> None:
        """Initialize summarizer with LLM client.
        
        Args:
            llm_client: The LLM client for making API calls
            model: Model name to use (default: "kimi" for cheap summarization)
        """
        self.llm_client = llm_client
        self.model = model

    async def summarize(
        self, 
        chapter_content: str, 
        chapter_outline: ChapterOutline
    ) -> ChapterSummary:
        """Summarize chapter content and extract key elements.
        
        Args:
            chapter_content: The full text content of the chapter
            chapter_outline: The outline for this chapter
            
        Returns:
            ChapterSummary with extracted information
        """
        prompt = self._build_summary_prompt(chapter_content, chapter_outline)
        
        response = await self.llm_client.acompletion(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.3,
            max_tokens=2000,
        )

        return self._parse_summary_response(response.content, chapter_outline.chapter_id)

    async def summarize_world(
        self, 
        world_setting: WorldSetting, 
        max_tokens: int = 1000
    ) -> str:
        """Compress world setting to a brief summary.
        
        Args:
            world_setting: The world setting to summarize
            max_tokens: Maximum tokens for the summary
            
        Returns:
            Compressed world setting summary string
        """
        world_dict = world_setting.model_dump() if hasattr(world_setting, 'model_dump') else vars(world_setting)
        world_json = json.dumps(world_dict, ensure_ascii=False, indent=2)
        
        prompt = f"""请对以下世界观设定进行压缩总结，提炼出最核心的信息。

原始世界观设定（JSON格式）：
{world_json}

要求：
1. 保留最关键的世界规则、势力分布、历史背景
2. 删除次要细节和冗余描述
3. 总长度控制在1000个token以内
4. 使用简洁的bullet points或短段落

请输出压缩后的世界观摘要："""

        response = await self.llm_client.acompletion(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.3,
        )

        return response.content.strip()

    def _build_summary_prompt(
        self, 
        content: str, 
        outline: ChapterOutline
    ) -> str:
        """Build prompt for chapter summarization.
        
        Args:
            content: Chapter content
            outline: Chapter outline
            
        Returns:
            Formatted prompt string
        """
        outline_dict = outline.model_dump() if hasattr(outline, 'model_dump') else vars(outline)
        
        return f"""请分析以下小说章节内容，提取关键信息并以JSON格式返回。

章节大纲：
{json.dumps(outline_dict, ensure_ascii=False, indent=2)}

章节内容：
{content}

请提取以下信息并以JSON格式返回（不要包含任何其他文字，只返回JSON）：
{{
    "core_events": ["事件1", "事件2", ...],
    "character_changes": ["角色A的变化描述", "角色B的变化描述", ...],
    "key_dialogues": ["关键对话1", "关键对话2", ...],
    "turning_points": ["转折点1描述", "转折点2描述", ...],
    "cliffhangers": ["悬念1", "悬念2", ...],
    "timeline_events": [
        {{"time": "时间点描述", "event": "事件描述"}},
        ...
    ]
}}

注意：
- core_events: 本章节发生的核心事件列表
- character_changes: 角色性格、关系、状态的重要变化
- key_dialogues: 推动剧情或揭示信息的关键对话摘要
- turning_points: 情节走向发生转变的关键节点
- cliffhangers: 留给下章的悬念或伏笔
- timeline_events: 按时间顺序排列的事件（如适用）"""

    def _parse_summary_response(self, response_text: str, chapter_id: str) -> ChapterSummary:
        """Parse LLM response into ChapterSummary object.
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            Parsed ChapterSummary
        """
        # Clean up response - extract JSON if wrapped in markdown
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from text
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(text[start:end+1])
            else:
                raise ValueError(f"Could not parse summary response: {response_text}")
        
        raw_character_changes = data.get("character_changes", [])
        character_changes: list[dict[str, Any]] = []
        for item in raw_character_changes:
            if isinstance(item, dict):
                character_changes.append(item)
            elif isinstance(item, str) and item.strip():
                character_changes.append({"description": item.strip()})

        raw_timeline_events = data.get("timeline_events", [])
        timeline_events: list[dict[str, Any]] = []
        for item in raw_timeline_events:
            if isinstance(item, dict):
                timeline_events.append(item)
            elif isinstance(item, str) and item.strip():
                timeline_events.append({"event": item.strip()})

        return ChapterSummary(
            chapter_id=data.get("chapter_id") or chapter_id,
            core_events=data.get("core_events", []),
            character_changes=character_changes,
            key_dialogues=data.get("key_dialogues", []),
            turning_points=data.get("turning_points", []),
            cliffhangers=data.get("cliffhangers", []),
            timeline_events=timeline_events,
        )
