"""WorldBuilder agent for generating world settings."""

from __future__ import annotations
import json

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models.data_models import WorldSetting
from src.config import AgentsConfig
from src.models.llm_client import LLMClient


class WorldBuilderAgent(BaseAgent):
    """Agent responsible for generating and refining world settings."""

    def __init__(self, config: AgentsConfig, llm_client: LLMClient) -> None:
        """Initialize the WorldBuilder agent.

        Args:
            config: Configuration for all agents.
            llm_client: Client for LLM interactions.
        """
        super().__init__(
            name="world_builder",
            config=config,
            llm_client=llm_client,
            system_prompt_path="config/prompts/world_builder.txt"
        )

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Generate world setting from user input.

        Args:
            input_data: Input containing user instruction.

        Returns:
            AgentOutput with generated world setting.
        """
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": input_data.instruction})

        response = await self._call_llm(
            messages=messages,
            model=self.config.world_builder.model,
            max_tokens=self.config.world_builder.max_tokens,
            response_format="json",
            agent_id="world_builder"
        )

        token_usage = {}
        if hasattr(response, "usage") and response.usage:
            token_usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
            }
        cost = getattr(response, "cost", 0.0)

        try:
            parsed_data = json.loads(response.content)
            WorldSetting(**parsed_data)
            return AgentOutput(
                agent_name="world_builder",
                success=True,
                content=response.content,
                error="",
                metadata={"parsed": True},
                token_usage=token_usage,
                cost=cost,
            )
        except (json.JSONDecodeError, Exception) as e:
            return AgentOutput(
                agent_name="world_builder",
                success=False,
                content=response.content,
                error=str(e),
                metadata={"parsed": False},
                token_usage=token_usage,
                cost=cost,
            )

    async def refine(self, current_setting: WorldSetting, feedback: str) -> AgentOutput:
        """Refine existing world setting based on feedback.

        Args:
            current_setting: The current world setting to refine.
            feedback: User feedback for modification.

        Returns:
            AgentOutput with refined world setting.
        """
        setting_json = current_setting.model_dump_json(indent=2)
        prompt = f"请根据以下反馈修改世界观设定:\n{feedback}\n\n当前设定:\n{setting_json}"

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._call_llm(
            messages=messages,
            model=self.config.world_builder.model,
            max_tokens=self.config.world_builder.max_tokens,
            response_format="json",
            agent_id="world_builder"
        )

        token_usage = {}
        if hasattr(response, "usage") and response.usage:
            token_usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
            }
        cost = getattr(response, "cost", 0.0)

        try:
            parsed_data = json.loads(response.content)
            WorldSetting(**parsed_data)
            return AgentOutput(
                agent_name="world_builder",
                success=True,
                content=response.content,
                error="",
                metadata={"parsed": True},
                token_usage=token_usage,
                cost=cost,
            )
        except (json.JSONDecodeError, Exception) as e:
            return AgentOutput(
                agent_name="world_builder",
                success=False,
                content=response.content,
                error=str(e),
                metadata={"parsed": False},
                token_usage=token_usage,
                cost=cost,
            )
