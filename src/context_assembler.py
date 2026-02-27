from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from src.models.data_models import ChapterOutline, WorldSetting
from src.utils.logger import get_logger
from src.utils.persistence import NovelStorage


class ContextAssembler:
    def __init__(self, storage: NovelStorage, rag_retriever: Any | None = None) -> None:
        self.storage = storage
        self.rag_retriever = rag_retriever
        self.logger = get_logger("context_assembler")
        self._prompts_dir = Path(__file__).resolve().parents[1] / "config" / "prompts"

    async def assemble_world_builder(
        self, novel_id: str, user_input: str
    ) -> list[dict]:
        system_prompt = await self._load_prompt("world_builder.txt")
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

    async def assemble_plot_designer(
        self, novel_id: str, world_setting: WorldSetting
    ) -> list[dict]:
        system_prompt = await self._load_prompt("plot_designer.txt")
        world_json = world_setting.model_dump_json()
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"世界观设定:\n{world_json}"},
        ]

    async def assemble_writer(
        self, novel_id: str, chapter_outline: ChapterOutline, **kwargs: Any
    ) -> list[dict]:
        system_prompt = await self._load_prompt("writer.txt")

        world_brief = await asyncio.to_thread(self._summarize_world, novel_id)
        character_statuses = await asyncio.to_thread(
            self._get_character_statuses, novel_id, chapter_outline.involved_characters
        )
        recent_summaries = await asyncio.to_thread(
            self._get_recent_summaries, novel_id, 3
        )
        previous_ending = await asyncio.to_thread(self._get_chapter_ending, novel_id)
        rag_references = await self._build_rag_references(chapter_outline)
        debate_results = self._build_debate_placeholder(chapter_outline)

        outline_json = chapter_outline.model_dump_json()
        key_scenes = self._format_key_scenes(chapter_outline)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"世界观摘要:\n{world_brief}"},
            {"role": "user", "content": f"章节大纲:\n{outline_json}"},
            {"role": "user", "content": f"关键场景:\n{key_scenes}"},
            {"role": "user", "content": f"角色状态:\n{character_statuses}"},
            {"role": "user", "content": f"最近摘要:\n{recent_summaries}"},
            {"role": "user", "content": f"上一章结尾:\n{previous_ending}"},
            {"role": "user", "content": f"相关史料:\n{rag_references}"},
            {"role": "user", "content": f"辩论结果:\n{debate_results}"},
            {"role": "user", "content": "请根据以上信息创作本章正文。"},
        ]

    async def _load_prompt(self, filename: str) -> str:
        path = self._prompts_dir / filename
        return await asyncio.to_thread(path.read_text, "utf-8")

    async def _build_rag_references(self, chapter_outline: ChapterOutline) -> str:
        if not self.rag_retriever or not chapter_outline.historical_events:
            return "暂无检索结果。"

        entries: list[str] = []
        for event in chapter_outline.historical_events:
            result = await self._rag_search(event)
            entries.append(f"{event}: {result}")
        return "\n".join(entries) if entries else "暂无检索结果。"

    async def _rag_search(self, query: str) -> str:
        search_fn = getattr(self.rag_retriever, "search", None)
        if search_fn is None:
            search_fn = getattr(self.rag_retriever, "query", None)
        if search_fn is None:
            return "(RAG接口未实现)"

        try:
            results = await asyncio.to_thread(search_fn, query)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning("RAG search failed: %s", exc)
            return "(RAG检索失败)"

        if results is None:
            return "(无结果)"
        if isinstance(results, str):
            return results
        try:
            return json.dumps(results, ensure_ascii=False)
        except TypeError:
            return str(results)

    def _build_debate_placeholder(self, chapter_outline: ChapterOutline) -> str:
        if chapter_outline.requires_debate:
            return "(待接入辩论结果)"
        return "无辩论需求。"

    def _summarize_world(self, novel_id: str) -> str:
        world_setting = self.storage.load_world_setting(novel_id) or {}
        era = world_setting.get("era", "")
        political_system = world_setting.get("political_system", "")
        summary_parts = [part for part in [era, political_system] if part]
        return " / ".join(summary_parts) if summary_parts else "暂无世界观摘要。"

    def _get_character_statuses(self, novel_id: str, character_ids: list[str]) -> str:
        if not character_ids:
            return "暂无角色状态。"

        lines: list[str] = []
        for character_id in character_ids:
            data = self.storage.load_character(novel_id, character_id) or {}
            name = data.get("name", character_id)
            status = data.get("current_status", {})
            location = status.get("location", "")
            position = status.get("position", "")
            health = status.get("health", "")
            mood = status.get("mood", "")
            key_info = status.get("key_info", []) or []
            info_str = "、".join(key_info) if key_info else "无"
            parts = [part for part in [location, position, health, mood] if part]
            detail = " | ".join(parts) if parts else "无"
            lines.append(f"{name}({character_id}): {detail}; 关键信息: {info_str}")
        return "\n".join(lines) if lines else "暂无角色状态。"

    def _get_recent_summaries(self, novel_id: str, n: int = 3) -> str:
        summaries_dir = self.storage._novel_dir(novel_id) / "summaries"
        if not summaries_dir.exists():
            return "暂无最近摘要。"

        summary_files = sorted(summaries_dir.glob("*.json"), key=lambda p: p.stem)
        if not summary_files:
            return "暂无最近摘要。"

        selected = summary_files[-n:]
        lines: list[str] = []
        for path in selected:
            chapter_id = path.stem
            summary = self.storage.load_summary(novel_id, chapter_id) or {}
            content = json.dumps(summary, ensure_ascii=False) if summary else "(空)"
            lines.append(f"{chapter_id}: {content}")
        return "\n".join(lines) if lines else "暂无最近摘要。"

    def _get_chapter_ending(self, novel_id: str) -> str:
        chapters_dir = self.storage._novel_dir(novel_id) / "chapters"
        if not chapters_dir.exists():
            return "暂无上一章结尾。"

        chapter_files = list(chapters_dir.glob("*.md"))
        if not chapter_files:
            return "暂无上一章结尾。"

        latest = max(chapter_files, key=lambda p: p.stat().st_mtime)
        content = latest.read_text("utf-8")
        return content[-500:] if content else "暂无上一章结尾。"

    def _format_key_scenes(self, chapter_outline: ChapterOutline) -> str:
        if not chapter_outline.key_scenes:
            return "暂无关键场景。"

        lines: list[str] = []
        for scene in chapter_outline.key_scenes:
            scene_line = scene.description
            if scene.location:
                scene_line += f" | 地点: {scene.location}"
            if scene.characters:
                scene_line += f" | 角色: {', '.join(scene.characters)}"
            lines.append(scene_line)
        return "\n".join(lines)
