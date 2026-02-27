"""Novel CLI - Main entry point for the novel generation tool."""

import asyncio
from functools import wraps
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.utils.async_io import async_input, async_confirm, async_prompt


console = Console()


def coro(f):
    """Decorator to run async functions with asyncio.run()."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


@click.group()
def cli():
    """Novel generation CLI tool."""
    pass


@cli.command()
@coro
async def new():
    """Create a new novel project."""
    console.print(Panel("[bold blue]Create New Novel", expand=False))
    
    title = await async_prompt("Enter novel title")
    genre = await async_prompt("Enter genre", default="fantasy")
    
    with Progress(
        SpinnerColumn(spinner_name="line"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating novel project...", total=None)
        # TODO: Implement novel creation logic
        await asyncio.sleep(1)
        progress.update(task, completed=True)
    
    console.print(Panel(f"[bold green][OK] Novel '{title}' created successfully!", expand=False))


@cli.command()
@click.argument("novel_id")
@coro
async def resume(novel_id: str):
    """Resume an existing novel project."""
    console.print(Panel(f"[bold blue]Resume Novel: {novel_id}", expand=False))
    
    confirm = await async_confirm(f"Resume novel {novel_id}?", default=True)
    if not confirm:
        console.print("[yellow]Cancelled.")
        return
    
    with Progress(
        SpinnerColumn(spinner_name="line"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading novel project...", total=None)
        # TODO: Implement resume logic
        await asyncio.sleep(1)
        progress.update(task, completed=True)
    
    console.print(Panel(f"[bold green][OK] Resumed novel {novel_id}", expand=False))


@cli.command()
@coro
async def status():
    """Show status of all novel projects."""
    console.print(Panel("[bold blue]Novel Project Status", expand=False))
    
    with Progress(
        SpinnerColumn(spinner_name="line"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching status...", total=None)
        # TODO: Implement status fetch logic
        await asyncio.sleep(0.5)
        progress.update(task, completed=True)
    
    table = Table(title="Novel Projects")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Progress", style="yellow")
    
    # TODO: Fetch actual novel data
    table.add_row("1", "The Great Adventure", "Writing", "45%")
    table.add_row("2", "Mystery of Time", "Planning", "10%")
    
    console.print(table)


@cli.command()
@click.argument("novel_id")
@click.option("--format", "export_format", default="epub", type=click.Choice(["epub", "pdf", "txt"]), help="Export format")
@coro
async def export(novel_id: str, export_format: str):
    """Export a novel to specified format."""
    console.print(Panel(f"[bold blue]Export Novel: {novel_id} ({export_format.upper()})", expand=False))
    
    confirm = await async_confirm(f"Export novel {novel_id} as {export_format}?", default=True)
    if not confirm:
        console.print("[yellow]Export cancelled.")
        return
    
    with Progress(
        SpinnerColumn(spinner_name="line"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Exporting to {export_format}...", total=None)
        # TODO: Implement export logic
        await asyncio.sleep(2)
        progress.update(task, completed=True)
    
    console.print(Panel(f"[bold green][OK] Novel {novel_id} exported to {export_format.upper()}", expand=False))


def main():
    """Entry point for the novel CLI."""
    cli()


if __name__ == "__main__":
    main()
