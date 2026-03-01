from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models.data_models import ConsistencyReport, ChapterOutline

if TYPE_CHECKING:
    from src.config import AgentsConfig
    from src.models.llm_client import LLMClient


class ConsistencyCheckerAgent(BaseAgent):
    """一致性检查Agent，检查章节内容的时间线、角色、地理和历史一致性。"""

    def __init__(self, config: AgentsConfig, llm_client: LLMClient) -> None:
        """初始化一致性检查Agent。

        Args:
            config: Agent配置。
            llm_client: LLM客户端。

        """
        super().__init__(
            name="consistency_checker",
            config=config,
            llm_client=llm_client,
            system_prompt_path="config/prompts/consistency_checker.txt",
        )
        self.model = config.consistency_checker.model
        self.max_tokens = config.consistency_checker.max_tokens

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process入口（不推荐，请使用check_chapter）。"""
        return AgentOutput(
            agent_name=self.name,
            success=False,
            content="",
            error="ConsistencyCheckerAgent does not support process(); use check_chapter().",
        )

    async def check_chapter(
        self,
        chapter_content: str,
        chapter_outline: ChapterOutline,
        context: dict,
    ) -> ConsistencyReport:
        """检查章节一致性。

        Args:
            chapter_content: 章节内容。
            chapter_outline: 章节大纲。
            context: 上下文信息，包含recent_summaries, character_statuses, world_setting。

        Returns:
            ConsistencyReport: 一致性检查报告。

        """
        # 构建上下文信息
        context_parts = []
        context_parts.append(f"章节ID: {chapter_outline.chapter_id}")
        context_parts.append(f"章节编号: {chapter_outline.chapter_number}")
        context_parts.append(f"章节标题: {chapter_outline.title}")

        if "recent_summaries" in context:
            context_parts.append("\n=== 近期章节摘要 ===")
            for summary in context["recent_summaries"]:
                context_parts.append(f"- {summary}")

        if "character_statuses" in context:
            context_parts.append("\n=== 角色当前状态 ===")
            for char_name, status in context["character_statuses"].items():
                context_parts.append(f"{char_name}: {status}")

        if "world_setting" in context:
            context_parts.append("\n=== 世界观设定 ===")
            world_setting = context["world_setting"]
            if isinstance(world_setting, dict):
                for key, value in world_setting.items():
                    context_parts.append(f"{key}: {value}")
            else:
                context_parts.append(str(world_setting))

        # 构建完整提示
        context_str = "\n".join(context_parts)

        force_json_hint = ""
        if context.get("force_json"):
            force_json_hint = "\n\n重要：请务必输出有效的JSON格式，不要包含任何其他文本。只返回JSON对象。"

        prompt = f"""{context_str}

=== 章节大纲 ===
{chapter_outline.model_dump_json(indent=2)}

=== 待检查章节内容 ===
{chapter_content}

请检查上述章节内容的一致性，包括时间线、角色行为、地理位置和历史事件。返回JSON格式的ConsistencyReport。{force_json_hint}"""

        # 构建消息
        messages = self._build_messages([
            ("system", self.system_prompt or "你是一个专业的一致性检查员。"),
            ("user", prompt),
        ])

        # 调用LLM
        response = await self._call_llm(
            messages=messages,
            model=self.model,
            max_tokens=self.max_tokens,
            response_format="json",
            agent_id=self.name,
        )

        # 解析JSON响应
        if hasattr(response, "parsed_content") and response.parsed_content:
            data = response.parsed_content
        else:
            try:
                data = json.loads(response.content)
            except json.JSONDecodeError:
                # 最后尝试：提取最外层 { ... }
                text = response.content
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    data = json.loads(text[start : end + 1])
                else:
                    raise

        # 构建一致性报告
        report = ConsistencyReport(
            chapter_id=chapter_outline.chapter_id,
            issues=data.get("issues", []),
            passed=data.get("passed", True),
        )

        return report

    async def check_with_retry(
        self,
        chapter_content: str,
        chapter_outline: ChapterOutline,
        context: dict,
        max_retries: int = 1,
    ) -> ConsistencyReport:
        """带重试的章节一致性检查。

        如果JSON解析失败，会重试一次，附加"输出有效JSON"的指令。

        Args:
            chapter_content: 章节内容。
            chapter_outline: 章节大纲。
            context: 上下文信息。
            max_retries: 最大重试次数，默认为1。

        Returns:
            ConsistencyReport: 一致性检查报告。

        """
        try:
            return await self.check_chapter(chapter_content, chapter_outline, context)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            if max_retries <= 0:
                self.logger.error(f"一致性检查失败，重试次数已耗尽: {e}")
                # 返回一个失败的报告
                return ConsistencyReport(
                    chapter_id=chapter_outline.chapter_id,
                    issues=[],
                    passed=False,
                )

            self.logger.warning(f"JSON解析失败，进行重试: {e}")

            # 添加强制输出JSON的指令
            context = context.copy()
            context["force_json"] = True

            # 修改提示，明确要求输出JSON
            retry_context = context.copy()
            retry_context["instruction"] = "请务必输出有效的JSON格式，不要包含任何其他文本。输出有效JSON"

            return await self.check_with_retry(
                chapter_content,
                chapter_outline,
                retry_context,
                max_retries=max_retries - 1,
            )
