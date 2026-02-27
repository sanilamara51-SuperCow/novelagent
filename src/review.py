"""ReviewManager for human-in-the-loop review workflow."""
import asyncio
from typing import Tuple, Optional

from src.utils.async_io import async_prompt, async_confirm


class ReviewManager:
    """Manages human-in-the-loop review for novel generation pipeline."""

    DEFAULT_TIMEOUT = 300  # 5 minutes default timeout

    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout or self.DEFAULT_TIMEOUT

    async def review_world_setting(self, setting: str) -> Tuple[str, Optional[str]]:
        """
        Review world setting with human feedback.

        Args:
            setting: The world setting content to review

        Returns:
            Tuple of (action, feedback) where action is 'confirm', 'edit', or 'regenerate'
            and feedback is optional human input
        """
        print("\n" + "=" * 60)
        print("WORLD SETTING REVIEW")
        print("=" * 60)
        print(setting)
        print("=" * 60)

        try:
            # Get action choice
            prompt_text = "Action [confirm/edit/regenerate]: "
            action = await asyncio.wait_for(
                async_prompt(prompt_text),
                timeout=self.timeout
            )
            action = action.strip().lower()

            while action not in ('confirm', 'edit', 'regenerate'):
                print("Invalid choice. Please enter: confirm, edit, or regenerate")
                action = await asyncio.wait_for(
                    async_prompt(prompt_text),
                    timeout=self.timeout
                )
                action = action.strip().lower()

            # Get feedback if not confirming
            feedback = None
            if action in ('edit', 'regenerate'):
                feedback = await asyncio.wait_for(
                    async_prompt("Feedback (optional, press Enter to skip): "),
                    timeout=self.timeout
                )
                if not feedback.strip():
                    feedback = None

            return action, feedback

        except (asyncio.TimeoutError, EOFError):
            print("\n[Review timeout - defaulting to confirm]")
            return 'confirm', None

    async def review_outline(self, outline: str) -> Tuple[str, Optional[str]]:
        """
        Review story outline with human feedback.

        Args:
            outline: The outline content to review

        Returns:
            Tuple of (action, feedback) where action is 'confirm' or 'edit'
            and feedback is optional human input
        """
        print("\n" + "=" * 60)
        print("OUTLINE REVIEW")
        print("=" * 60)
        print(outline)
        print("=" * 60)

        try:
            # Get action choice
            prompt_text = "Action [confirm/edit]: "
            action = await asyncio.wait_for(
                async_prompt(prompt_text),
                timeout=self.timeout
            )
            action = action.strip().lower()

            while action not in ('confirm', 'edit'):
                print("Invalid choice. Please enter: confirm or edit")
                action = await asyncio.wait_for(
                    async_prompt(prompt_text),
                    timeout=self.timeout
                )
                action = action.strip().lower()

            # Get feedback if editing
            feedback = None
            if action == 'edit':
                feedback = await asyncio.wait_for(
                    async_prompt("Feedback (optional, press Enter to skip): "),
                    timeout=self.timeout
                )
                if not feedback.strip():
                    feedback = None

            return action, feedback

        except (asyncio.TimeoutError, EOFError):
            print("\n[Review timeout - defaulting to confirm]")
            return 'confirm', None

    async def review_chapter(
        self,
        chapter: str,
        risk_report: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Review chapter content with human feedback.

        Args:
            chapter: The chapter content to review
            risk_report: Optional risk assessment report

        Returns:
            Tuple of (action, feedback) where action is 'pass', 'modify',
            'rewrite', or 'quit' and feedback is optional human input
        """
        print("\n" + "=" * 60)
        print("CHAPTER REVIEW")
        print("=" * 60)

        if risk_report:
            print("\n[RISK REPORT]")
            print(risk_report)
            print("-" * 60)

        print(chapter)
        print("=" * 60)

        try:
            # Get action choice
            prompt_text = "Action [pass/modify/rewrite/quit]: "
            action = await asyncio.wait_for(
                async_prompt(prompt_text),
                timeout=self.timeout
            )
            action = action.strip().lower()

            while action not in ('pass', 'modify', 'rewrite', 'quit'):
                print("Invalid choice. Please enter: pass, modify, rewrite, or quit")
                action = await asyncio.wait_for(
                    async_prompt(prompt_text),
                    timeout=self.timeout
                )
                action = action.strip().lower()

            # Get feedback for non-pass actions
            feedback = None
            if action in ('modify', 'rewrite'):
                feedback = await asyncio.wait_for(
                    async_prompt("Feedback (optional, press Enter to skip): "),
                    timeout=self.timeout
                )
                if not feedback.strip():
                    feedback = None

            return action, feedback

        except (asyncio.TimeoutError, EOFError):
            print("\n[Review timeout - defaulting to pass]")
            return 'pass', None
