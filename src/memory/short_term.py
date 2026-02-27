from __future__ import annotations

from collections import deque

from src.models.data_models import ChapterSummary


class ShortTermMemory:
    """Rolling window short-term memory for recent chapter summaries.

    Maintains a fixed-size deque of recent chapter summaries for quick access
    to recent context without persisting to disk.
    """

    def __init__(self, window_size: int = 3, max_tokens: int = 4000) -> None:
        """Initialize short-term memory with specified window size.

        Args:
            window_size: Maximum number of chapter summaries to retain.
            max_tokens: Maximum tokens allowed in context string generation.
        """
        self.window_size = window_size
        self.max_tokens = max_tokens
        self._summaries: deque[ChapterSummary] = deque(maxlen=window_size)

    def add_summary(self, summary: ChapterSummary) -> None:
        """Add a chapter summary to the rolling window.

        Args:
            summary: The chapter summary to add.
        """
        self._summaries.append(summary)

    def get_recent_summaries(self, n: int | None = None) -> list[ChapterSummary]:
        """Retrieve recent chapter summaries.

        Args:
            n: Number of summaries to return. If None, returns all.

        Returns:
            List of chapter summaries, oldest first.
        """
        if n is None or n >= len(self._summaries):
            return list(self._summaries)
        return list(self._summaries)[-n:]

    def get_context_string(self, max_tokens: int | None = None) -> str:
        """Format summaries as a context string, truncating if needed.

        Args:
            max_tokens: Maximum tokens allowed. Uses instance default if None.

        Returns:
            Formatted string of recent chapter summaries.
        """
        max_tokens = max_tokens or self.max_tokens

        if not self._summaries:
            return ""

        parts = []
        total_tokens = 0

        for summary in self._summaries:
            summary_text = self._format_summary(summary)
            summary_tokens = self.estimate_tokens(summary_text)

            if total_tokens + summary_tokens > max_tokens and parts:
                break

            parts.append(summary_text)
            total_tokens += summary_tokens

        return "\n\n".join(parts)

    def get_last_chapter_ending(self, max_chars: int = 500) -> str:
        """Extract the ending/cliffhanger from the most recent chapter.

        Args:
            max_chars: Maximum characters to return from the ending.

        Returns:
            The ending text of the last chapter, truncated if necessary.
        """
        if not self._summaries:
            return ""

        last_summary = self._summaries[-1]
        ending = getattr(last_summary, "ending", "") or getattr(
            last_summary, "cliffhanger", ""
        )

        if not ending:
            content = getattr(last_summary, "content", "")
            ending = content[-max_chars:] if len(content) > max_chars else content

        return ending[:max_chars] if len(ending) > max_chars else ending

    def estimate_tokens(self, text: str) -> int:
        """Roughly estimate token count for text.

        Uses characters / 2 as an approximation, which works reasonably
        well for Chinese text where each character is roughly 1-2 tokens.

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        return len(text) // 2

    def clear(self) -> None:
        """Clear all stored summaries."""
        self._summaries.clear()

    def _format_summary(self, summary: ChapterSummary) -> str:
        """Format a single chapter summary as a string.

        Args:
            summary: The chapter summary to format.

        Returns:
            Formatted string representation.
        """
        chapter_num = getattr(summary, "chapter_number", "?")
        title = getattr(summary, "title", "")
        content = getattr(summary, "content", "")

        if title:
            return f"Chapter {chapter_num}: {title}\n{content}"
        return f"Chapter {chapter_num}\n{content}"
