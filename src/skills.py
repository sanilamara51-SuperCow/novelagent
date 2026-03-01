"""Skills adapter layer for Claude Code integration.

Exposes each agent as a callable async function. Claude acts as the Director —
reviewing global state, planning chapters, and invoking agents through these
skills. All skills share infrastructure (config, storage, memory, LLM client)
via a lazily-initialized ``NovelSession``.

Usage from Claude Code::

    from src.skills import session

    # Initialize a session for a novel
    await session.init("qiewei_001")

    # Check project status
    status = await session.status()

    # Build world setting
    result = await session.build_world("北魏末年穿越小说，主角...")

    # Design outline
    result = await session.design_outline()

    # Write a chapter with full pipeline
    result = await session.write_chapter(3)

    # Or call individual stages
    draft = await session.draft_chapter(3)
    report = await session.check_consistency(3)
    polished = await session.polish_chapter(3)
    risk = await session.assess_risk(3)
    await session.update_memory(3)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agents.base_agent import AgentInput
from src.agents.consistency_checker import ConsistencyCheckerAgent
from src.agents.emotion_risk_control import EmotionRiskControlAgent
from src.agents.plot_designer import PlotDesignerAgent
from src.agents.sandbox_debater import SandboxDebaterAgent
from src.agents.style_polisher import StylePolisherAgent
from src.agents.world_builder import WorldBuilderAgent
from src.agents.writer import WriterAgent
from src.config import AppConfig, load_config, get_config
from src.context_assembler import ContextAssembler
from src.knowledge.embedding_service import EmbeddingService
from src.knowledge.rag_retriever import RAGRetriever
from src.memory.memory_manager import MemoryManager
from src.models.data_models import ChapterOutline, WorldSetting
from src.models.llm_client import LLMClient
from src.utils.logger import get_logger
from src.utils.outline_loader import load_outlines_for_novel
from src.utils.persistence import NovelStorage


logger = get_logger("skills")


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class SkillResult:
    """Uniform return type for all skills."""

    success: bool
    content: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def __str__(self) -> str:
        if self.success:
            preview = self.content[:200] + "..." if len(self.content) > 200 else self.content
            return preview
        return f"[FAILED] {self.error}"


# ---------------------------------------------------------------------------
# Novel Session — shared infrastructure
# ---------------------------------------------------------------------------

class NovelSession:
    """Holds all shared state for a single novel project.

    Call ``await session.init(novel_id)`` before using any skill.
    Switching novels is supported — just call ``init`` again.
    """

    def __init__(self) -> None:
        self._novel_id: str = ""
        self._config: AppConfig | None = None
        self._storage: NovelStorage | None = None
        self._llm_client: LLMClient | None = None
        self._memory: MemoryManager | None = None
        self._context: ContextAssembler | None = None

        # agents
        self._world_builder: WorldBuilderAgent | None = None
        self._plot_designer: PlotDesignerAgent | None = None
        self._writer: WriterAgent | None = None
        self._checker: ConsistencyCheckerAgent | None = None
        self._polisher: StylePolisherAgent | None = None
        self._risk: EmotionRiskControlAgent | None = None
        self._debater: SandboxDebaterAgent | None = None

        # cached outlines
        self._outlines: list[ChapterOutline] = []

    # ── bootstrap ──────────────────────────────────────────────────────

    async def init(
        self,
        novel_id: str,
        config_path: str = "config/settings.yaml",
    ) -> SkillResult:
        """Initialize (or re-initialize) session for a novel project."""
        self._novel_id = novel_id

        # config (reuse if already loaded)
        try:
            self._config = get_config()
        except RuntimeError:
            self._config = load_config(config_path)

        self._storage = NovelStorage(self._config.project.data_dir)
        self._storage.init_novel_dir(novel_id)
        self._llm_client = LLMClient(self._config)

        agents = self._config.agents
        self._world_builder = WorldBuilderAgent(agents, self._llm_client)
        self._plot_designer = PlotDesignerAgent(agents, self._llm_client)
        self._writer = WriterAgent(agents, self._llm_client)
        self._checker = ConsistencyCheckerAgent(agents, self._llm_client)
        self._polisher = StylePolisherAgent(agents, self._llm_client)
        self._risk = EmotionRiskControlAgent(agents, self._llm_client)
        self._debater = SandboxDebaterAgent(agents, self._llm_client)

        # Initialize RAG if vector DB exists
        rag_retriever = None
        if self._config.rag.vector_db_path:
            try:
                import os
                if os.path.exists(self._config.rag.vector_db_path):
                    embedding_svc = EmbeddingService(self._config.rag)
                    rag_retriever = RAGRetriever(self._config.rag, embedding_svc)
                    logger.info("RAG initialized: %s", self._config.rag.vector_db_path)
                else:
                    logger.warning("RAG vector DB not found: %s", self._config.rag.vector_db_path)
            except Exception as e:
                logger.warning("RAG initialization failed: %s", e)

        self._memory = MemoryManager(
            novel_id=novel_id,
            storage=self._storage,
            llm_client=self._llm_client,
            rag_retriever=rag_retriever,
            summarizer_model=agents.summarizer.model,
        )
        self._context = ContextAssembler(storage=self._storage, rag_retriever=rag_retriever)

        # load outlines if they exist
        novel_dir = self._storage._novel_dir(novel_id)
        self._outlines = load_outlines_for_novel(novel_dir)

        logger.info("Session initialized for novel: %s", novel_id)
        return SkillResult(
            success=True,
            content=f"Session ready: {novel_id}, {len(self._outlines)} chapters in outline.",
        )

    def _ensure_init(self) -> None:
        if not self._novel_id:
            raise RuntimeError("Call session.init(novel_id) first.")

    # ── status ─────────────────────────────────────────────────────────

    async def status(self) -> SkillResult:
        """Return current project status: world, outline, chapters written."""
        self._ensure_init()
        assert self._storage is not None

        novel_dir = self._storage._novel_dir(self._novel_id)
        has_world = (novel_dir / "world_setting.json").exists()

        outline_count = len(self._outlines)

        chapters_dir = novel_dir / "chapters"
        written = sorted(p.stem for p in chapters_dir.glob("ch_*.md")) if chapters_dir.exists() else []

        info = {
            "novel_id": self._novel_id,
            "has_world_setting": has_world,
            "outline_chapters": outline_count,
            "chapters_written": len(written),
            "written_ids": written,
            "next_chapter": len(written) + 1,
        }

        lines = [
            f"Novel: {self._novel_id}",
            f"World setting: {'yes' if has_world else 'no'}",
            f"Outline: {outline_count} chapters",
            f"Written: {len(written)} chapters",
        ]
        if written:
            lines.append(f"Latest: {written[-1]}")
            lines.append(f"Next: ch_{len(written)+1:03d}")

        return SkillResult(success=True, content="\n".join(lines), data=info)

    # ── world building ─────────────────────────────────────────────────

    async def build_world(self, description: str) -> SkillResult:
        """Generate world setting from a free-form description."""
        self._ensure_init()
        assert self._world_builder is not None and self._storage is not None

        result = await self._world_builder.process(
            AgentInput(task_type="world_building", instruction=description)
        )

        # Accept even if success=False (may be JSON parse issue in agent)
        if not result.content:
            return SkillResult(success=False, error=result.error or "World building returned empty content.")

        # persist - handle markdown code fences
        content = result.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON with regex
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    data = {"raw": result.content}
            else:
                data = {"raw": result.content}

        self._storage.save_world_setting(self._novel_id, data)

        return SkillResult(
            success=True,
            content=result.content,
            data={"token_usage": result.token_usage, "cost": result.cost},
        )

    async def refine_world(self, feedback: str) -> SkillResult:
        """Refine the existing world setting based on feedback."""
        self._ensure_init()
        assert self._world_builder is not None and self._storage is not None

        raw = self._storage.load_world_setting(self._novel_id)
        if not raw:
            return SkillResult(success=False, error="No world setting found. Run build_world first.")

        world = WorldSetting(**raw)
        result = await self._world_builder.refine(world, feedback)

        if result.success:
            try:
                data = json.loads(result.content)
            except json.JSONDecodeError:
                data = {"raw": result.content}
            self._storage.save_world_setting(self._novel_id, data)

        return SkillResult(
            success=result.success,
            content=result.content,
            error=result.error,
        )

    # ── outline design ─────────────────────────────────────────────────

    async def design_outline(self, instruction: str = "") -> SkillResult:
        """Design full novel outline based on world setting."""
        self._ensure_init()
        assert self._plot_designer is not None and self._storage is not None

        world_raw = self._storage.load_world_setting(self._novel_id)
        if not world_raw:
            return SkillResult(success=False, error="No world setting. Run build_world first.")

        world = WorldSetting(**world_raw)
        context = world.model_dump_json(indent=2)
        prompt = instruction or "请根据世界观设定设计完整的小说大纲。"

        result = await self._plot_designer.process(
            AgentInput(
                task_type="outline_design",
                context=context,
                instruction=prompt,
            )
        )

        if result.success:
            try:
                data = json.loads(result.content)
            except json.JSONDecodeError:
                data = {"raw": result.content}
            self._storage.save_outline(self._novel_id, data)
            # reload outlines
            novel_dir = self._storage._novel_dir(self._novel_id)
            self._outlines = load_outlines_for_novel(novel_dir)

        return SkillResult(
            success=result.success,
            content=result.content,
            data={"chapters": len(self._outlines)},
            error=result.error,
        )

    # ── chapter writing (full pipeline) ────────────────────────────────

    async def write_chapter(
        self,
        chapter_number: int,
        max_consistency_retries: int = 1,
    ) -> SkillResult:
        """Write a chapter through the full quality pipeline.

        Pipeline: draft → consistency check → polish → risk assess → memory update.

        Args:
            chapter_number: 1-based chapter number.
            max_consistency_retries: Max times to rewrite on consistency failure.
        """
        self._ensure_init()

        # 1. Draft
        draft = await self.draft_chapter(chapter_number)
        if not draft.success:
            return draft

        # 2. Consistency check (with retry loop)
        for attempt in range(max_consistency_retries + 1):
            check = await self.check_consistency(chapter_number)
            if check.success and check.data.get("passed", True):
                break
            if attempt < max_consistency_retries:
                logger.info("Consistency failed, rewriting (attempt %d)...", attempt + 1)
                issues = check.data.get("issues", [])
                rewrite = await self._rewrite_for_consistency(chapter_number, issues)
                if not rewrite.success:
                    return rewrite

        # 3. Polish
        polish = await self.polish_chapter(chapter_number)
        if not polish.success:
            logger.warning("Polish failed, continuing with unpolished draft.")

        # 4. Risk assessment
        risk = await self.assess_risk(chapter_number)
        if risk.data.get("rewrite_required"):
            logger.warning("Risk control flagged rewrite: %s", risk.data.get("suggestions"))
            # Return with warning rather than auto-rewriting — let Claude (Director) decide
            pass

        # 5. Memory update
        await self.update_memory(chapter_number)

        # Load final content
        content, meta = self._storage.load_chapter(self._novel_id, f"ch_{chapter_number:03d}")

        return SkillResult(
            success=True,
            content=content or "",
            data={
                "chapter_number": chapter_number,
                "consistency": check.data if check else {},
                "risk": risk.data if risk else {},
                "word_count": len(content) if content else 0,
            },
        )

    # ── individual pipeline stages ─────────────────────────────────────

    async def draft_chapter(self, chapter_number: int) -> SkillResult:
        """Generate a chapter draft (no quality checks)."""
        self._ensure_init()
        assert self._writer is not None and self._storage is not None and self._context is not None

        outline = self._get_outline(chapter_number)
        if outline is None:
            return SkillResult(success=False, error=f"No outline found for chapter {chapter_number}.")

        # Assemble context
        messages = await self._context.assemble_writer(self._novel_id, outline)
        context_str = "\n\n".join(m["content"] for m in messages if m["role"] == "user")

        result = await self._writer.process(
            AgentInput(
                task_type="chapter_writing",
                context=context_str,
                instruction=f"请创作第{chapter_number}章：{outline.title}",
            )
        )

        if result.success:
            chapter_id = f"ch_{chapter_number:03d}"
            self._storage.save_chapter(
                self._novel_id,
                chapter_id,
                result.content,
                result.metadata or {},
            )

        return SkillResult(
            success=result.success,
            content=result.content,
            data={"token_usage": result.token_usage, "cost": result.cost},
            error=result.error,
        )

    async def check_consistency(self, chapter_number: int) -> SkillResult:
        """Run consistency check on a written chapter."""
        self._ensure_init()
        assert self._checker is not None and self._storage is not None and self._memory is not None

        chapter_id = f"ch_{chapter_number:03d}"
        content, _ = self._storage.load_chapter(self._novel_id, chapter_id)
        if not content:
            return SkillResult(success=False, error=f"Chapter {chapter_id} not found.")

        outline = self._get_outline(chapter_number)
        if outline is None:
            return SkillResult(success=False, error=f"No outline for chapter {chapter_number}.")

        ctx = self._memory.get_writer_context(outline)
        world_raw = self._storage.load_world_setting(self._novel_id)
        if world_raw:
            ctx["world_setting"] = world_raw

        report = await self._checker.check_with_retry(content, outline, ctx)

        issues_list = []
        for issue in report.issues:
            if isinstance(issue, dict):
                issues_list.append(issue)
            else:
                issues_list.append(issue.model_dump() if hasattr(issue, "model_dump") else vars(issue))

        return SkillResult(
            success=True,
            content=f"Consistency: {'PASS' if report.passed else 'FAIL'} ({len(report.issues)} issues)",
            data={"passed": report.passed, "issues": issues_list},
        )

    async def polish_chapter(
        self,
        chapter_number: int,
        instructions: str = "",
    ) -> SkillResult:
        """Polish a written chapter for style and prose quality."""
        self._ensure_init()
        assert self._polisher is not None and self._storage is not None

        chapter_id = f"ch_{chapter_number:03d}"
        content, meta = self._storage.load_chapter(self._novel_id, chapter_id)
        if not content:
            return SkillResult(success=False, error=f"Chapter {chapter_id} not found.")

        result = await self._polisher.polish(content, instructions)

        if result.success and result.content:
            self._storage.save_chapter(
                self._novel_id, chapter_id, result.content, meta or {}
            )

        return SkillResult(
            success=result.success,
            content=result.content,
            data={"token_usage": result.token_usage, "cost": result.cost},
            error=result.error,
        )

    async def assess_risk(self, chapter_number: int) -> SkillResult:
        """Run emotion/risk assessment on a chapter."""
        self._ensure_init()
        assert self._risk is not None and self._storage is not None

        chapter_id = f"ch_{chapter_number:03d}"
        content, _ = self._storage.load_chapter(self._novel_id, chapter_id)
        if not content:
            return SkillResult(success=False, error=f"Chapter {chapter_id} not found.")

        outline = self._get_outline(chapter_number)
        if outline is None:
            return SkillResult(success=False, error=f"No outline for chapter {chapter_number}.")

        report = await self._risk.assess(content, outline)

        return SkillResult(
            success=True,
            content=(
                f"Risk: tension={report.tension_score} villain_iq={report.villain_iq} "
                f"difficulty={report.protagonist_difficulty} arc={report.arc_match} "
                f"rewrite={'YES' if report.rewrite_required else 'no'}"
            ),
            data={
                "tension_score": report.tension_score,
                "villain_iq": report.villain_iq,
                "protagonist_difficulty": report.protagonist_difficulty,
                "arc_match": report.arc_match,
                "rewrite_required": report.rewrite_required,
                "suggestions": report.suggestions,
            },
        )

    async def update_memory(self, chapter_number: int) -> SkillResult:
        """Update memory systems after a chapter is finalized."""
        self._ensure_init()
        assert self._memory is not None and self._storage is not None

        chapter_id = f"ch_{chapter_number:03d}"
        content, _ = self._storage.load_chapter(self._novel_id, chapter_id)
        if not content:
            return SkillResult(success=False, error=f"Chapter {chapter_id} not found.")

        outline = self._get_outline(chapter_number)
        if outline is None:
            return SkillResult(success=False, error=f"No outline for chapter {chapter_number}.")

        await self._memory.update_after_chapter(content, outline)

        return SkillResult(success=True, content=f"Memory updated for {chapter_id}.")

    # ── debate ─────────────────────────────────────────────────────────

    async def run_debate(
        self,
        topic: str,
        npcs: list[dict[str, str]],
        context: str = "",
        max_rounds: int = 5,
    ) -> SkillResult:
        """Run a sandbox debate between NPCs.

        Args:
            topic: The debate topic / question.
            npcs: List of NPC dicts, each with at least ``name`` and ``stance``.
            context: Background context for the debate.
            max_rounds: Maximum debate rounds.
        """
        self._ensure_init()
        assert self._debater is not None

        result = await self._debater.run_debate(topic, npcs, context, max_rounds)

        transcript_text = "\n".join(
            f"[{s.speaker}] {s.content}" for s in result.transcript
        )

        return SkillResult(
            success=True,
            content=transcript_text,
            data={
                "rounds": result.rounds,
                "outcome": result.outcome,
                "character_changes": result.character_changes,
            },
        )

    # ── revision ───────────────────────────────────────────────────────

    async def revise_chapter(
        self, chapter_number: int, feedback: str
    ) -> SkillResult:
        """Revise a chapter based on free-form feedback."""
        self._ensure_init()
        assert self._writer is not None and self._storage is not None

        chapter_id = f"ch_{chapter_number:03d}"
        content, meta = self._storage.load_chapter(self._novel_id, chapter_id)
        if not content:
            return SkillResult(success=False, error=f"Chapter {chapter_id} not found.")

        outline = self._get_outline(chapter_number)
        result = await self._writer.revise(content, feedback, outline)

        if result.success and result.content:
            self._storage.save_chapter(
                self._novel_id, chapter_id, result.content, meta or {}
            )

        return SkillResult(
            success=result.success,
            content=result.content,
            error=result.error,
        )

    # ── read helpers (for Director reasoning) ──────────────────────────

    async def get_world_setting(self) -> SkillResult:
        """Load and return the current world setting."""
        self._ensure_init()
        assert self._storage is not None

        data = self._storage.load_world_setting(self._novel_id)
        if not data:
            return SkillResult(success=False, error="No world setting found.")

        return SkillResult(
            success=True,
            content=json.dumps(data, ensure_ascii=False, indent=2),
            data=data,
        )

    async def get_outline(self, chapter_number: int | None = None) -> SkillResult:
        """Get outline — full or for a specific chapter."""
        self._ensure_init()

        if chapter_number is not None:
            outline = self._get_outline(chapter_number)
            if outline is None:
                return SkillResult(success=False, error=f"No outline for chapter {chapter_number}.")
            return SkillResult(
                success=True,
                content=outline.model_dump_json(indent=2),
                data=outline.model_dump(),
            )

        if not self._outlines:
            return SkillResult(success=False, error="No outline loaded.")

        summaries = [
            f"Ch{o.chapter_number}: {o.title} — {o.summary[:80]}"
            for o in self._outlines
        ]
        return SkillResult(
            success=True,
            content="\n".join(summaries),
            data={"total": len(self._outlines)},
        )

    async def get_chapter(self, chapter_number: int) -> SkillResult:
        """Load a written chapter's content."""
        self._ensure_init()
        assert self._storage is not None

        chapter_id = f"ch_{chapter_number:03d}"
        content, meta = self._storage.load_chapter(self._novel_id, chapter_id)
        if not content:
            return SkillResult(success=False, error=f"Chapter {chapter_id} not found.")

        return SkillResult(success=True, content=content, data=meta or {})

    async def get_memory_context(self, chapter_number: int) -> SkillResult:
        """Get assembled memory context for a chapter (what Writer would see)."""
        self._ensure_init()
        assert self._memory is not None

        outline = self._get_outline(chapter_number)
        if outline is None:
            return SkillResult(success=False, error=f"No outline for chapter {chapter_number}.")

        ctx = self._memory.get_writer_context(outline)
        return SkillResult(
            success=True,
            content=json.dumps(ctx, ensure_ascii=False, indent=2, default=str),
            data=ctx,
        )

    # ── private helpers ────────────────────────────────────────────────

    def _get_outline(self, chapter_number: int) -> ChapterOutline | None:
        for o in self._outlines:
            if o.chapter_number == chapter_number:
                return o
        return None

    async def _rewrite_for_consistency(
        self, chapter_number: int, issues: list[dict]
    ) -> SkillResult:
        """Internal: rewrite chapter to fix consistency issues."""
        assert self._writer is not None and self._storage is not None

        chapter_id = f"ch_{chapter_number:03d}"
        content, meta = self._storage.load_chapter(self._novel_id, chapter_id)
        if not content:
            return SkillResult(success=False, error=f"Chapter {chapter_id} not found.")

        from src.models.data_models import ConsistencyIssue

        issue_objects = []
        for iss in issues:
            issue_objects.append(ConsistencyIssue(
                issue_type=iss.get("issue_type", "unknown"),
                severity=iss.get("severity", "warning"),
                description=iss.get("description", ""),
                suggestion=iss.get("suggestion", ""),
            ))

        result = await self._writer.revise_for_consistency(content, issue_objects)

        if result.success and result.content:
            self._storage.save_chapter(
                self._novel_id, chapter_id, result.content, meta or {}
            )

        return SkillResult(
            success=result.success,
            content=result.content,
            error=result.error,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

session = NovelSession()
