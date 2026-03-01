#!/usr/bin/env python3
"""
Config-driven LLM Client - N-Model Registry
支持从配置动态加载任意数量的模型
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.config import AppConfig, ModelConfig


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    usage: Any | None = None
    routing: dict[str, Any] | None = None


class ModelRegistry:
    """配置驱动的模型注册表，支持N个模型."""

    def __init__(self, config: AppConfig | None = None):
        """Initialize registry from config.

        Args:
            config: Application config. If None, loads from default.
        """
        self._clients: dict[str, AsyncOpenAI] = {}
        self._model_configs: dict[str, ModelConfig] = {}

        if config is None:
            from src.config import load_config

            config = load_config()

        # Register all configured model aliases (lazy client init)
        for alias, model_cfg in config.llm.models.items():
            self._model_configs[alias] = model_cfg

    def _resolve_api_key(self, alias: str, raw_api_key: str) -> str:
        """Resolve API key from config literal or ${ENV_VAR}."""
        api_key = raw_api_key
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var, "")

        if not api_key:
            raise ValueError(
                f"Missing API key for model alias '{alias}'. Set it in env or config."
            )
        return api_key

    def get_client(self, alias: str) -> AsyncOpenAI:
        """Get client by alias."""
        if alias not in self._model_configs:
            raise ValueError(
                f"Unknown model alias: {alias}. Available: {list(self._model_configs.keys())}"
            )

        if alias in self._clients:
            return self._clients[alias]

        cfg = self._model_configs[alias]
        api_key = self._resolve_api_key(alias, cfg.api_key)
        timeout = 300.0
        if cfg.api_base:
            self._clients[alias] = AsyncOpenAI(
                api_key=api_key,
                base_url=cfg.api_base,
                timeout=timeout,
            )
        else:
            self._clients[alias] = AsyncOpenAI(api_key=api_key, timeout=timeout)

        return self._clients[alias]

    def get_config(self, alias: str) -> ModelConfig:
        """Get model config by alias."""
        if alias not in self._model_configs:
            raise ValueError(f"Unknown model alias: {alias}")
        return self._model_configs[alias]

    def list_aliases(self) -> list[str]:
        """List all available model aliases."""
        return list(self._model_configs.keys())

    def resolve_alias(self, model_or_alias: str) -> str:
        """Resolve incoming model string (alias/provider model) to configured alias."""
        if model_or_alias in self._model_configs:
            return model_or_alias

        suffix = model_or_alias.split("/")[-1]
        if suffix in self._model_configs:
            return suffix

        for alias, cfg in self._model_configs.items():
            if cfg.model == model_or_alias or cfg.model.split("/")[-1] == suffix:
                return alias

        raise ValueError(
            f"Unknown model '{model_or_alias}'. Available aliases: {list(self._model_configs.keys())}"
        )

    async def call(
        self,
        alias: str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Call a model by alias with automatic config fallback."""
        client = self.get_client(alias)
        cfg = self.get_config(alias)

        # Use config defaults if not specified
        if max_tokens is None:
            max_tokens = cfg.max_tokens
        if temperature is None:
            temperature = cfg.temperature

        response = await client.chat.completions.create(
            model=cfg.model.split("/")[-1],  # Remove provider prefix if present
            messages=cast(list[ChatCompletionMessageParam], messages),
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Extract usage
        inp = response.usage.prompt_tokens if response.usage else 0
        out = response.usage.completion_tokens if response.usage else 0

        # Estimate cost (simplified)
        cost = self._estimate_cost(cfg.model, inp, out)

        # Validate response has choices
        if not response.choices:
            return LLMResponse(
                content="",
                model=cfg.model,
                input_tokens=inp,
                output_tokens=out,
                cost=cost,
            )

        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=cfg.model,
            input_tokens=inp,
            output_tokens=out,
            cost=cost,
        )

    def _estimate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost based on model name."""
        # Simplified pricing - in production, load from config
        model_lower = model.lower()
        if "deepseek" in model_lower:
            return (input_tokens * 0.001 + output_tokens * 0.002) / 1000
        elif "doubao" in model_lower or "kimi" in model_lower:
            return (input_tokens + output_tokens) * 0.0001
        else:
            return 0.0  # Unknown model


class MultiModelClient:
    """多模型客户端 - 保留原有API兼容."""

    def __init__(self, config: AppConfig | None = None):
        """Initialize with config."""
        self._registry = ModelRegistry(config)

    async def call_deepseek(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """调用DeepSeek - 负责战略/骨架"""
        # Find alias for deepseek-chat
        for alias in self._registry.list_aliases():
            cfg = self._registry.get_config(alias)
            if "deepseek" in cfg.model.lower() and "chat" in cfg.model.lower():
                return await self._registry.call(
                    alias, messages, max_tokens, temperature
                )
        raise ValueError("No DeepSeek chat model configured")

    async def call_doubao(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.8,
    ) -> LLMResponse:
        """调用豆包 - 负责情感/细节"""
        for alias in self._registry.list_aliases():
            cfg = self._registry.get_config(alias)
            if "doubao" in cfg.model.lower():
                return await self._registry.call(
                    alias, messages, max_tokens, temperature
                )
        raise ValueError("No Doubao model configured")

    async def call_kimi(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.9,
    ) -> LLMResponse:
        """调用Kimi K2 - 负责对话/口语化"""
        for alias in self._registry.list_aliases():
            cfg = self._registry.get_config(alias)
            if "kimi" in cfg.model.lower():
                return await self._registry.call(
                    alias, messages, max_tokens, temperature
                )
        raise ValueError("No Kimi model configured")

    async def call_by_alias(
        self,
        alias: str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """通过配置别名调用任意模型."""
        return await self._registry.call(alias, messages, max_tokens, temperature)

    async def generate_chapter(
        self, chapter_num: int, title: str, context: str, characters: list[str]
    ) -> dict[str, LLMResponse]:
        """
        多模型协作生成单章

        Returns:
            {
                "skeleton": DeepSeek生成的骨架,
                "dialogues": Kimi生成的对话,
                "emotion": 豆包生成的情感描写,
                "full_text": 整合后的完整章节
            }
        """
        results = {}

        # Step 1: DeepSeek写骨架
        skeleton_prompt = f"""写第{chapter_num}章《{title}》的详细大纲：

前文概要：
{context}

要求：
1. 分5-7个场景
2. 每个场景标明：时间、地点、人物、核心冲突
3. 标注爽点位置
4. 结尾留钩子

输出格式：
场景1：...
场景2：...
..."""

        results["skeleton"] = await self.call_deepseek(
            [
                {
                    "role": "system",
                    "content": "你是精通北魏史的历史小说家，擅长设计权谋剧情。输出简洁的结构化大纲。",
                },
                {"role": "user", "content": skeleton_prompt},
            ]
        )

        # Step 2: Kimi写关键对话
        dialogue_prompt = f"""根据以下场景，写三段口语化对话：

场景：{title}
人物：{", ".join(characters)}

要求：
1. 对话要真实，有停顿、有潜台词
2. 符合人物身份（士族傲慢、武将粗鲁、主角不卑不亢）
3. 不要用破折号，用动作打断
4. 加几句废话、寒暄、口头禅

直接输出对话，不要解释。"""

        results["dialogues"] = await self.call_kimi(
            [
                {
                    "role": "system",
                    "content": "你是擅长写人物对话的作家，精通古代口语和方言。",
                },
                {"role": "user", "content": dialogue_prompt},
            ]
        )

        # Step 3: 豆包写情感描写
        emotion_prompt = f"""写一段细腻的情感/环境描写：

场景：{title}中的某个温馨或紧张时刻
要求：
1. 突出心理活动和氛围
2. 具体细节（光影、气味、触感）
3. 不要用破折号
4. 不要解释，直接写感受

800字左右。"""

        results["emotion"] = await self.call_doubao(
            [
                {
                    "role": "system",
                    "content": "你是擅长写细腻情感的女作家，文笔优美含蓄。",
                },
                {"role": "user", "content": emotion_prompt},
            ]
        )

        return results


# 兼容旧的LLMClient接口
class LLMClient:
    """兼容原版的简化Client - 支持配置驱动模型选择"""

    def __init__(self, config: AppConfig | None = None):
        if config is None:
            from src.config import load_config

            config = load_config()
        self._config = config
        self._registry = ModelRegistry(config)
        self.logger = get_logger("llm_client", self._config.project.log_level)

    def _build_chain(self, model: str, role: str | None) -> list[str]:
        alias = self._registry.resolve_alias(model)
        workflow = self._config.workflow
        chains = workflow.role_model_chains or {}
        policy = workflow.fallback_retry_policy or {}

        chain: list[str] = []
        if role and isinstance(chains, dict):
            candidates = chains.get(role, [])
            if isinstance(candidates, list):
                for item in candidates:
                    if isinstance(item, str):
                        try:
                            chain.append(self._registry.resolve_alias(item))
                        except Exception:
                            continue

        if alias not in chain:
            chain.insert(0, alias)

        fallback_aliases = policy.get("fallback_aliases", [])
        if isinstance(fallback_aliases, list):
            for item in fallback_aliases:
                if not isinstance(item, str):
                    continue
                try:
                    resolved = self._registry.resolve_alias(item)
                except Exception:
                    continue
                if resolved not in chain:
                    chain.append(resolved)
        return chain

    async def acompletion(
        self,
        messages: list[dict[str, str]],
        model: str = "deepseek-chat",  # Changed from "deepseek/deepseek-chat" to alias
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """兼容旧接口 - 支持模型别名调用"""
        role = kwargs.get("role") if isinstance(kwargs.get("role"), str) else None
        chain = self._build_chain(model, role)

        policy = self._config.workflow.fallback_retry_policy or {}
        try:
            retries = int(policy.get("max_retries", 0))
        except Exception:
            retries = 0
        try:
            delay = float(policy.get("retry_delay", 0.0))
        except Exception:
            delay = 0.0

        errors: list[str] = []
        for alias in chain:
            for attempt in range(retries + 1):
                try:
                    self.logger.info(
                        "LLM attempt role=%s alias=%s attempt=%d/%d",
                        role or "default",
                        alias,
                        attempt + 1,
                        retries + 1,
                    )
                    result = await self._registry.call(
                        alias, messages, max_tokens, temperature
                    )
                    result.routing = {
                        "role": role,
                        "chain": chain,
                        "selected_alias": alias,
                        "attempt": attempt + 1,
                    }
                    self.logger.info(
                        "LLM success role=%s alias=%s in=%s out=%s",
                        role or "default",
                        alias,
                        str(result.input_tokens),
                        str(result.output_tokens),
                    )
                    return result
                except Exception as exc:
                    self.logger.warning(
                        "LLM fail role=%s alias=%s attempt=%d/%d err=%s",
                        role or "default",
                        alias,
                        attempt + 1,
                        retries + 1,
                        str(exc),
                    )
                    errors.append(f"{alias}#{attempt + 1}: {exc}")
                    if delay > 0 and attempt < retries:
                        await asyncio.sleep(delay)

        raise RuntimeError(
            f"LLM call failed for role={role or 'default'} model={model}. Errors: {' | '.join(errors)}"
        )

    def list_models(self) -> list[str]:
        """List available model aliases."""
        return self._registry.list_aliases()


# 测试代码
if __name__ == "__main__":
    import asyncio

    async def test():
        client = LLMClient()

        print("测试配置驱动LLM Client...")
        print(f"可用模型: {client.list_models()}")

        # 测试通过别名调用
        if "deepseek-chat" in client.list_models():
            print("\n[1] 测试DeepSeek:")
            try:
                resp = await client.acompletion(
                    [{"role": "user", "content": "简述北魏末年的历史背景，100字"}],
                    model="deepseek-chat",
                )
                print(f"响应: {resp.content[:100]}...")
                print(f"Token: {resp.input_tokens} -> {resp.output_tokens}")
            except Exception as e:
                print(f"错误: {e}")

        print("\n测试完成!")

    asyncio.run(test())
