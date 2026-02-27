"""Emotion Risk Control Agent for assessing emotional arc and reader engagement."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.agents.base_agent import BaseAgent
from src.models.data_models import ChapterOutline, RiskIssue, RiskReport

if TYPE_CHECKING:
    from src.config import AgentsConfig
    from src.models.llm_client import LLMClient


class EmotionRiskControlAgent(BaseAgent):
    """Agent for assessing emotional arc and reader engagement.

    Evaluates tension levels, villain IQ, protagonist difficulty, and emotional
    arc match to identify risks and determine if chapter rewrites are needed.
    """

    def __init__(
        self,
        config: AgentsConfig,
        llm_client: LLMClient,
        thresholds: dict | None = None,
    ) -> None:
        """Initialize the EmotionRiskControl agent.

        Args:
            config: Configuration for agents.
            llm_client: The LLM client for making API calls.
            thresholds: Optional threshold values for risk assessment.
                Keys: tension_threshold, villain_iq_threshold,
                      protagonist_difficulty_threshold, arc_match_threshold
        """
        super().__init__(
            name="emotion_risk_control",
            config=config,
            llm_client=llm_client,
            system_prompt_path="config/prompts/emotion_risk_control.txt",
        )

        # Store configurable thresholds with defaults
        self.thresholds = {
            "tension_threshold": 4.0,
            "villain_iq_threshold": 5.0,
            "protagonist_difficulty_threshold": 4.0,
            "arc_match_threshold": 6.0,
        }
        if thresholds:
            self.thresholds.update(thresholds)

        # Get model from config
        self.model = config.emotion_risk_control.model

    async def assess(
        self,
        chapter_content: str,
        chapter_outline: ChapterOutline,
        previous_chapters: list[str] | None = None,
    ) -> RiskReport:
        """Assess emotional risks in a chapter.

        Performs a comprehensive assessment of tension, villain IQ, protagonist
        difficulty, and emotional arc match against the planned outline.

        Args:
            chapter_content: The full content of the chapter.
            chapter_outline: The chapter outline with emotional arc information.
            previous_chapters: Optional list of previous chapter contents for context.

        Returns:
            RiskReport with scores, issues, and rewrite recommendation.
        """
        # Build context with chapter content, outline, and previous chapters
        context_parts = [
            "=== CHAPTER CONTENT ===",
            chapter_content,
            "",
            "=== CHAPTER OUTLINE ===",
            f"Chapter ID: {chapter_outline.chapter_id}",
            f"Title: {chapter_outline.title}",
            f"Summary: {chapter_outline.summary}",
            "",
            "=== EMOTIONAL ARC ===",
            f"Start: {chapter_outline.emotional_arc.start}",
            f"Peak: {chapter_outline.emotional_arc.peak}",
            f"End: {chapter_outline.emotional_arc.end}",
            f"Description: {chapter_outline.emotional_arc.description}",
        ]

        # Add previous chapters context if provided
        if previous_chapters:
            context_parts.extend([
                "",
                "=== PREVIOUS CHAPTERS (for context) ===",
            ])
            for i, prev_content in enumerate(previous_chapters, 1):
                context_parts.extend([
                    f"--- Previous Chapter {i} ---",
                    prev_content[:2000] if len(prev_content) > 2000 else prev_content,
                    "",
                ])

        context = "\n".join(context_parts)

        # Build messages
        messages = self._build_messages([
            ("system", self.system_prompt or ""),
            ("user", context),
        ])

        # Call LLM with system prompt + context
        response = await self._call_llm(
            messages=messages,
            model=self.model,
            max_tokens=4096,
            temperature=0.3,
            response_format="json",
            agent_id="emotion_risk_control",
        )

        # Parse JSON response into RiskReport
        parsed_data = response.parsed_content if hasattr(response, "parsed_content") else {}

        if not parsed_data and hasattr(response, "content"):
            try:
                parsed_data = json.loads(response.content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {e}")
                parsed_data = {}

        # Extract scores
        tension_score = parsed_data.get("tension_score", 5.0)
        villain_iq = parsed_data.get("villain_iq", 5.0)
        protagonist_difficulty = parsed_data.get("protagonist_difficulty", 5.0)
        arc_match = parsed_data.get("arc_match", 5.0)

        # Parse issues
        issues_data = parsed_data.get("issues", [])
        issues = []
        for issue_data in issues_data:
            issues.append(RiskIssue(
                category=issue_data.get("category", ""),
                description=issue_data.get("description", ""),
                suggestion=issue_data.get("suggestion", ""),
            ))

        # Determine rewrite_required based on thresholds
        rewrite_required = False
        reasons = []

        if tension_score < self.thresholds["tension_threshold"]:
            rewrite_required = True
            reasons.append(f"tension_score ({tension_score}) < threshold ({self.thresholds['tension_threshold']})")

        if villain_iq < self.thresholds["villain_iq_threshold"]:
            rewrite_required = True
            reasons.append(f"villain_iq ({villain_iq}) < threshold ({self.thresholds['villain_iq_threshold']})")

        if protagonist_difficulty < self.thresholds["protagonist_difficulty_threshold"]:
            rewrite_required = True
            reasons.append(f"protagonist_difficulty ({protagonist_difficulty}) < threshold ({self.thresholds['protagonist_difficulty_threshold']})")

        if arc_match < self.thresholds["arc_match_threshold"]:
            rewrite_required = True
            reasons.append(f"arc_match ({arc_match}) < threshold ({self.thresholds['arc_match_threshold']})")

        # Get suggestions from LLM or generate defaults
        suggestions = parsed_data.get("suggestions", [])
        if not suggestions and reasons:
            suggestions.append(f"Review required due to: {', '.join(reasons)}")

        # Create and return RiskReport
        return RiskReport(
            chapter_id=chapter_outline.chapter_id,
            tension_score=tension_score,
            villain_iq=villain_iq,
            protagonist_difficulty=protagonist_difficulty,
            arc_match=arc_match,
            issues=issues,
            rewrite_required=rewrite_required,
            suggestions=suggestions,
        )

    async def quick_check(self, chapter_content: str) -> dict:
        """Perform a lightweight risk check.

        Returns just the core scores without detailed analysis or issue tracking.

        Args:
            chapter_content: The content of the chapter to check.

        Returns:
            Dictionary with tension_score, villain_iq, protagonist_difficulty,
            arc_match, and overall_status.
        """
        # Build lightweight prompt
        prompt = f"""Perform a quick emotional risk assessment of this chapter.

Return ONLY a JSON object with these numeric scores (0-10 scale):
- tension_score: How engaging/ tense the chapter is
- villain_iq: How smart and threatening the antagonist appears
- protagonist_difficulty: How challenging the protagonist's situation is
- arc_match: How well the emotional arc flows

Chapter content:
{chapter_content[:5000]}

JSON response format:
{{{{
    "tension_score": 7.5,
    "villain_iq": 6.0,
    "protagonist_difficulty": 8.0,
    "arc_match": 7.5
}}}}
"""

        messages = self._build_messages([
            ("system", "You are a literary analyst. Respond only with valid JSON."),
            ("user", prompt),
        ])

        response = await self._call_llm(
            messages=messages,
            model=self.model,
            max_tokens=1024,
            temperature=0.2,
            response_format="json",
            agent_id="emotion_risk_control_quick",
        )

        # Parse response
        parsed_data = response.parsed_content if hasattr(response, "parsed_content") else {}

        if not parsed_data and hasattr(response, "content"):
            try:
                parsed_data = json.loads(response.content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse quick check response: {e}")
                parsed_data = {}

        # Extract scores with defaults
        scores = {
            "tension_score": parsed_data.get("tension_score", 5.0),
            "villain_iq": parsed_data.get("villain_iq", 5.0),
            "protagonist_difficulty": parsed_data.get("protagonist_difficulty", 5.0),
            "arc_match": parsed_data.get("arc_match", 5.0),
        }

        # Determine overall status based on thresholds
        low_scores = 0
        if scores["tension_score"] < self.thresholds["tension_threshold"]:
            low_scores += 1
        if scores["villain_iq"] < self.thresholds["villain_iq_threshold"]:
            low_scores += 1
        if scores["protagonist_difficulty"] < self.thresholds["protagonist_difficulty_threshold"]:
            low_scores += 1
        if scores["arc_match"] < self.thresholds["arc_match_threshold"]:
            low_scores += 1

        if low_scores == 0:
            scores["overall_status"] = "good"
        elif low_scores <= 2:
            scores["overall_status"] = "needs_improvement"
        else:
            scores["overall_status"] = "critical"

        return scores
