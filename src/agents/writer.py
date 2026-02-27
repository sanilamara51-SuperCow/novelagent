from __future__ import annotations

import re
from typing import TYPE_CHECKING

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models.data_models import ChapterOutline, ConsistencyIssue
from src.config import AgentsConfig
from src.models.llm_client import LLMClient

if TYPE_CHECKING:
    pass


class WriterAgent(BaseAgent):
    """Agent responsible for generating novel chapters."""

    def __init__(self, config: AgentsConfig, llm_client: LLMClient) -> None:
        """Initialize the writer agent.

        Args:
            config: Configuration for agents.
            llm_client: The LLM client for making API calls.
        """
        super().__init__(
            name="writer",
            config=config,
            llm_client=llm_client,
            system_prompt_path="config/prompts/writer.txt",
        )
        self.writer_config = config.writer

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Generate a chapter based on the assembled context.

        Args:
            input_data: The input data containing the full assembled context
                       (10 components: world setting, characters, plot outline,
                       previous chapters, style guide, etc.)

        Returns:
            AgentOutput with chapter content and metadata.
        """
        try:
            # Build messages for LLM call
            messages = self._build_messages([
                ("system", self.system_prompt or "You are a professional novelist. Write engaging chapters in Markdown format."),
                ("user", f"Task: {input_data.task_type}\n\nContext:\n{input_data.context}\n\nInstruction:\n{input_data.instruction}"),
            ])

            # Call LLM without streaming for reliable cost tracking
            response = await self._call_llm(
                messages=messages,
                model=self.writer_config.model,
                max_tokens=self.writer_config.max_tokens,
                temperature=0.7,
                agent_id="writer",
            )

            # Extract chapter content
            chapter_content = response.content if hasattr(response, "content") else str(response)

            # Extract metadata from content
            metadata = self._extract_metadata(chapter_content)

            # Extract token usage and cost
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
                content=chapter_content,
                metadata=metadata,
                token_usage=token_usage,
                cost=cost,
            )

        except Exception as e:
            self.logger.error(f"Writer agent failed to process: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                content="",
                error=str(e),
            )

    async def revise(
        self,
        content: str,
        feedback: str,
        chapter_outline: ChapterOutline | None = None,
    ) -> AgentOutput:
        """Revise chapter based on feedback.

        Args:
            content: The original chapter content to revise.
            feedback: Specific revision instructions and feedback.
            chapter_outline: Optional chapter outline for reference.

        Returns:
            AgentOutput with revised chapter content and metadata.
        """
        try:
            # Build revision prompt
            revision_context = f"""Original Chapter Content:

{content}

Revision Instructions:
{feedback}"""

            if chapter_outline:
                revision_context += f"""

Chapter Outline Reference:
- Title: {chapter_outline.title}
- Summary: {chapter_outline.summary}
- Key Scenes: {[s.description for s in chapter_outline.key_scenes]}
- Involved Characters: {chapter_outline.involved_characters}"""

            messages = self._build_messages([
                ("system", self.system_prompt or "You are a professional novelist. Revise chapters based on feedback while maintaining the original style and intent."),
                ("user", f"Please revise the following chapter based on the provided feedback. Maintain the Markdown format and ensure the revisions address all points raised.\n\n{revision_context}\n\nProvide the complete revised chapter."),
            ])

            # Call LLM without streaming
            response = await self._call_llm(
                messages=messages,
                model=self.writer_config.model,
                max_tokens=self.writer_config.max_tokens,
                temperature=0.7,
                agent_id="writer_revise",
            )

            # Extract revised content
            revised_content = response.content if hasattr(response, "content") else str(response)

            # Extract metadata
            metadata = self._extract_metadata(revised_content)
            metadata["revision"] = True
            metadata["original_word_count"] = len(content.split())

            # Extract token usage and cost
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
                content=revised_content,
                metadata=metadata,
                token_usage=token_usage,
                cost=cost,
            )

        except Exception as e:
            self.logger.error(f"Writer agent failed to revise: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                content="",
                error=str(e),
            )

    async def revise_for_consistency(
        self,
        content: str,
        issues: list[ConsistencyIssue],
    ) -> AgentOutput:
        """Fix consistency issues identified by ConsistencyChecker.

        Args:
            content: The chapter content to fix.
            issues: List of consistency issues with suggested fixes.

        Returns:
            AgentOutput with corrected chapter content and metadata.
        """
        try:
            # Build issues description
            issues_text = "\n\n".join([
                f"Issue {i+1}:\n"
                f"- Type: {issue.issue_type}\n"
                f"- Severity: {issue.severity}\n"
                f"- Description: {issue.description}\n"
                f"- Suggested Fix: {issue.suggestion}"
                for i, issue in enumerate(issues)
            ])

            messages = self._build_messages([
                ("system", self.system_prompt or "You are a professional novelist. Fix consistency issues while preserving the narrative flow and style."),
                ("user", f"""Please revise the following chapter to fix the identified consistency issues.

Original Chapter Content:

{content}

Consistency Issues to Fix:

{issues_text}

Instructions:
1. Address each issue while maintaining the overall narrative flow
2. Make minimal changes necessary to fix the inconsistencies
3. Preserve the original writing style and tone
4. Return the complete corrected chapter in Markdown format

Provide the fully corrected chapter:"""),
            ])

            # Call LLM without streaming
            response = await self._call_llm(
                messages=messages,
                model=self.writer_config.model,
                max_tokens=self.writer_config.max_tokens,
                temperature=0.6,  # Slightly lower temperature for consistency fixes
                agent_id="writer_consistency",
            )

            # Extract corrected content
            corrected_content = response.content if hasattr(response, "content") else str(response)

            # Extract metadata
            metadata = self._extract_metadata(corrected_content)
            metadata["consistency_revision"] = True
            metadata["issues_fixed"] = len(issues)
            metadata["issue_types"] = [issue.issue_type for issue in issues]

            # Extract token usage and cost
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
                content=corrected_content,
                metadata=metadata,
                token_usage=token_usage,
                cost=cost,
            )

        except Exception as e:
            self.logger.error(f"Writer agent failed to revise for consistency: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                content="",
                error=str(e),
            )

    def _extract_metadata(self, content: str) -> dict:
        """Extract metadata from chapter content.

        Args:
            content: The chapter content in Markdown format.

        Returns:
            Dictionary with word_count, scenes, and characters.
        """
        # Calculate word count
        word_count = len(content.split())

        # Extract scene headings (assuming scenes are marked with ## or ### headers)
        scene_headers = re.findall(r'#{2,3}\s+(.+)', content)
        scenes = scene_headers if scene_headers else []

        # Extract character names (simple heuristic: capitalized words that appear multiple times)
        # Look for names in bold or as proper nouns
        potential_names = re.findall(r'\*\*([^*]+)\*\*|[A-Z][a-zA-Z]{1,15}(?:\s+[A-Z][a-zA-Z]{1,15})?', content)
        # Flatten and filter potential names
        characters = []
        name_counts: dict[str, int] = {}
        for match in potential_names:
            if isinstance(match, tuple):
                name = match[0] or match[1]
            else:
                name = match
            if name and len(name) > 1:
                name_counts[name] = name_counts.get(name, 0) + 1

        # Keep names that appear at least twice (likely characters)
        characters = [name for name, count in name_counts.items() if count >= 2]

        return {
            "word_count": word_count,
            "scenes": scenes,
            "characters": characters[:20],  # Limit to top 20 characters
        }
