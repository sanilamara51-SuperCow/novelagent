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

        # Foreshadowing table (REQUIREMENTS.md 8.1)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS foreshadowing (
                foreshadow_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                planted_chapter INTEGER NOT NULL,
                expected_payoff_start INTEGER,
                expected_payoff_end INTEGER,
                payoff_chapter INTEGER,
                status TEXT DEFAULT 'planted',
                importance TEXT DEFAULT 'major',
                related_characters TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Rhythm table (REQUIREMENTS.md 8.3)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rhythm (
                chapter_id INTEGER PRIMARY KEY,
                tension_score INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Story threads table (REQUIREMENTS.md 8.4)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS story_threads (
                thread_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                pov_character TEXT,
                arc TEXT,
                current_progress INTEGER DEFAULT 0,
                chapters TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # ========================================================================
    # Foreshadowing Ledger (REQUIREMENTS.md 8.1)
    # ========================================================================

    def add_foreshadow(
        self,
        foreshadow_id: str,
        description: str,
        planted_chapter: int,
        expected_payoff_range: list[int] | None = None,
        importance: str = "major",
        related_characters: list[str] | None = None,
    ) -> None:
        """Add or update a foreshadowing entry.

        Args:
            foreshadow_id: Unique identifier for the foreshadowing
            description: Description of the foreshadowing content
            planted_chapter: Chapter where the foreshadowing was planted
            expected_payoff_range: [start_chapter, end_chapter] for expected payoff
            importance: 'major' or 'minor'
            related_characters: List of related character names
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO foreshadowing
            (foreshadow_id, description, planted_chapter, expected_payoff_start,
             expected_payoff_end, payoff_chapter, status, importance, related_characters, updated_at)
            VALUES (?, ?, ?, ?, ?, NULL, 'planted', ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(foreshadow_id) DO UPDATE SET
                description = excluded.description,
                planted_chapter = excluded.planted_chapter,
                expected_payoff_start = excluded.expected_payoff_start,
                expected_payoff_end = excluded.expected_payoff_end,
                importance = excluded.importance,
                related_characters = excluded.related_characters,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                foreshadow_id,
                description,
                planted_chapter,
                expected_payoff_range[0] if expected_payoff_range and len(expected_payoff_range) > 0 else None,
                expected_payoff_range[1] if expected_payoff_range and len(expected_payoff_range) > 1 else None,
                importance,
                json.dumps(related_characters or []),
            ),
        )
        self.conn.commit()
        self.logger.debug(f"Added foreshadowing: {foreshadow_id}")

    def mark_foreshadow_paid_off(
        self,
        foreshadow_id: str,
        payoff_chapter: int,
    ) -> None:
        """Mark a foreshadowing as paid off (recycled).

        Args:
            foreshadow_id: Foreshadowing identifier
            payoff_chapter: Chapter where the foreshadowing was paid off
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE foreshadowing
            SET payoff_chapter = ?,
                status = 'paid_off',
                updated_at = CURRENT_TIMESTAMP
            WHERE foreshadow_id = ?
            """,
            (payoff_chapter, foreshadow_id),
        )
        self.conn.commit()
        self.logger.debug(f"Marked foreshadowing paid off: {foreshadow_id}")

    def get_foreshadowing_status(self) -> list[dict]:
        """Get all foreshadowing entries with their status.

        Returns:
            List of foreshadowing dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT foreshadow_id, description, planted_chapter,
                   expected_payoff_start, expected_payoff_end, payoff_chapter,
                   status, importance, related_characters
            FROM foreshadowing
            ORDER BY planted_chapter ASC
            """
        )
        rows = cursor.fetchall()

        return [
            {
                "foreshadow_id": row["foreshadow_id"],
                "description": row["description"],
                "planted_chapter": row["planted_chapter"],
                "expected_payoff_range": [row["expected_payoff_start"], row["expected_payoff_end"]]
                    if row["expected_payoff_start"] else [],
                "payoff_chapter": row["payoff_chapter"],
                "status": row["status"],
                "importance": row["importance"],
                "related_characters": json.loads(row["related_characters"]) if row["related_characters"] else [],
            }
            for row in rows
        ]

    def get_due_foreshadowing(self, current_chapter: int) -> list[dict]:
        """Get foreshadowing entries that are due for payoff.

        Args:
            current_chapter: Current chapter number

        Returns:
            List of foreshadowing dictionaries that are due or overdue
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT foreshadow_id, description, planted_chapter,
                   expected_payoff_start, expected_payoff_end, status
            FROM foreshadowing
            WHERE status = 'planted'
              AND expected_payoff_start IS NOT NULL
              AND expected_payoff_start <= ?
            ORDER BY expected_payoff_start ASC
            """,
            (current_chapter,),
        )
        rows = cursor.fetchall()

        result = []
        for row in rows:
            is_overdue = row["expected_payoff_end"] is not None and current_chapter > row["expected_payoff_end"]
            result.append({
                "foreshadow_id": row["foreshadow_id"],
                "description": row["description"],
                "planted_chapter": row["planted_chapter"],
                "expected_payoff_range": [row["expected_payoff_start"], row["expected_payoff_end"]]
                    if row["expected_payoff_start"] else [],
                "is_overdue": is_overdue,
            })
        return result

    # ========================================================================
    # Rhythm Tracker (REQUIREMENTS.md 8.3)
    # ========================================================================

    def record_tension(self, chapter_id: int, tension_score: int) -> None:
        """Record tension score for a chapter.

        Args:
            chapter_id: Chapter number
            tension_score: Tension score (1-10)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO rhythm (chapter_id, tension_score)
            VALUES (?, ?)
            ON CONFLICT(chapter_id) DO UPDATE SET
                tension_score = excluded.tension_score
            """,
            (chapter_id, tension_score),
        )
        self.conn.commit()

    def get_rhythm_sequence(self, limit: int | None = None) -> list[dict]:
        """Get tension score sequence for rhythm analysis.

        Args:
            limit: Optional limit for most recent chapters

        Returns:
            List of {chapter_id, tension_score} dictionaries
        """
        cursor = self.conn.cursor()
        query = "SELECT chapter_id, tension_score FROM rhythm ORDER BY chapter_id ASC"
        if limit:
            query = f"SELECT chapter_id, tension_score FROM rhythm ORDER BY chapter_id DESC LIMIT {limit}"

        cursor.execute(query)
        rows = cursor.fetchall()

        return [
            {"chapter_id": row["chapter_id"], "tension_score": row["tension_score"]}
            for row in rows
        ]

    def get_rhythm_analysis(self) -> dict:
        """Analyze rhythm trends.

        Returns:
            Dictionary with rhythm analysis:
            - recent_tensions: list of recent tension scores
            - trend: 'rising' | 'falling' | 'flat' | 'volatile'
            - suggestion: str
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT chapter_id, tension_score FROM rhythm ORDER BY chapter_id ASC")
        rows = cursor.fetchall()

        if len(rows) < 3:
            return {
                "recent_tensions": [row["tension_score"] for row in rows],
                "trend": "insufficient_data",
                "suggestion": "需要更多章节数据才能分析节奏趋势",
            }

        tensions = [row["tension_score"] for row in rows]
        recent = tensions[-3:]
        avg_recent = sum(recent) / len(recent)

        # Calculate trend
        if recent[-1] > recent[0] + 1:
            trend = "rising"
        elif recent[-1] < recent[0] - 1:
            trend = "falling"
        elif max(recent) - min(recent) <= 1:
            trend = "flat"
        else:
            trend = "volatile"

        # Generate suggestion
        suggestion = ""
        if trend == "flat" and avg_recent < 5:
            suggestion = "连续多章节奏平淡，建议增加冲突或转折点"
        elif trend == "rising" and recent[-1] >= 8:
            suggestion = "连续高潮后需要节奏回落，让读者喘息"
        elif trend == "falling" and recent[-1] <= 3:
            suggestion = "节奏持续走低，建议制造新的冲突或悬念"

        return {
            "recent_tensions": recent,
            "trend": trend,
            "suggestion": suggestion,
            "all_tensions": tensions,
        }

    # ========================================================================
    # Story Threads (REQUIREMENTS.md 8.4)
    # ========================================================================

    def add_story_thread(
        self,
        thread_id: str,
        name: str,
        pov_character: str = "",
        arc: str = "",
    ) -> None:
        """Add a new story thread.

        Args:
            thread_id: Unique thread identifier
            name: Thread name
            pov_character: POV character name
            arc: Overall arc description
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO story_threads (thread_id, name, pov_character, arc, chapters, updated_at)
            VALUES (?, ?, ?, ?, '[]', CURRENT_TIMESTAMP)
            ON CONFLICT(thread_id) DO UPDATE SET
                name = excluded.name,
                pov_character = excluded.pov_character,
                arc = excluded.arc,
                updated_at = CURRENT_TIMESTAMP
            """,
            (thread_id, name, pov_character, arc),
        )
        self.conn.commit()

    def update_thread_progress(
        self,
        thread_id: str,
        chapter_id: int,
    ) -> None:
        """Update story thread progress.

        Args:
            thread_id: Thread identifier
            chapter_id: Chapter where thread progressed
        """
        cursor = self.conn.cursor()

        # Get current chapters list
        cursor.execute("SELECT chapters FROM story_threads WHERE thread_id = ?", (thread_id,))
        row = cursor.fetchone()
        chapters = json.loads(row["chapters"]) if row and row["chapters"] else []

        if chapter_id not in chapters:
            chapters.append(chapter_id)
            chapters.sort()

        cursor.execute(
            """
            UPDATE story_threads
            SET chapters = ?,
                current_progress = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE thread_id = ?
            """,
            (json.dumps(chapters), chapters[-1] if chapters else 0, thread_id),
        )
        self.conn.commit()

    def get_story_threads(self) -> list[dict]:
        """Get all story threads with their progress.

        Returns:
            List of story thread dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT thread_id, name, pov_character, arc, current_progress, chapters
            FROM story_threads
            ORDER BY thread_id ASC
            """
        )
        rows = cursor.fetchall()

        return [
            {
                "thread_id": row["thread_id"],
                "name": row["name"],
                "pov_character": row["pov_character"],
                "arc": row["arc"],
                "current_progress": row["current_progress"],
                "chapters": json.loads(row["chapters"]) if row["chapters"] else [],
            }
            for row in rows
        ]

    def get_thread_gap_warning(self, max_gap: int = 5) -> list[dict]:
        """Get threads that haven't appeared in too many chapters.

        Args:
            max_gap: Maximum allowed gap between thread appearances

        Returns:
            List of threads that need attention
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(chapter_id) FROM rhythm")
        max_chapter = cursor.fetchone()[0] if cursor.fetchone() else 1

        threads = self.get_story_threads()
        warnings = []

        for thread in threads:
            chapters = thread["chapters"]
            if not chapters:
                warnings.append({
                    "thread_id": thread["thread_id"],
                    "name": thread["name"],
                    "issue": "从未出现",
                })
            elif max_chapter - chapters[-1] > max_gap:
                warnings.append({
                    "thread_id": thread["thread_id"],
                    "name": thread["name"],
                    "issue": f"已{max_chapter - chapters[-1]}章未出现",
                })

        return warnings
