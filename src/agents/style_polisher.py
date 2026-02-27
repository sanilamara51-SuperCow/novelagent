from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.config import AgentsConfig
from src.models.llm_client import LLMClient

if TYPE_CHECKING:
    pass


class StylePolisherAgent(BaseAgent):
    """Agent responsible for polishing chapter style, rhythm, and imagery."""

    def __init__(self, config: AgentsConfig, llm_client: LLMClient) -> None:
        """Initialize the style polisher agent.

        Args:
            config: Configuration for agents.
            llm_client: The LLM client for making API calls.
        """
        super().__init__(
            name="style_polisher",
            config=config,
            llm_client=llm_client,
            system_prompt_path="config/prompts/style_polisher.txt",
        )
        self.polisher_config = config.style_polisher

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process the input data and return output.

        This is the standard agent interface. For style polishing,
        use polish() or polish_with_context() methods instead.

        Args:
            input_data: The input data for the agent to process.

        Returns:
            The output from the agent processing.
        """
        return await self.polish(
            chapter_content=input_data.context,
            polish_instructions=input_data.instruction,
        )

    async def polish(
        self,
        chapter_content: str,
        polish_instructions: str = "",
    ) -> AgentOutput:
        """Polish chapter content for style, rhythm, and imagery.

        Args:
            chapter_content: The chapter content to polish.
            polish_instructions: Optional specific instructions for polishing.

        Returns:
            AgentOutput with polished content and metadata.
        """
        try:
            # Build context with chapter content and optional instructions
            context = chapter_content
            if polish_instructions:
                context = f"{polish_instructions}\n\n{chapter_content}"

            messages = self._build_messages([
                ("system", self.system_prompt or "You are a professional literary editor. Polish prose for style, rhythm, and imagery while preserving the original plot and character actions. Return polished content in Markdown format."),
                ("user", f"Please polish the following chapter content. Focus on improving style, rhythm, and imagery without changing the plot or character actions:\n\n{context}\n\nProvide the polished chapter in Markdown format:"),
            ])

            # Call LLM for style polishing
            response = await self._call_llm(
                messages=messages,
                model=self.polisher_config.model,
                max_tokens=self.polisher_config.max_tokens,
                temperature=0.6,
                agent_id="style_polisher",
            )

            # Extract polished content
            polished_content = response.content if hasattr(response, "content") else str(response)

            # Calculate metadata
            original_word_count = len(chapter_content.split())
            polished_word_count = len(polished_content.split())

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
                content=polished_content,
                metadata={
                    "original_word_count": original_word_count,
                    "polished_word_count": polished_word_count,
                    "word_count_delta": polished_word_count - original_word_count,
                },
                token_usage=token_usage,
                cost=cost,
            )

        except Exception as e:
            self.logger.error(f"Style polisher agent failed: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                content="",
                error=str(e),
            )

    async def polish_with_context(
        self,
        chapter_content: str,
        style_guide: str,
        previous_chapter_style: str | None = None,
    ) -> AgentOutput:
        """Polish chapter with style guide and context from previous chapter.

        Args:
            chapter_content: The chapter content to polish.
            style_guide: Style guidelines to follow during polishing.
            previous_chapter_style: Optional excerpt or summary of previous chapter's
                style for consistency.

        Returns:
            AgentOutput with polished content and metadata.
        """
        try:
            # Build comprehensive context
            context_parts = [f"Style Guide:\n{style_guide}"]

            if previous_chapter_style:
                context_parts.append(f"Previous Chapter Style Reference:\n{previous_chapter_style}")

            context_parts.append(f"Chapter Content to Polish:\n\n{chapter_content}")

            full_context = "\n\n---\n\n".join(context_parts)

            messages = self._build_messages([
                ("system", self.system_prompt or "You are a professional literary editor. Polish prose for style, rhythm, and imagery while preserving the original plot and character actions. Maintain consistency with the established style guide and previous chapters. Return polished content in Markdown format."),
                ("user", f"Please polish the following chapter content. Follow the style guide and maintain consistency with the previous chapter's style:\n\n{full_context}\n\nProvide the polished chapter in Markdown format:"),
            ])

            # Call LLM for style polishing with context
            response = await self._call_llm(
                messages=messages,
                model=self.polisher_config.model,
                max_tokens=self.polisher_config.max_tokens,
                temperature=0.6,
                agent_id="style_polisher_context",
            )

            # Extract polished content
            polished_content = response.content if hasattr(response, "content") else str(response)

            # Calculate metadata
            original_word_count = len(chapter_content.split())
            polished_word_count = len(polished_content.split())

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
                content=polished_content,
                metadata={
                    "original_word_count": original_word_count,
                    "polished_word_count": polished_word_count,
                    "word_count_delta": polished_word_count - original_word_count,
                    "has_style_guide": True,
                    "has_previous_style_context": previous_chapter_style is not None,
                },
                token_usage=token_usage,
                cost=cost,
            )

        except Exception as e:
            self.logger.error(f"Style polisher agent failed with context: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                content="",
                error=str(e),
            )
