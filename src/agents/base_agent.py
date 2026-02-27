from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from src.models.llm_client import LLMClient
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.config import AgentsConfig


class AgentInput(BaseModel):
    """Input data for an agent."""

    task_type: str
    context: str
    instruction: str

    model_config = ConfigDict(from_attributes=True)


class AgentOutput(BaseModel):
    """Output data from an agent."""

    agent_name: str
    success: bool
    content: str
    error: str = ""
    metadata: dict = {}
    token_usage: dict = {}
    cost: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        name: str,
        config: "AgentsConfig",
        llm_client: LLMClient,
        system_prompt_path: str | None = None,
    ) -> None:
        """Initialize the base agent.

        Args:
            name: The name of the agent.
            config: Configuration for agents.
            llm_client: The LLM client for making API calls.
            system_prompt_path: Optional path to a system prompt file.
        """
        self.name = name
        self.config = config
        self.llm_client = llm_client
        self.logger = get_logger(name)
        self.system_prompt: str | None = None

        if system_prompt_path:
            prompt_file = Path(system_prompt_path)
            if prompt_file.exists():
                self.system_prompt = prompt_file.read_text(encoding="utf-8")
            else:
                self.logger.warning(f"System prompt file not found: {system_prompt_path}")

    @abstractmethod
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process the input data and return output.

        Args:
            input_data: The input data for the agent to process.

        Returns:
            The output from the agent processing.
        """
        raise NotImplementedError("Subclasses must implement the process method")

    async def _call_llm(
        self,
        messages: list[dict],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        response_format: str | None = None,
        agent_id: str = "",
    ) -> Any:
        """Call the LLM with the given messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
            model: Optional model override.
            max_tokens: Optional max tokens override.
            temperature: Optional temperature override.
            response_format: Optional response format (e.g., "json").
            agent_id: Optional agent identifier for tracking.

        Returns:
            The LLM response object.
        """
        if model is None:
            raise ValueError("model is required")

        response = await self.llm_client.acompletion(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            agent_id=agent_id or self.name,
        )

        content = self._extract_content(response)
        normalized = SimpleNamespace(
            content=content,
            usage=getattr(response, "usage", None),
            cost=getattr(response, "cost", 0.0),
            raw_response=response,
            parsed_content=None,
        )

        if response_format == "json":
            try:
                normalized.parsed_content = json.loads(content)
            except json.JSONDecodeError:
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        normalized.parsed_content = json.loads(content[start:end + 1])
                    except json.JSONDecodeError:
                        self.logger.warning("Failed to parse response as JSON")
                else:
                    self.logger.warning("Failed to parse response as JSON")

        return normalized

    def _extract_content(self, response: Any) -> str:
        direct = getattr(response, "content", None)
        if isinstance(direct, str) and direct:
            return direct

        choices = getattr(response, "choices", None)
        if choices:
            first = choices[0]
            message = getattr(first, "message", None)
            if message is not None:
                msg_content = getattr(message, "content", None)
                if isinstance(msg_content, str):
                    return msg_content
                if isinstance(msg_content, list):
                    parts = []
                    for item in msg_content:
                        text = item.get("text") if isinstance(item, dict) else None
                        if text:
                            parts.append(text)
                    if parts:
                        return "".join(parts)

            if isinstance(first, dict):
                msg = first.get("message", {})
                if isinstance(msg, dict):
                    msg_content = msg.get("content")
                    if isinstance(msg_content, str):
                        return msg_content

        return str(response)

    def _build_messages(self, parts: list[tuple[str, str]]) -> list[dict]:
        """Build message list from role-content tuples.

        Args:
            parts: List of (role, content) tuples.

        Returns:
            List of message dictionaries.
        """
        return [{"role": role, "content": content} for role, content in parts]
