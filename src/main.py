"""Novel CLI - Main entry point for the novel generation tool."""

from __future__ import annotations

import asyncio
from functools import wraps
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import load_config
from src.utils.outline_loader import load_outlines_for_novel
from src.utils.persistence import NovelStorage
from src.utils.range_planner import (
    list_existing_chapter_numbers,
    next_missing_start,
    parse_range_expr,
    plan_chapters,
)


console = Console()


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def _novel_dir(data_dir: str, novel_id: str) -> Path:
    return Path(data_dir) / "novels" / novel_id


def _assert_rag_ready(config) -> None:
    db_path = Path(config.rag.vector_db_path)
    if not db_path.exists() or not any(db_path.iterdir()):
        raise click.ClickException(
            "RAG index not ready. Run: python scripts/setup_kb.py --raw-dir data/knowledge_base/raw"
        )


async def _run_write(
    novel_id: str,
    range_expr: str | None,
    auto_mode: bool,
    overwrite: bool,
    strict_rag: bool,
    stage_timeout: int | None,
) -> None:
    config = load_config()
    config.workflow.auto_mode = auto_mode
    if stage_timeout is not None:
        defaults = config.workflow.write_range_defaults or {}
        defaults["stage_timeout_seconds"] = stage_timeout
        config.workflow.write_range_defaults = defaults

    if strict_rag:
        _assert_rag_ready(config)

    storage = NovelStorage(config.project.data_dir)
    novel_dir = _novel_dir(config.project.data_dir, novel_id)
    if not novel_dir.exists():
        raise click.ClickException(f"Novel not found: {novel_id}")

    outlines = load_outlines_for_novel(novel_dir)
    if not outlines:
        raise click.ClickException("No usable outline found.")

    numbers = [o.chapter_number for o in outlines]
    min_num = min(numbers)
    max_num = max(numbers)

    chapters_dir = novel_dir / "chapters"
    existing = list_existing_chapter_numbers(chapters_dir)

    effective_range = range_expr
    if not effective_range:
        defaults = config.workflow.write_range_defaults or {}
        default_range = defaults.get("default_range")
        if isinstance(default_range, str) and default_range.strip():
            effective_range = default_range

    start, end = parse_range_expr(effective_range, min_num, max_num)
    selected, skipped_by_plan = plan_chapters(outlines, start, end, existing, overwrite)

    if not selected:
        console.print(
            Panel(
                f"[yellow]No chapters to generate in range {start}-{end}."
                f"\nSkipped existing: {len(skipped_by_plan)}",
                expand=False,
            )
        )
        return

    preview = ", ".join(ch.chapter_id for ch in selected[:10])
    if len(selected) > 10:
        preview += ", ..."
    console.print(
        Panel(
            (
                f"[bold cyan]Process[/]\n"
                f"Range: {start}-{end}\n"
                f"Planned chapters: {len(selected)}\n"
                f"Preview: {preview}\n"
                f"Stage timeout: {(config.workflow.write_range_defaults or {}).get('stage_timeout_seconds', 60)}s"
            ),
            expand=False,
        )
    )

    try:
        from src.orchestrator import Orchestrator
    except ModuleNotFoundError as exc:
        raise click.ClickException(
            f"Missing dependency for orchestration: {exc}. Run: pip install -r requirements.txt"
        ) from exc

    orchestrator = Orchestrator(novel_id=novel_id, config=config, storage=storage)
    result = await orchestrator.write_range(selected, overwrite=overwrite)

    summary = result.get("summary", {})
    failed = result.get("failed", [])
    console.print(
        Panel(
            (
                f"[bold green]Write completed[/]\n"
                f"Range: {start}-{end}\n"
                f"Generated: {summary.get('generated_count', 0)}\n"
                f"Skipped(existing): {summary.get('skipped_count', 0)}\n"
                f"Failed: {summary.get('failed_count', 0)}"
            ),
            expand=False,
        )
    )

    if failed:
        table = Table(title="Write Failures")
        table.add_column("Chapter", style="cyan")
        table.add_column("Error", style="red")
        for item in failed:
            table.add_row(str(item.get("chapter_id", "")), str(item.get("error", "")))
        console.print(table)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--title", required=True, help="Novel title")
@click.option("--novel-id", default=None, help="Optional custom novel id")
@coro
async def new(title: str, novel_id: str | None):
    config = load_config()
    storage = NovelStorage(config.project.data_dir)

    resolved_id = novel_id or title.strip().lower().replace(" ", "_")
    if not resolved_id:
        raise click.ClickException("Invalid novel id")

    novel_dir = _novel_dir(config.project.data_dir, resolved_id)
    if novel_dir.exists():
        raise click.ClickException(f"Novel already exists: {resolved_id}")

    storage.init_novel_dir(resolved_id)
    storage.save_state(
        resolved_id,
        {
            "novel_id": resolved_id,
            "title": title,
            "status": "idle",
            "phase": "init",
            "current_chapter": 1,
            "completed_chapters": [],
        },
    )
    console.print(Panel(f"[bold green][OK] Created novel {resolved_id}", expand=False))


@cli.command()
@click.option("--novel-id", required=True)
@click.option("--range", "range_expr", default=None, help="e.g. 3-5 or 3-")
@click.option("--auto/--no-auto", default=True)
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--strict-rag", is_flag=True, default=False)
@click.option(
    "--stage-timeout", type=int, default=None, help="Per-stage timeout in seconds"
)
@coro
async def write(
    novel_id: str,
    range_expr: str | None,
    auto: bool,
    overwrite: bool,
    strict_rag: bool,
    stage_timeout: int | None,
):
    await _run_write(novel_id, range_expr, auto, overwrite, strict_rag, stage_timeout)


@cli.command()
@click.option("--novel-id", required=True)
@click.option("--range", "range_expr", default=None, help="Optional explicit override")
@click.option("--auto/--no-auto", default=True)
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--strict-rag", is_flag=True, default=False)
@click.option(
    "--stage-timeout", type=int, default=None, help="Per-stage timeout in seconds"
)
@coro
async def resume(
    novel_id: str,
    range_expr: str | None,
    auto: bool,
    overwrite: bool,
    strict_rag: bool,
    stage_timeout: int | None,
):
    config = load_config()
    novel_dir = _novel_dir(config.project.data_dir, novel_id)
    outlines = load_outlines_for_novel(novel_dir)
    if not outlines:
        raise click.ClickException("No usable outline found for resume")

    all_numbers = [o.chapter_number for o in outlines]
    existing = list_existing_chapter_numbers(novel_dir / "chapters")
    next_start = next_missing_start(all_numbers, existing)
    if next_start > max(all_numbers) and not range_expr:
        console.print(Panel("[yellow]All chapters already generated.", expand=False))
        return

    effective_range = range_expr or f"{next_start}-"
    await _run_write(
        novel_id,
        effective_range,
        auto,
        overwrite,
        strict_rag,
        stage_timeout,
    )


@cli.command()
@coro
async def status():
    config = load_config()
    storage = NovelStorage(config.project.data_dir)
    novels = storage.list_novels()

    table = Table(title="Novel Projects")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="magenta")
    table.add_column("Phase", style="green")
    table.add_column("Chapters", style="yellow")

    for novel_id in novels:
        state = storage.load_state(novel_id) or {}
        title = str(state.get("title", novel_id))
        phase = str(state.get("phase", state.get("status", "unknown")))
        chapter_count = len(
            list_existing_chapter_numbers(
                _novel_dir(config.project.data_dir, novel_id) / "chapters"
            )
        )
        table.add_row(novel_id, title, phase, str(chapter_count))

    if not novels:
        console.print(Panel("[yellow]No novel projects found.", expand=False))
        return

    console.print(table)


@cli.command()
@click.argument("novel_id")
@click.option(
    "--format",
    "export_format",
    default="txt",
    type=click.Choice(["epub", "pdf", "txt"]),
)
@coro
async def export(novel_id: str, export_format: str):
    config = load_config()
    novel_dir = _novel_dir(config.project.data_dir, novel_id)
    chapters_dir = novel_dir / "chapters"

    if export_format != "txt":
        raise click.ClickException(f"Format {export_format} is not implemented yet")

    chapter_files = sorted(
        [
            p
            for p in chapters_dir.glob("ch_*.md")
            if p.stem.startswith("ch_") and len(p.stem) == 6
        ],
        key=lambda p: p.stem,
    )
    if not chapter_files:
        raise click.ClickException("No chapter files found to export")

    out_dir = novel_dir / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{novel_id}.txt"

    chunks: list[str] = []
    for p in chapter_files:
        chunks.append(p.read_text(encoding="utf-8"))
    out_path.write_text("\n\n".join(chunks), encoding="utf-8")

    console.print(Panel(f"[bold green][OK] Exported: {out_path}", expand=False))


def main():
    cli()


if __name__ == "__main__":
    main()
