from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models.data_models import Outline, Volume, WorldSetting

if TYPE_CHECKING:
    from src.config import AgentsConfig
    from src.models.llm_client import LLMClient


class PlotDesignerAgent(BaseAgent):
    """Agent for designing novel plot outlines based on world settings."""

    def __init__(self, config: AgentsConfig, llm_client: LLMClient) -> None:
        """Initialize the plot designer agent.

        Args:
            config: Configuration for agents.
            llm_client: The LLM client for making API calls.
        """
        super().__init__(
            name="plot_designer",
            config=config,
            llm_client=llm_client,
            system_prompt_path="config/prompts/plot_designer.txt",
        )

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Generate a novel outline from world settings.

        Args:
            input_data: Input containing WorldSetting JSON in context.

        Returns:
            AgentOutput with success status and outline data.
        """
        try:
            # Build messages with system prompt and user context
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": input_data.context})
            if input_data.instruction:
                messages.append({"role": "user", "content": input_data.instruction})

            # Get agent-specific config
            agent_config = self.config.plot_designer

            # Call LLM
            response = await self._call_llm(
                messages=messages,
                model=agent_config.model,
                max_tokens=agent_config.max_tokens,
                response_format="json",
                agent_id=self.name,
            )

            # Parse response as JSON - handle markdown code fences
            content = response.content if hasattr(response, "content") else str(response)
            content_stripped = content.strip()
            if content_stripped.startswith("```json"):
                content_stripped = content_stripped[7:]
            elif content_stripped.startswith("```"):
                content_stripped = content_stripped[3:]
            if content_stripped.endswith("```"):
                content_stripped = content_stripped[:-3]
            content_stripped = content_stripped.strip()

            try:
                parsed_data = json.loads(content_stripped)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {e}")
                return AgentOutput(
                    agent_name=self.name,
                    success=False,
                    content=content,
                    error=f"JSON parse error: {e}",
                )

            # Validate against Outline model
            try:
                outline = Outline(**parsed_data)
            except Exception as e:
                self.logger.error(f"Failed to validate outline: {e}")
                return AgentOutput(
                    agent_name=self.name,
                    success=False,
                    content=content,
                    error=f"Validation error: {e}",
                )

            # Get token usage and cost
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
                content=json.dumps(outline.model_dump(), ensure_ascii=False, indent=2),
                metadata={"outline": outline.model_dump()},
                token_usage=token_usage,
                cost=cost,
            )

        except Exception as e:
            self.logger.error(f"Plot designer process failed: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                content="",
                error=str(e),
            )

    async def design_volume(
        self, volume_number: int, outline: Outline, user_request: str = ""
    ) -> AgentOutput:
        """Design detailed chapter outlines for a specific volume.

        Args:
            volume_number: The volume number to design.
            outline: The current outline containing volume information.
            user_request: Optional user request for specific volume design.

        Returns:
            AgentOutput with detailed Volume JSON.
        """
        try:
            # Build context with outline and volume-specific information
            context = {
                "volume_number": volume_number,
                "outline": outline.model_dump(),
                "existing_volumes": [v.model_dump() for v in outline.volumes],
            }

            instruction = f"Design detailed chapter outlines for Volume {volume_number}."
            if user_request:
                instruction += f"\n\nUser request: {user_request}"

            # Build messages
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append(
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)}
            )
            messages.append({"role": "user", "content": instruction})

            # Get agent-specific config
            agent_config = self.config.plot_designer

            # Call LLM
            response = await self._call_llm(
                messages=messages,
                model=agent_config.model,
                max_tokens=agent_config.max_tokens,
                response_format="json",
                agent_id=self.name,
            )

            # Parse response as JSON
            content = response.content if hasattr(response, "content") else str(response)
            try:
                parsed_data = json.loads(content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {e}")
                return AgentOutput(
                    agent_name=self.name,
                    success=False,
                    content=content,
                    error=f"JSON parse error: {e}",
                )

            # Validate against Volume model
            try:
                volume = Volume(**parsed_data)
            except Exception as e:
                self.logger.error(f"Failed to validate volume: {e}")
                return AgentOutput(
                    agent_name=self.name,
                    success=False,
                    content=content,
                    error=f"Validation error: {e}",
                )

            # Get token usage and cost
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
                content=json.dumps(volume.model_dump(), ensure_ascii=False, indent=2),
                metadata={"volume": volume.model_dump(), "volume_number": volume_number},
                token_usage=token_usage,
                cost=cost,
            )

        except Exception as e:
            self.logger.error(f"Volume design failed: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                content="",
                error=str(e),
            )

    async def refine_outline(self, current: Outline, feedback: str) -> AgentOutput:
        """Refine outline based on user feedback.

        Args:
            current: The current outline to refine.
            feedback: User feedback for refinement.

        Returns:
            AgentOutput with refined Outline JSON.
        """
        try:
            # Build context with current outline and feedback
            context = {
                "current_outline": current.model_dump(),
                "feedback": feedback,
            }

            instruction = (
                "Refine the current outline based on the provided feedback. "
                "Return the complete refined outline structure."
            )

            # Build messages
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append(
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)}
            )
            messages.append({"role": "user", "content": instruction})

            # Get agent-specific config
            agent_config = self.config.plot_designer

            # Call LLM
            response = await self._call_llm(
                messages=messages,
                model=agent_config.model,
                max_tokens=agent_config.max_tokens,
                response_format="json",
                agent_id=self.name,
            )

            # Parse response as JSON
            content = response.content if hasattr(response, "content") else str(response)
            try:
                parsed_data = json.loads(content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {e}")
                return AgentOutput(
                    agent_name=self.name,
                    success=False,
                    content=content,
                    error=f"JSON parse error: {e}",
                )

            # Validate against Outline model
            try:
                refined_outline = Outline(**parsed_data)
            except Exception as e:
                self.logger.error(f"Failed to validate refined outline: {e}")
                return AgentOutput(
                    agent_name=self.name,
                    success=False,
                    content=content,
                    error=f"Validation error: {e}",
                )

            # Get token usage and cost
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
                content=json.dumps(refined_outline.model_dump(), ensure_ascii=False, indent=2),
                metadata={
                    "original_outline": current.model_dump(),
                    "refined_outline": refined_outline.model_dump(),
                    "feedback": feedback,
                },
                token_usage=token_usage,
                cost=cost,
            )

        except Exception as e:
            self.logger.error(f"Outline refinement failed: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                content="",
                error=str(e),
            )
