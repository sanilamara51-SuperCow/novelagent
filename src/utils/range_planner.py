from __future__ import annotations

import re
from pathlib import Path

from src.models.data_models import ChapterOutline


def list_existing_chapter_numbers(chapters_dir: Path) -> set[int]:
    if not chapters_dir.exists():
        return set()

    numbers: set[int] = set()
    for p in chapters_dir.glob("ch_*.md"):
        m = re.match(r"^ch_(\d{3})$", p.stem)
        if not m:
            continue
        numbers.add(int(m.group(1)))
    return numbers


def parse_range_expr(expr: str | None, min_num: int, max_num: int) -> tuple[int, int]:
    if not expr:
        return min_num, max_num

    m = re.match(r"^(\d+)-(\d+)?$", expr.strip())
    if not m:
        raise ValueError(f"Invalid range: {expr}. Expected like 3-5 or 3-")

    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else max_num
    if start > end:
        raise ValueError(f"Invalid range: {expr}. start > end")
    if start < min_num or end > max_num:
        raise ValueError(f"Range out of bounds: {expr}. allowed {min_num}-{max_num}")
    return start, end


def next_missing_start(all_numbers: list[int], existing: set[int]) -> int:
    for n in sorted(all_numbers):
        if n not in existing:
            return n
    return max(all_numbers) + 1 if all_numbers else 1


def plan_chapters(
    outlines: list[ChapterOutline],
    start: int,
    end: int,
    existing: set[int],
    overwrite: bool,
) -> tuple[list[ChapterOutline], list[int]]:
    selected: list[ChapterOutline] = []
    skipped: list[int] = []
    for ch in outlines:
        n = ch.chapter_number
        if n < start or n > end:
            continue
        if not overwrite and n in existing:
            skipped.append(n)
            continue
        selected.append(ch)
    return selected, skipped
