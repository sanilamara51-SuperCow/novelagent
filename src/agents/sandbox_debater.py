from __future__ import annotations

import asyncio

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models.data_models import DebateResult, Speech
from src.config import AgentsConfig
from src.models.llm_client import LLMClient


class SandboxDebaterAgent(BaseAgent):
    """Agent for running sandbox debate simulations between NPCs."""

    def __init__(self, config: AgentsConfig, llm_client: LLMClient) -> None:
        super().__init__(
            name="sandbox_debater",
            config=config,
            llm_client=llm_client,
            system_prompt_path="config/prompts/sandbox_debater.txt",
        )
        self.debater_config = config.sandbox_debater
        self._current_max_rounds = self.debater_config.max_rounds
        self._last_round_contents: dict[str, str] = {}
        self._debate_context = ""

    async def process(self, input_data: AgentInput) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            success=False,
            content="",
            error="SandboxDebaterAgent does not support process(); use run_debate().",
        )

    async def run_debate(
        self,
        topic: str,
        npcs: list[dict],
        context: str,
        max_rounds: int = 5,
    ) -> DebateResult:
        transcript: list[Speech] = []
        termination_reason = ""
        outcome = ""
        character_changes: list[dict] = []

        self._last_round_contents = {}
        self._debate_context = context
        self._current_max_rounds = min(max_rounds, self.debater_config.max_rounds)

        for round_num in range(1, self._current_max_rounds + 1):
            tasks = [
                self._generate_npc_speech(npc, topic, transcript, round_num)
                for npc in npcs
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            round_speeches: list[Speech] = []
            for npc, result in zip(npcs, results):
                if isinstance(result, Exception):
                    self.logger.error(f"NPC speech generation failed: {result}")
                    round_speeches.append(
                        Speech(
                            round=round_num,
                            speaker_id=str(npc.get("id", "")),
                            speaker_name=str(npc.get("name", "")),
                            content=f"[Error generating speech: {result}]",
                        )
                    )
                else:
                    round_speeches.append(result)

            transcript.extend(round_speeches)

            should_end, reason = self._check_termination(round_speeches, round_num)
            self._last_round_contents = {
                speech.speaker_id: speech.content.strip()
                for speech in round_speeches
            }

            if should_end:
                termination_reason = reason
                break

        if not termination_reason:
            termination_reason = "max_rounds"

        outcome = await self._generate_host_summary(
            topic=topic,
            context=context,
            transcript=transcript,
            termination_reason=termination_reason,
        )

        return DebateResult(
            topic=topic,
            rounds=len({speech.round for speech in transcript}),
            transcript=transcript,
            outcome=outcome,
            character_changes=character_changes,
        )

    async def _generate_npc_speech(
        self,
        npc: dict,
        topic: str,
        previous_speeches: list[Speech],
        round_num: int,
    ) -> Speech:
        npc_id = str(npc.get("id", ""))
        npc_name = str(npc.get("name", ""))
        personality = str(npc.get("personality", ""))
        stance = str(npc.get("stance", ""))

        recent_history = "\n".join(
            f"Round {speech.round} - {speech.speaker_name}: {speech.content}"
            for speech in previous_speeches[-6:]
        )
        if not recent_history:
            recent_history = "No prior speeches yet."

        prompt = (
            f"Topic: {topic}\n"
            f"Round: {round_num}\n"
            f"NPC: {npc_name} (id: {npc_id})\n"
            f"Personality: {personality}\n"
            f"Stance: {stance}\n\n"
            f"Context:\n{self._debate_context}\n\n"
            f"Recent debate history:\n{recent_history}\n\n"
            "Respond with a concise debate speech from this NPC's perspective."
        )

        messages = self._build_messages([
            ("system", self.system_prompt or "You are a debate participant."),
            ("user", prompt),
        ])

        response = await self._call_llm(
            messages=messages,
            model=self.debater_config.npc_model,
            max_tokens=500,
            temperature=0.8,
            agent_id=f"npc_{npc_id or npc_name}",
        )

        content = response.content if hasattr(response, "content") else str(response)
        return Speech(
            round=round_num,
            speaker_id=npc_id,
            speaker_name=npc_name,
            content=content,
        )

    def _check_termination(self, speeches: list[Speech], round_num: int) -> tuple[bool, str]:
        if not speeches:
            return True, "no_speeches"

        if round_num >= self._current_max_rounds:
            return True, "max_rounds"

        consensus_markers = (
            "we all agree",
            "consensus",
            "i agree",
            "agreed",
            "we agree",
            "common ground",
        )
        if all(
            any(marker in speech.content.lower() for marker in consensus_markers)
            for speech in speeches
        ):
            return True, "consensus"

        if self._last_round_contents:
            repeated = all(
                speech.content.strip() == self._last_round_contents.get(speech.speaker_id, "")
                for speech in speeches
            )
            if repeated:
                return True, "repetition"

        return False, ""

    async def _generate_host_summary(
        self,
        topic: str,
        context: str,
        transcript: list[Speech],
        termination_reason: str,
    ) -> str:
        transcript_text = "\n".join(
            f"Round {speech.round} - {speech.speaker_name}: {speech.content}"
            for speech in transcript
        )
        prompt = (
            f"Topic: {topic}\n"
            f"Termination reason: {termination_reason}\n\n"
            f"Context:\n{context}\n\n"
            f"Transcript:\n{transcript_text}\n\n"
            "Summarize the debate outcome and key points of agreement or disagreement."
        )
        messages = self._build_messages([
            ("system", "You are the debate host summarizing the discussion."),
            ("user", prompt),
        ])

        try:
            response = await self._call_llm(
                messages=messages,
                model=self.debater_config.host_model,
                max_tokens=self.debater_config.max_tokens,
                temperature=0.3,
                agent_id="debate_host",
            )
            return response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            self.logger.error(f"Host summary failed: {exc}")
            return termination_reason
