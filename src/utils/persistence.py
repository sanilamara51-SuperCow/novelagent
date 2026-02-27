from __future__ import annotations

import json
import logging
from pathlib import Path

from src.utils.logger import get_logger


class NovelStorage:
    """JSON file persistence for novel data."""

    def __init__(self, data_dir: str | Path = "./data") -> None:
        self.data_dir = Path(data_dir)
        self.logger = get_logger("storage")

    def _novel_dir(self, novel_id: str) -> Path:
        """Return the directory path for a specific novel."""
        return self.data_dir / "novels" / novel_id

    def init_novel_dir(self, novel_id: str) -> Path:
        """Create subdirectories for a novel and return the novel directory."""
        novel_dir = self._novel_dir(novel_id)
        subdirs = ["characters", "outline", "chapters", "summaries"]
        for subdir in subdirs:
            (novel_dir / subdir).mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Initialized novel directory: {novel_dir}")
        return novel_dir

    def _save_json(self, path: Path, data: dict) -> None:
        """Save data as JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Saved JSON to: {path}")

    def _load_json(self, path: Path) -> dict | None:
        """Load data from JSON file. Return None if file doesn't exist."""
        if not path.exists():
            self.logger.debug(f"JSON file not found: {path}")
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.logger.debug(f"Loaded JSON from: {path}")
        return data

    def save_state(self, novel_id: str, state: dict) -> None:
        """Save novel state to novel_state.json."""
        path = self._novel_dir(novel_id) / "novel_state.json"
        self._save_json(path, state)

    def load_state(self, novel_id: str) -> dict | None:
        """Load novel state from novel_state.json."""
        path = self._novel_dir(novel_id) / "novel_state.json"
        return self._load_json(path)

    def save_world_setting(self, novel_id: str, setting: dict) -> None:
        """Save world setting to world_setting.json."""
        path = self._novel_dir(novel_id) / "world_setting.json"
        self._save_json(path, setting)

    def load_world_setting(self, novel_id: str) -> dict | None:
        """Load world setting from world_setting.json."""
        path = self._novel_dir(novel_id) / "world_setting.json"
        return self._load_json(path)

    def save_chapter(
        self, novel_id: str, chapter_id: str, content: str, metadata: dict
    ) -> None:
        """Save chapter content and metadata."""
        novel_dir = self._novel_dir(novel_id)
        # Save content as plain
        content_path = novel_dir / "chapters" / f"{chapter_id}.md"
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(content)
        self.logger.info(f"Saved chapter content to: {content_path}")
        # Save metadata as JSON
        metadata_path = novel_dir / "chapters" / f"{chapter_id}.meta.json"
        self._save_json(metadata_path, metadata)

    def load_chapter(
        self, novel_id: str, chapter_id: str
    ) -> tuple[str | None, dict | None]:
        """Load chapter content and metadata. Returns (content, metadata)."""
        novel_dir = self._novel_dir(novel_id)
        content_path = novel_dir / "chapters" / f"{chapter_id}.md"
        metadata_path = novel_dir / "chapters" / f"{chapter_id}.meta.json"

        if not content_path.exists():
            return None, None

        with open(content_path, encoding="utf-8") as f:
            content = f.read()

        metadata = self._load_json(metadata_path)
        return content, metadata

    def save_outline(self, novel_id: str, outline: dict) -> None:
        """Save outline to outline.json."""
        path = self._novel_dir(novel_id) / "outline" / "outline.json"
        self._save_json(path, outline)

    def load_outline(self, novel_id: str) -> dict | None:
        """Load outline from outline.json."""
        path = self._novel_dir(novel_id) / "outline" / "outline.json"
        return self._load_json(path)

    def save_character(self, novel_id: str, character_id: str, character: dict) -> None:
        """Save character data to characters/{character_id}.json."""
        path = self._novel_dir(novel_id) / "characters" / f"{character_id}.json"
        self._save_json(path, character)

    def load_character(self, novel_id: str, character_id: str) -> dict | None:
        """Load character data from characters/{character_id}.json."""
        path = self._novel_dir(novel_id) / "characters" / f"{character_id}.json"
        return self._load_json(path)

    def list_characters(self, novel_id: str) -> list[str]:
        """List all character IDs in the characters directory."""
        characters_dir = self._novel_dir(novel_id) / "characters"
        if not characters_dir.exists():
            return []
        character_ids = []
        for f in characters_dir.iterdir():
            if f.suffix == ".json" and f.stem != ".gitkeep":
                character_ids.append(f.stem)
        return sorted(character_ids)

    def save_summary(self, novel_id: str, chapter_id: str, summary: dict) -> None:
        """Save summary to summaries/{chapter_id}.json."""
        path = self._novel_dir(novel_id) / "summaries" / f"{chapter_id}.json"
        self._save_json(path, summary)

    def load_summary(self, novel_id: str, chapter_id: str) -> dict | None:
        """Load summary from summaries/{chapter_id}.json."""
        path = self._novel_dir(novel_id) / "summaries" / f"{chapter_id}.json"
        return self._load_json(path)

    def list_novels(self) -> list[str]:
        """List all novel IDs from the novels directory."""
        novels_dir = self.data_dir / "novels"
        if not novels_dir.exists():
            return []
        novel_ids = []
        for d in novels_dir.iterdir():
            if d.is_dir() and d.name != ".gitkeep":
                novel_ids.append(d.name)
        return sorted(novel_ids)
