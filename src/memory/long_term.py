from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.utils.logger import get_logger


class LongTermMemory:
    """SQLite-based long-term memory for characters, events, and timeline."""

    def __init__(self, novel_id: str, db_path: str | None = None) -> None:
        """Initialize long-term memory storage.

        Args:
            novel_id: Unique identifier for the novel
            db_path: Custom database path (defaults to data/novels/{novel_id}/memory.sqlite)
        """
        self.novel_id = novel_id
        self.logger = get_logger(f"memory.{novel_id}")

        if db_path is None:
            db_path = f"data/novels/{novel_id}/memory.sqlite"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row

        self._init_tables()
        self.logger.info(f"Long-term memory initialized at {self.db_path}")

    def _init_tables(self) -> None:
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Characters table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Events table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Timeline table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                event TEXT NOT NULL,
                source_chapter TEXT NOT NULL
            )
            """
        )

        # Relationships table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS relationships (
                char1_id TEXT NOT NULL,
                char2_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (char1_id, char2_id),
                FOREIGN KEY (char1_id) REFERENCES characters(id),
                FOREIGN KEY (char2_id) REFERENCES characters(id)
            )
            """
        )

        self.conn.commit()

    # Character methods
    def update_character(self, character_id: str, data: dict) -> None:
        """Update or insert a character.

        Args:
            character_id: Unique character identifier
            data: Character data dictionary (must include 'name' key)
        """
        name = data.get("name", character_id)
        json_data = json.dumps(data)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO characters (id, name, data, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                data = excluded.data,
                updated_at = CURRENT_TIMESTAMP
            """,
            (character_id, name, json_data),
        )
        self.conn.commit()
        self.logger.debug(f"Updated character: {character_id}")

    def get_character(self, character_id: str) -> dict | None:
        """Retrieve a character by ID.

        Args:
            character_id: Character identifier

        Returns:
            Character data dictionary or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT data FROM characters WHERE id = ?",
            (character_id,),
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return json.loads(row["data"])

    def list_characters(self) -> list[dict]:
        """List all characters.

        Returns:
            List of character data dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT data FROM characters ORDER BY name")
        rows = cursor.fetchall()

        return [json.loads(row["data"]) for row in rows]

    def search_characters(self, query: str) -> list[dict]:
        """Search characters by name.

        Args:
            query: Search query string

        Returns:
            List of matching character data dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT data FROM characters WHERE name LIKE ? ORDER BY name",
            (f"%{query}%",),
        )
        rows = cursor.fetchall()

        return [json.loads(row["data"]) for row in rows]

    # Event methods
    def add_event(
        self,
        chapter_id: str,
        event_type: str,
        description: str,
        timestamp: str | None = None,
    ) -> int:
        """Add a new event.

        Args:
            chapter_id: Source chapter identifier
            event_type: Type of event
            description: Event description
            timestamp: Optional custom timestamp

        Returns:
            Event ID
        """
        cursor = self.conn.cursor()

        if timestamp:
            cursor.execute(
                """
                INSERT INTO events (chapter_id, event_type, description, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (chapter_id, event_type, description, timestamp),
            )
        else:
            cursor.execute(
                """
                INSERT INTO events (chapter_id, event_type, description)
                VALUES (?, ?, ?)
                """,
                (chapter_id, event_type, description),
            )

        self.conn.commit()
        event_id = cursor.lastrowid
        self.logger.debug(f"Added event {event_id}: {event_type}")
        return event_id

    def query_events(
        self,
        chapter_id: str | None = None,
        event_type: str | None = None,
    ) -> list[dict]:
        """Query events with optional filters.

        Args:
            chapter_id: Filter by chapter ID
            event_type: Filter by event type

        Returns:
            List of event dictionaries
        """
        cursor = self.conn.cursor()
        conditions = []
        params = []

        if chapter_id:
            conditions.append("chapter_id = ?")
            params.append(chapter_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        where_clause = " AND ".join(conditions) if conditions else "1"

        cursor.execute(
            f"""
            SELECT id, chapter_id, event_type, description, timestamp
            FROM events
            WHERE {where_clause}
            ORDER BY timestamp DESC
            """,
            params,
        )
        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "chapter_id": row["chapter_id"],
                "event_type": row["event_type"],
                "description": row["description"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    # Timeline methods
    def mark_timeline(self, year: int, event: str, source_chapter: str) -> int:
        """Mark an event on the timeline.

        Args:
            year: Year of the event
            event: Event description
            source_chapter: Source chapter identifier

        Returns:
            Timeline entry ID
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO timeline (year, event, source_chapter)
            VALUES (?, ?, ?)
            """,
            (year, event, source_chapter),
        )
        self.conn.commit()
        entry_id = cursor.lastrowid
        self.logger.debug(f"Added timeline entry for year {year}")
        return entry_id

    def get_timeline(self) -> list[dict]:
        """Get all timeline entries sorted by year.

        Returns:
            List of timeline entry dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, year, event, source_chapter
            FROM timeline
            ORDER BY year ASC, id ASC
            """
        )
        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "year": row["year"],
                "event": row["event"],
                "source_chapter": row["source_chapter"],
            }
            for row in rows
        ]

    # Relationship methods
    def update_relationship(
        self,
        char1: str,
        char2: str,
        rel_type: str,
        description: str = "",
    ) -> None:
        """Update or create a relationship between two characters.

        Args:
            char1: First character ID
            char2: Second character ID
            rel_type: Type of relationship
            description: Optional relationship description
        """
        # Ensure consistent ordering for primary key
        char1_id, char2_id = sorted([char1, char2])

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO relationships (char1_id, char2_id, relationship_type, description, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(char1_id, char2_id) DO UPDATE SET
                relationship_type = excluded.relationship_type,
                description = excluded.description,
                updated_at = CURRENT_TIMESTAMP
            """,
            (char1_id, char2_id, rel_type, description),
        )
        self.conn.commit()
        self.logger.debug(f"Updated relationship: {char1} <-> {char2}")

    def get_relationships(self, char_id: str) -> list[dict]:
        """Get all relationships for a character.

        Args:
            char_id: Character ID

        Returns:
            List of relationship dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT 
                char1_id,
                char2_id,
                relationship_type,
                description,
                CASE 
                    WHEN char1_id = ? THEN char2_id
                    ELSE char1_id
                END as other_char
            FROM relationships
            WHERE char1_id = ? OR char2_id = ?
            ORDER BY updated_at DESC
            """,
            (char_id, char_id, char_id),
        )
        rows = cursor.fetchall()

        return [
            {
                "char1_id": row["char1_id"],
                "char2_id": row["char2_id"],
                "relationship_type": row["relationship_type"],
                "description": row["description"],
                "other_character": row["other_char"],
            }
            for row in rows
        ]
