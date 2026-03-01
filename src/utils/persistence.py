from __future__ import annotations

import json
import os
import re
import tempfile
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

    def _save_json(self, path: Path, data: dict[str, object]) -> None:
        """Save data as JSON file atomically."""
        # Write to temp file first, then rename (atomic on most filesystems)
        dir_path = path.parent
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create temp file in same directory to ensure atomic rename
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".json.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Atomic rename
            os.replace(tmp_path, path)
            self.logger.info(f"Saved JSON to: {path}")
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _load_json(self, path: Path) -> dict[str, object] | None:
        """Load data from JSON file. Return None if file doesn't exist."""
        if not path.exists():
            self.logger.debug(f"JSON file not found: {path}")
            return None

        text = path.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
            self.logger.debug(f"Loaded JSON from: {path}")
            return data
        except json.JSONDecodeError:
            pass

        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            candidate = "\n".join(lines).strip()
            try:
                data = json.loads(candidate)
                self.logger.warning(
                    "Loaded fenced JSON from %s; consider normalizing file format.",
                    path,
                )
                return data
            except json.JSONDecodeError:
                pass

        # Last fallback: extract first JSON object block if present.
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                data = json.loads(match.group(0))
                self.logger.warning(
                    "Loaded loosely formatted JSON from %s; consider normalizing file format.",
                    path,
                )
                return data
            except json.JSONDecodeError:
                pass

        self.logger.warning("Failed to parse JSON file: %s", path)
        return None

    def save_state(self, novel_id: str, state: dict[str, object]) -> None:
        """Save novel state to novel_state.json."""
        path = self._novel_dir(novel_id) / "novel_state.json"
        self._save_json(path, state)

    def load_state(self, novel_id: str) -> dict[str, object] | None:
        """Load novel state from novel_state.json."""
        path = self._novel_dir(novel_id) / "novel_state.json"
        return self._load_json(path)

    def save_world_setting(self, novel_id: str, setting: dict[str, object]) -> None:
        """Save world setting to world_setting.json."""
        path = self._novel_dir(novel_id) / "world_setting.json"
        self._save_json(path, setting)

    def load_world_setting(self, novel_id: str) -> dict[str, object] | None:
        """Load world setting from world_setting.json."""
        path = self._novel_dir(novel_id) / "world_setting.json"
        return self._load_json(path)

    def save_chapter(
        self,
        novel_id: str,
        chapter_id: str,
        content: str,
        metadata: dict[str, object],
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
    ) -> tuple[str | None, dict[str, object] | None]:
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

    def save_outline(self, novel_id: str, outline: dict[str, object]) -> None:
        """Save outline to outline.json."""
        path = self._novel_dir(novel_id) / "outline" / "outline.json"
        self._save_json(path, outline)

    def load_outline(self, novel_id: str) -> dict[str, object] | None:
        """Load outline from outline.json."""
        path = self._novel_dir(novel_id) / "outline" / "outline.json"
        return self._load_json(path)

    def save_character(
        self, novel_id: str, character_id: str, character: dict[str, object]
    ) -> None:
        """Save character data to characters/{character_id}.json."""
        path = self._novel_dir(novel_id) / "characters" / f"{character_id}.json"
        self._save_json(path, character)

    def load_character(
        self, novel_id: str, character_id: str
    ) -> dict[str, object] | None:
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

    def save_summary(
        self, novel_id: str, chapter_id: str, summary: dict[str, object]
    ) -> None:
        """Save summary to summaries/{chapter_id}.json."""
        path = self._novel_dir(novel_id) / "summaries" / f"{chapter_id}.json"
        self._save_json(path, summary)

    def load_summary(self, novel_id: str, chapter_id: str) -> dict[str, object] | None:
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
