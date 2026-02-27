from __future__ import annotations

from typing import Any

from src.memory.short_term import ShortTermMemory
from src.memory.long_term import LongTermMemory
from src.memory.summarizer import Summarizer
from src.utils.persistence import NovelStorage
from src.models.llm_client import LLMClient
from src.models.data_models import ChapterOutline


class MemoryManager:
    """Central coordinator for all memory operations.

    Orchestrates short-term memory (recent context), long-term memory (persistent
    characters, timeline), and summarization to provide cohesive memory management
    for the novel generation system.
    """

    def __init__(
        self,
        novel_id: str,
        storage: NovelStorage,
        llm_client: LLMClient,
        rag_retriever: Any | None = None,
        summarizer_model: str = "kimi",
    ) -> None:
        """Initialize the memory manager with all memory subsystems.

        Args:
            novel_id: Unique identifier for the novel.
            storage: Persistence layer for saving/loading data.
            llm_client: LLM client for summarization operations.
            rag_retriever: Optional RAG retriever for indexing content.
        """
        self.novel_id = novel_id
        self.storage = storage
        self.llm_client = llm_client
        self.rag_retriever = rag_retriever

        # Initialize memory subsystems
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory(novel_id)
        self.summarizer = Summarizer(llm_client, model=summarizer_model)

    async def update_after_chapter(
        self, chapter_content: str, chapter_outline: ChapterOutline
    ) -> None:
        """Update all memory systems after a chapter is written.

        This method:
        1. Summarizes the chapter content
        2. Updates character information in long-term memory
        3. Updates timeline events in long-term memory
        4. Adds summary to short-term memory
        5. Saves summary file via storage
        6. Optionally indexes to RAG if retriever provided

        Args:
            chapter_content: The full text content of the chapter.
            chapter_outline: The outline for this chapter.
        """
        chapter_id = chapter_outline.chapter_id

        # 1. Summarize chapter
        summary = await self.summarizer.summarize(chapter_content, chapter_outline)

        # Ensure chapter_id is set on the summary
        summary.chapter_id = chapter_id

        # 2. Update characters in LTM from character_changes
        for change in summary.character_changes:
            if isinstance(change, dict):
                char_id = change.get("character_id") or change.get("name", "").lower().replace(" ", "_")
                if char_id:
                    existing = self.long_term.get_character(char_id) or {}
                    # Merge changes into existing character data
                    updated = {**existing, **change}
                    self.long_term.update_character(char_id, updated)

        # Also update characters from involved_characters in outline
        for char_name in chapter_outline.involved_characters:
            char_id = char_name.lower().replace(" ", "_")
            existing = self.long_term.get_character(char_id)
            if existing is None:
                # Create new character entry
                self.long_term.update_character(
                    char_id,
                    {
                        "character_id": char_id,
                        "name": char_name,
                        "first_appearance": chapter_id,
                    },
                )

        # 3. Update timeline in LTM from timeline_events
        for event in summary.timeline_events:
            if isinstance(event, dict):
                year = event.get("year") or event.get("time", "")
                if isinstance(year, str):
                    # Try to extract year from string
                    import re

                    match = re.search(r"(\d{3,4})", year)
                    if match:
                        year = int(match.group(1))
                    else:
                        continue
                if isinstance(year, int):
                    event_desc = event.get("event", "") or event.get("description", "")
                    if event_desc:
                        self.long_term.mark_timeline(year, event_desc, chapter_id)

        # 4. Add summary to STM
        self.short_term.add_summary(summary)

        # 5. Save summary file via storage
        summary_dict = summary.model_dump()
        self.storage.save_summary(self.novel_id, chapter_id, summary_dict)

        # 6. Optional: index to RAG if rag_retriever provided
        if self.rag_retriever is not None:
            try:
                await self.rag_retriever.index_chapter(
                    novel_id=self.novel_id,
                    chapter_id=chapter_id,
                    content=chapter_content,
                    summary=summary,
                )
            except Exception:
                # RAG indexing is optional, don't fail if it errors
                pass

    def get_writer_context(self, chapter_outline: ChapterOutline) -> dict:
        """Assemble context dictionary for the writer agent.

        Gathers relevant context from all memory systems to help the writer
        generate consistent and coherent chapter content.

        Args:
            chapter_outline: The outline for the chapter being written.

        Returns:
            Dictionary containing recent summaries, character statuses,
            timeline events, and previous chapter ending.
        """
        context: dict[str, Any] = {
            "recent_summaries": [],
            "character_statuses": {},
            "timeline_events": [],
            "previous_ending": "",
        }

        # Get recent summaries from STM
        recent = self.short_term.get_recent_summaries()
        context["recent_summaries"] = [s.model_dump() for s in recent]

        # Get character statuses from LTM for involved characters
        for char_name in chapter_outline.involved_characters:
            char_id = char_name.lower().replace(" ", "_")
            char_data = self.long_term.get_character(char_id)
            if char_data:
                context["character_statuses"][char_name] = char_data

        # Get timeline events from LTM
        timeline = self.long_term.get_timeline()
        context["timeline_events"] = timeline

        # Get previous chapter ending
        context["previous_ending"] = self.short_term.get_last_chapter_ending()

        return context

    async def get_character_context(self, character_id: str) -> str:
        """Get formatted character context string from long-term memory.

        Args:
            character_id: The unique identifier for the character.

        Returns:
            Formatted string with character information, or empty string
            if character not found.
        """
        char_data = self.long_term.get_character(character_id)
        if char_data is None:
            return ""

        # Format character data as a readable string
        lines = []
        name = char_data.get("name", character_id)
        lines.append(f"Character: {name}")
        lines.append("-" * 40)

        # Add key fields if present
        for key in ["identity", "personality", "background", "goals"]:
            if key in char_data and char_data[key]:
                value = char_data[key]
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                lines.append(f"{key.capitalize()}: {value}")

        # Add current status if present
        current_status = char_data.get("current_status", {})
        if current_status:
            lines.append("\nCurrent Status:")
            for key, value in current_status.items():
                if value:
                    lines.append(f"  {key}: {value}")

        # Add history if present
        history = char_data.get("history", [])
        if history:
            lines.append(f"\nRecent Events ({len(history)} total):")
            for event in history[-5:]:  # Show last 5 events
                if isinstance(event, dict):
                    event_desc = event.get("event", "")
                    chapter = event.get("chapter_id", "")
                    if event_desc:
                        lines.append(f"  - {event_desc} (in {chapter})")

        return "\n".join(lines)

    async def get_timeline_context(
        self, start_year: int | None = None, end_year: int | None = None
    ) -> str:
        """Get formatted timeline context string from long-term memory.

        Args:
            start_year: Optional start year for filtering (inclusive).
            end_year: Optional end year for filtering (inclusive).

        Returns:
            Formatted string with timeline events.
        """
        timeline = self.long_term.get_timeline()

        if not timeline:
            return "No timeline events recorded."

        # Filter by year range if specified
        filtered = timeline
        if start_year is not None:
            filtered = [e for e in filtered if e.get("year", 0) >= start_year]
        if end_year is not None:
            filtered = [e for e in filtered if e.get("year", 0) <= end_year]

        if not filtered:
            return "No timeline events in the specified range."

        # Format timeline as a readable string
        lines = ["Historical Timeline", "-" * 40]

        current_year = None
        for entry in filtered:
            year = entry.get("year", "?")
            event = entry.get("event", "")
            source = entry.get("source_chapter", "")

            # Group by year
            if year != current_year:
                lines.append(f"\nYear {year}:")
                current_year = year

            if source:
                lines.append(f"  - {event} (from {source})")
            else:
                lines.append(f"  - {event}")

        return "\n".join(lines)
