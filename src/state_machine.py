from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from statemachine import State, StateMachine


class NovelStateMachine(StateMachine):
    idle = State("idle", initial=True)
    init = State("init")
    world_building = State("world_building")
    world_review = State("world_review")
    outline_design = State("outline_design")
    outline_review = State("outline_review")
    chapter_writing = State("chapter_writing")
    debate = State("debate")
    consistency_check = State("consistency_check")
    style_polish = State("style_polish")
    emotion_risk = State("emotion_risk")
    chapter_review = State("chapter_review")
    memory_update = State("memory_update")
    completed = State("completed", final=True)

    start = idle.to(init)
    begin_world = init.to(world_building)
    world_built = world_building.to(world_review)
    world_confirmed = world_review.to(outline_design)
    world_edit = world_review.to(world_building)

    outline_built = outline_design.to(outline_review)
    outline_confirmed = outline_review.to(chapter_writing)
    outline_edit = outline_review.to(outline_design)

    needs_debate = chapter_writing.to(debate)
    debate_done = debate.to(chapter_writing)
    draft_done = chapter_writing.to(consistency_check)

    consistency_pass = consistency_check.to(style_polish)
    consistency_fail = consistency_check.to(chapter_writing)

    polish_done = style_polish.to(emotion_risk)
    risk_pass = emotion_risk.to(chapter_review)
    risk_fail = emotion_risk.to(chapter_review)

    chapter_confirm = chapter_review.to(memory_update)
    chapter_revise = chapter_review.to(chapter_writing)

    memory_updated = memory_update.to(chapter_writing)
    workflow_complete = memory_update.to(completed)

    def __init__(self, state_path: str | Path | None = None, **kwargs: Any) -> None:
        self._state_path = self._resolve_state_path(state_path)
        super().__init__(**kwargs)

    async def on_enter_state(self, state: State) -> None:
        await asyncio.to_thread(self._persist_state, state)

    def _resolve_state_path(self, state_path: str | Path | None) -> Path:
        if state_path is not None:
            return Path(state_path)
        return Path(__file__).resolve().parent.parent / "sm_state.json"

    def _persist_state(self, state: State) -> None:
        payload = {
            "state": state.id,
        }
        self._state_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )


async def create_state_machine(
    state_path: str | Path | None = None,
    **kwargs: Any,
) -> NovelStateMachine:
    sm = NovelStateMachine(state_path=state_path, **kwargs)
    await sm.activate_initial_state()
    return sm
