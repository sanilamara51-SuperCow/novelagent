from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import litellm
from litellm.cost_calculator import completion_cost
from litellm.router import Router
from litellm.utils import token_counter

from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.config import AppConfig


@dataclass
class UsageRecord:
    """Record of a single LLM API call usage."""

    model: str
    agent_id: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: datetime
    latency_ms: float


class UsageTracker:
    """Tracks LLM usage records and enforces budget limits."""

    def __init__(self, budget_limit: float | None = None) -> None:
        """Initialize the usage tracker.

        Args:
            budget_limit: Optional maximum budget in USD.
        """
        self._records: list[UsageRecord] = []
        self._budget_limit = budget_limit

    def track(self, record: UsageRecord) -> None:
        """Track a usage record and check budget.

        Args:
            record: The usage record to track.
        """
        self._records.append(record)

        if self._budget_limit is not None and self.is_over_budget():
            # Budget exceeded warning could be logged here
            pass

    def is_over_budget(self) -> bool:
        """Check if total cost exceeds budget limit.

        Returns:
            True if over budget, False otherwise.
        """
        if self._budget_limit is None:
            return False
        return self.get_total_cost() > self._budget_limit

    def get_total_cost(self) -> float:
        """Get total cost of all tracked usage.

        Returns:
            Total cost in USD.
        """
        return sum(record.cost for record in self._records)

    def get_report(self) -> dict[str, Any]:
        """Generate a usage report.

        Returns:
            Dictionary with per-model and per-agent cost breakdown,
            total cost, and total tokens.
        """
        total_cost = self.get_total_cost()
        total_input_tokens = sum(record.input_tokens for record in self._records)
        total_output_tokens = sum(record.output_tokens for record in self._records)

        # Per-model breakdown
        model_costs: dict[str, float] = {}
        model_tokens: dict[str, dict[str, int]] = {}
        for record in self._records:
            if record.model not in model_costs:
                model_costs[record.model] = 0.0
                model_tokens[record.model] = {"input": 0, "output": 0}
            model_costs[record.model] += record.cost
            model_tokens[record.model]["input"] += record.input_tokens
            model_tokens[record.model]["output"] += record.output_tokens

        # Per-agent breakdown
        agent_costs: dict[str, float] = {}
        agent_tokens: dict[str, dict[str, int]] = {}
        for record in self._records:
            if record.agent_id not in agent_costs:
                agent_costs[record.agent_id] = 0.0
                agent_tokens[record.agent_id] = {"input": 0, "output": 0}
            agent_costs[record.agent_id] += record.cost
            agent_tokens[record.agent_id]["input"] += record.input_tokens
            agent_tokens[record.agent_id]["output"] += record.output_tokens

        return {
            "total_cost": total_cost,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "record_count": len(self._records),
            "is_over_budget": self.is_over_budget(),
            "budget_limit": self._budget_limit,
            "by_model": {
                model: {
                    "cost": cost,
                    "input_tokens": model_tokens[model]["input"],
                    "output_tokens": model_tokens[model]["output"],
                }
                for model, cost in model_costs.items()
            },
            "by_agent": {
                agent: {
                    "cost": cost,
                    "input_tokens": agent_tokens[agent]["input"],
                    "output_tokens": agent_tokens[agent]["output"],
                }
                for agent, cost in agent_costs.items()
            },
        }


class LLMClient:
    """LiteLLM Router wrapper with cost tracking."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize the LLM client.

        Args:
            config: Application configuration containing LLM settings.
        """
        # Build model_list from config
        model_list = []
        for key, mc in config.llm.models.items():
            model_list.append({
                "model_name": key,
                "litellm_params": {
                    "model": mc.model,
                    "api_key": mc.api_key,
                    "max_tokens": mc.max_tokens,
                    "temperature": mc.temperature,
                    **({"api_base": mc.api_base} if getattr(mc, "api_base", None) else {}),
                },
            })

        # Create LiteLLM Router
        self.router = Router(
            model_list=model_list,
            routing_strategy="simple-shuffle",
            num_retries=3,
            timeout=180,
            allowed_fails=3,
            cooldown_time=60,
        )

        # Create usage tracker
        self.tracker = UsageTracker()

        # Create logger
        self.logger = get_logger("llm_client")

    async def acompletion(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int | None = None,
        temperature: float | None = None,
        stream: bool = False,
        agent_id: str = "unknown",
    ) -> Any:
        """Make an async completion call via LiteLLM Router.

        Args:
            model: Model name to use.
            messages: List of message dictionaries.
            max_tokens: Optional max tokens override.
            temperature: Optional temperature override.
            stream: Whether to stream the response.
            agent_id: Identifier for the calling agent.

        Returns:
            The completion response.

        Raises:
            litellm.exceptions.ContextWindowExceededError: If context window exceeded.
            litellm.exceptions.AuthenticationError: If authentication fails.
            Exception: For any other errors.
        """
        # Build kwargs
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature

        # Record start time
        start_time = time.time()

        try:
            # Call the router
            response = await self.router.acompletion(**kwargs)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Extract usage from response
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, "usage") and response.usage:
                prompt_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(response.usage, "completion_tokens", 0) or 0

            # Calculate cost
            cost = 0.0
            try:
                cost = completion_cost(completion_response=response)
            except Exception:
                cost = 0.0

            # Create usage record
            record = UsageRecord(
                model=model,
                agent_id=agent_id,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                cost=cost,
                timestamp=datetime.now(),
                latency_ms=latency_ms,
            )

            # Track usage
            self.tracker.track(record)

            # Log the usage
            self.logger.info(
                f"LLM call: model={model}, agent={agent_id}, "
                f"tokens={prompt_tokens}+{completion_tokens}, "
                f"cost=${cost:.6f}, latency={latency_ms:.2f}ms"
            )

            return response

        except litellm.exceptions.ContextWindowExceededError:
            self.logger.error(
                f"Context window exceeded: model={model}, agent={agent_id}"
            )
            raise
        except litellm.exceptions.AuthenticationError:
            self.logger.error(
                f"Authentication error: model={model}, agent={agent_id}"
            )
            raise
        except Exception as e:
            self.logger.error(
                f"LLM call failed: model={model}, agent={agent_id}, error={e}"
            )
            raise

    async def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        agent_id: str = "generate",
    ) -> str:
        response = await self.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
            agent_id=agent_id,
        )
        return self._extract_text(response)

    def _extract_text(self, response: Any) -> str:
        direct = getattr(response, "content", None)
        if isinstance(direct, str) and direct:
            return direct

        choices = getattr(response, "choices", None)
        if choices:
            first = choices[0]
            message = getattr(first, "message", None)
            if message is not None:
                content = getattr(message, "content", None)
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts: list[str] = []
                    for item in content:
                        if isinstance(item, dict):
                            text = item.get("text")
                            if text:
                                parts.append(text)
                    if parts:
                        return "".join(parts)

            if isinstance(first, dict):
                msg = first.get("message", {})
                if isinstance(msg, dict):
                    content = msg.get("content")
                    if isinstance(content, str):
                        return content

        return str(response)

    def estimate_tokens(self, model: str, messages: list[dict]) -> int:
        """Estimate token count for messages.

        Args:
            model: Model name.
            messages: List of message dictionaries.

        Returns:
            Estimated token count.
        """
        try:
            return token_counter(model=model, messages=messages)
        except Exception:
            # Fallback to rough character estimate (approx 4 chars per token)
            total_chars = sum(
                len(str(msg.get("content", ""))) for msg in messages
            )
            return total_chars // 4

    def get_usage_report(self) -> dict[str, Any]:
        """Get usage report from tracker.

        Returns:
            Usage report dictionary.
        """
        return self.tracker.get_report()
