import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


async def async_input(prompt: str = "") -> str:
    """Wrap input() to avoid blocking the event loop."""
    return await asyncio.to_thread(input, prompt)


async def async_prompt(
    prompt: str,
    choices: list[str] | None = None,
    default: str | None = None,
) -> str:
    """Wrap rich.prompt.Prompt.ask to avoid blocking the event loop."""
    return await asyncio.to_thread(
        Prompt.ask, prompt, choices=choices, default=default
    )


async def async_confirm(prompt: str, default: bool = True) -> bool:
    """Wrap rich.prompt.Confirm.ask to avoid blocking the event loop."""
    return await asyncio.to_thread(Confirm.ask, prompt, default=default)


def print_panel(title: str, content: str, style: str = "blue") -> None:
    """Print content in a rich Panel."""
    panel = Panel(content, title=title, border_style=style)
    console.print(panel)


def print_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    """Print data in a rich Table."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*row)
    console.print(table)
