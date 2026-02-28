from __future__ import annotations

import json
import re
from pathlib import Path

from src.models.data_models import ChapterOutline


SOURCE_PRIORITY = [
    "outline_mega_200.json",
    "outline_expanded.json",
    "outline.json",
]


def _strip_fence(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _parse_people(raw: str) -> list[str]:
    parts = re.split(r"[、,，;；]\s*", raw)
    out = []
    for p in parts:
        v = p.strip()
        if v and len(v) <= 30:
            out.append(v)
    return out


def _outline_from_dict(data: object) -> list[ChapterOutline]:
    outlines: list[ChapterOutline] = []
    if not isinstance(data, dict):
        return outlines

    # Common shape: {"volumes": [{"chapters": [...] }]}
    volumes = data.get("volumes")
    if isinstance(volumes, list):
        for vol in volumes:
            if not isinstance(vol, dict):
                continue
            chapters = vol.get("chapters")
            if not isinstance(chapters, list):
                continue
            for ch in chapters:
                if not isinstance(ch, dict):
                    continue
                num = ch.get("chapter_number") or ch.get("章序号")
                title = ch.get("title") or ch.get("标题") or ""
                if not isinstance(num, int) or not title:
                    continue
                summary = (
                    ch.get("summary")
                    or ch.get("核心事件")
                    or ch.get("core_thrill")
                    or ""
                )
                people = ch.get("involved_characters") or ch.get("出场人物") or []
                if isinstance(people, str):
                    people = _parse_people(people)
                if not isinstance(people, list):
                    people = []

                outlines.append(
                    ChapterOutline(
                        chapter_id=f"ch_{num:03d}",
                        chapter_number=num,
                        title=str(title),
                        summary=str(summary),
                        involved_characters=[str(x) for x in people if str(x).strip()],
                    )
                )

    # Fallback shape: direct "chapters"
    chapters = data.get("chapters")
    if isinstance(chapters, list):
        for ch in chapters:
            if not isinstance(ch, dict):
                continue
            num = ch.get("chapter_number") or ch.get("章序号")
            title = ch.get("title") or ch.get("标题") or ""
            if not isinstance(num, int) or not title:
                continue
            summary = ch.get("summary") or ch.get("核心事件") or ""
            outlines.append(
                ChapterOutline(
                    chapter_id=f"ch_{num:03d}",
                    chapter_number=num,
                    title=str(title),
                    summary=str(summary),
                )
            )

    return outlines


def _outline_from_text(text: str) -> list[ChapterOutline]:
    outlines: list[ChapterOutline] = []
    pattern = re.compile(r'"章序号"\s*:\s*(\d+).*?"标题"\s*:\s*"([^"]+)"', re.S)

    for m in pattern.finditer(text):
        num = int(m.group(1))
        title = m.group(2).strip()
        window = text[m.start() : min(len(text), m.start() + 1200)]

        summary = ""
        for key in ["核心事件", "summary", "core_thrill"]:
            sm = re.search(rf'"{key}"\s*:\s*"([^"]*)"', window)
            if sm:
                summary = sm.group(1).strip()
                break

        people: list[str] = []
        pm = re.search(r'"出场人物"\s*:\s*"([^"]*)"', window)
        if pm:
            people = _parse_people(pm.group(1))

        outlines.append(
            ChapterOutline(
                chapter_id=f"ch_{num:03d}",
                chapter_number=num,
                title=title,
                summary=summary,
                involved_characters=people,
            )
        )

    return outlines


def load_outlines_for_novel(novel_dir: Path) -> list[ChapterOutline]:
    for name in SOURCE_PRIORITY:
        path = novel_dir / name
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        text = _strip_fence(raw)

        try:
            data = json.loads(text)
            outlines = _outline_from_dict(data)
            if outlines:
                return sorted(outlines, key=lambda x: x.chapter_number)
        except Exception:
            pass

        outlines = _outline_from_text(text)
        if outlines:
            return sorted(outlines, key=lambda x: x.chapter_number)

    return []
