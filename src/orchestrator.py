from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import Any

from src.agents.base_agent import AgentInput, AgentOutput
from src.agents.consistency_checker import ConsistencyCheckerAgent
from src.agents.emotion_risk_control import EmotionRiskControlAgent
from src.agents.plot_designer import PlotDesignerAgent
from src.agents.sandbox_debater import SandboxDebaterAgent
from src.agents.style_polisher import StylePolisherAgent
from src.agents.world_builder import WorldBuilderAgent
from src.agents.writer import WriterAgent
from src.config import AppConfig, get_config
from src.context_assembler import ContextAssembler
from src.memory.memory_manager import MemoryManager
from src.models.data_models import ChapterOutline, DebateConfig, DebateResult
from src.models.llm_client import LLMClient
from src.review import ReviewManager
from src.state_machine import NovelStateMachine
from src.utils.logger import get_logger
from src.utils.persistence import NovelStorage


class _ConsistencyCheckerAdapter(ConsistencyCheckerAgent):
    async def process(self, input_data: AgentInput) -> AgentOutput:
        _ = input_data
        return AgentOutput(
            agent_name=self.name,
            success=False,
            content="",
            error="ConsistencyCheckerAgent does not support process(); use check_chapter().",
        )


class _EmotionRiskControlAdapter(EmotionRiskControlAgent):
    async def process(self, input_data: AgentInput) -> AgentOutput:
        _ = input_data
        return AgentOutput(
            agent_name=self.name,
            success=False,
            content="",
            error="EmotionRiskControlAgent does not support process(); use assess().",
        )


class Orchestrator:
    def __init__(
        self,
        novel_id: str,
        config: AppConfig | None = None,
        storage: NovelStorage | None = None,
        rag_retriever: Any | None = None,
        review_manager: ReviewManager | None = None,
        state_path: str | Path | None = None,
    ) -> None:
        self.config = config or get_config()
        self.novel_id = novel_id
        self.logger = get_logger("orchestrator", self.config.project.log_level)
        self.storage = storage or NovelStorage(self.config.project.data_dir)
        self.llm_client = LLMClient(self.config)

        self.world_builder = WorldBuilderAgent(self.config.agents, self.llm_client)
        self.plot_designer = PlotDesignerAgent(self.config.agents, self.llm_client)
        self.writer = WriterAgent(self.config.agents, self.llm_client)
        self.consistency_checker = _ConsistencyCheckerAdapter(
            self.config.agents, self.llm_client
        )
        self.style_polisher = StylePolisherAgent(self.config.agents, self.llm_client)
        self.emotion_risk_control = _EmotionRiskControlAdapter(
            self.config.agents, self.llm_client
        )
        self.sandbox_debater = SandboxDebaterAgent(self.config.agents, self.llm_client)

        self.memory_manager = MemoryManager(
            novel_id=novel_id,
            storage=self.storage,
            llm_client=self.llm_client,
            rag_retriever=rag_retriever,
            summarizer_model=self.config.agents.summarizer.model,
        )
        self.context_assembler = ContextAssembler(
            storage=self.storage,
            rag_retriever=rag_retriever,
        )
        self.state_machine = NovelStateMachine(state_path=state_path)
        self.review_manager = review_manager or ReviewManager()

        defaults = self.config.workflow.write_range_defaults or {}
        try:
            self.stage_timeout_seconds = int(defaults.get("stage_timeout_seconds", 60))
        except Exception:
            self.stage_timeout_seconds = 60

    async def _run_stage(self, stage: str, awaitable: Any) -> Any:
        self.logger.info("Stage start: %s", stage)
        try:
            result = await asyncio.wait_for(
                awaitable, timeout=self.stage_timeout_seconds
            )
            self.logger.info("Stage done: %s", stage)
            return result
        except TimeoutError as exc:
            self.logger.error(
                "Stage timeout: %s (>%ss)", stage, self.stage_timeout_seconds
            )
            raise RuntimeError(
                f"Stage '{stage}' timed out after {self.stage_timeout_seconds}s"
            ) from exc

    async def start(self, user_input: str) -> None:
        _ = user_input
        self.storage.init_novel_dir(self.novel_id)
        await self.state_machine.activate_initial_state()
        self._safe_transition("start")

    async def write_chapter(self, chapter_outline: ChapterOutline) -> dict[str, Any]:
        self._safe_transition("outline_confirmed")

        debate_result = None
        if chapter_outline.requires_debate and chapter_outline.debate_config:
            self._safe_transition("needs_debate")
            debate_result = await self._run_stage(
                "debate", self._run_debate(chapter_outline.debate_config)
            )
            self._safe_transition("debate_done")

        writer_context = await self._assemble_writer_context(
            chapter_outline, debate_result
        )
        writer_input = AgentInput(
            task_type="write_chapter",
            context=writer_context,
            instruction="Write the chapter content in Markdown format.",
        )
        writer_output = await self._run_stage(
            "writer", self.writer.process(writer_input)
        )
        if not writer_output.success:
            raise RuntimeError(writer_output.error or "Writer agent failed")

        chapter_content = writer_output.content
        metadata = dict(writer_output.metadata or {})

        self._safe_transition("draft_done")
        consistency_context = self._build_consistency_context(chapter_outline)
        consistency_report = None
        for _ in range(2):
            consistency_report = await self._run_stage(
                f"consistency_check_{_ + 1}",
                self.consistency_checker.check_with_retry(
                    chapter_content,
                    chapter_outline,
                    consistency_context,
                    max_retries=1,
                ),
            )
            if consistency_report.passed or not consistency_report.issues:
                break

            revision_output = await self._run_stage(
                f"revise_for_consistency_{_ + 1}",
                self.writer.revise_for_consistency(
                    chapter_content,
                    consistency_report.issues,
                ),
            )
            if not revision_output.success:
                break
            chapter_content = revision_output.content
            metadata.update(revision_output.metadata or {})

        if consistency_report and consistency_report.passed:
            self._safe_transition("consistency_pass")
        else:
            self._safe_transition("consistency_fail")

        polish_output = await self._run_stage(
            "style_polish", self.style_polisher.polish(chapter_content)
        )
        if polish_output.success:
            chapter_content = polish_output.content
            metadata.update(polish_output.metadata or {})
        self._safe_transition("polish_done")

        risk_report = await self._run_stage(
            "emotion_risk",
            self.emotion_risk_control.assess(
                chapter_content,
                chapter_outline,
            ),
        )
        if risk_report.rewrite_required:
            self._safe_transition("risk_fail")
        else:
            self._safe_transition("risk_pass")

        if self.config.workflow.auto_mode:
            review_action, review_feedback = "pass", None
        else:
            review_action, review_feedback = await self.review_manager.review_chapter(
                chapter_content,
                risk_report=json.dumps(
                    risk_report.model_dump(), indent=2, ensure_ascii=True
                ),
            )
        if review_action == "quit":
            raise RuntimeError("Review aborted by user")

        if review_action in {"modify", "rewrite"}:
            revision_output = await self._run_stage(
                "review_revision",
                self.writer.revise(
                    chapter_content,
                    review_feedback or "",
                    chapter_outline,
                ),
            )
            if revision_output.success:
                chapter_content = revision_output.content
                metadata.update(revision_output.metadata or {})

        if review_action == "pass":
            self._safe_transition("chapter_confirm")
        else:
            self._safe_transition("chapter_revise")

        await self._run_stage(
            "memory_update",
            self.memory_manager.update_after_chapter(
                chapter_content,
                chapter_outline,
            ),
        )
        self._safe_transition("memory_updated")

        self.storage.save_chapter(
            self.novel_id,
            chapter_outline.chapter_id,
            chapter_content,
            metadata,
        )

        return {
            "content": chapter_content,
            "metadata": metadata,
            "consistency_report": consistency_report,
            "risk_report": risk_report,
            "debate_result": debate_result,
            "review_action": review_action,
        }

    async def write_range(
        self,
        chapter_outlines: list[ChapterOutline],
        overwrite: bool = False,
    ) -> dict[str, Any]:
        generated: list[dict[str, Any]] = []
        skipped: list[str] = []
        failed: list[dict[str, str]] = []

        for outline in chapter_outlines:
            self.logger.info("Chapter start: %s %s", outline.chapter_id, outline.title)
            existing_content, _ = self.storage.load_chapter(
                self.novel_id, outline.chapter_id
            )
            if existing_content is not None and not overwrite:
                skipped.append(outline.chapter_id)
                self.logger.info("Chapter skipped (exists): %s", outline.chapter_id)
                continue

            try:
                result = await self.write_chapter(outline)
                generated.append(
                    {
                        "chapter_id": outline.chapter_id,
                        "chapter_number": outline.chapter_number,
                        "title": outline.title,
                        "review_action": result.get("review_action", "pass"),
                    }
                )
                self.logger.info("Chapter done: %s", outline.chapter_id)
            except Exception as exc:
                failed.append({"chapter_id": outline.chapter_id, "error": str(exc)})
                self.logger.error("Chapter failed: %s (%s)", outline.chapter_id, exc)

        return {
            "generated": generated,
            "skipped": skipped,
            "failed": failed,
            "summary": {
                "generated_count": len(generated),
                "skipped_count": len(skipped),
                "failed_count": len(failed),
            },
        }

    async def _assemble_writer_context(
        self,
        chapter_outline: ChapterOutline,
        debate_result: DebateResult | None,
    ) -> str:
        messages = await self.context_assembler.assemble_writer(
            self.novel_id, chapter_outline
        )
        context_parts = [
            f"{message['role']}: {message['content']}" for message in messages
        ]

        if debate_result is not None:
            debate_summary = self._format_debate_result(debate_result)
            context_parts.append(f"debate_result: {debate_summary}")

        return "\n\n".join(context_parts)

    def _build_consistency_context(
        self, chapter_outline: ChapterOutline
    ) -> dict[str, Any]:
        context = self.memory_manager.get_writer_context(chapter_outline)
        world_setting = self.storage.load_world_setting(self.novel_id) or {}
        context["world_setting"] = world_setting
        return context

    async def _run_debate(self, debate_config: DebateConfig) -> DebateResult:
        participants = debate_config.participants or []
        npcs = [
            {
                "id": name.lower().replace(" ", "_"),
                "name": name,
                "stance": debate_config.stances.get(name, ""),
                "personality": "",
            }
            for name in participants
        ]
        context = debate_config.topic
        return await self.sandbox_debater.run_debate(
            topic=debate_config.topic,
            npcs=npcs,
            context=context,
            max_rounds=debate_config.max_rounds,
        )

    def _format_debate_result(self, debate_result: DebateResult) -> str:
        transcript = "\n".join(
            f"Round {speech.round} - {speech.speaker_name}: {speech.content}"
            for speech in debate_result.transcript
        )
        return "\n".join(
            [
                f"Topic: {debate_result.topic}",
                f"Rounds: {debate_result.rounds}",
                f"Outcome: {debate_result.outcome}",
                "Transcript:",
                transcript,
            ]
        )

    def _safe_transition(self, transition: str) -> None:
        transition_fn = getattr(self.state_machine, transition, None)
        if transition_fn is None:
            return
        try:
            result = transition_fn()
            if asyncio.iscoroutine(result):
                task = asyncio.create_task(result)
                task.add_done_callback(lambda t: t.exception())
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.debug("State transition %s skipped: %s", transition, exc)
