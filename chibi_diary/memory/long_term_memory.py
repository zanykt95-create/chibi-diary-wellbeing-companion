"""
chibi_diary/memory/long_term_memory.py

Long-term SQLite-backed diary history for Chibi Diary.

Design decisions:
  - SQLite was chosen over a cloud database for Day 1 because it requires zero
    infrastructure and is trivially portable (just a .db file).
  - We provide BOTH sync and async methods. The sync variants are used by the
    ADK tool functions (which are called synchronously by the LLM agent loop).
    The async variants are available for a future FastAPI endpoint layer.
  - The DB path is configurable via the DATABASE_PATH environment variable so
    it can be swapped in tests or CI/CD without code changes.

Schema:
    diary_entries (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT NOT NULL,           -- ISO date YYYY-MM-DD
        raw_text    TEXT NOT NULL,           -- full diary entry
        mood        TEXT NOT NULL,           -- happy/sad/anxious/grateful/excited/neutral
        mood_score  REAL NOT NULL,           -- 0.0 to 1.0
        summary     TEXT NOT NULL,           -- ≤50-word summary
        chibi_url   TEXT NOT NULL,           -- illustration URL
        created_at  TEXT NOT NULL            -- ISO datetime of insert
    )
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator


class LongTermMemory:
    """SQLite-backed diary history manager.

    Provides synchronous and asynchronous methods for saving and querying
    diary entries. Designed to be instantiated once per process (singleton).

    Args:
        db_path: Filesystem path to the SQLite database file.
            Will be created automatically if it does not exist.

    Example:
        memory = LongTermMemory(db_path="./chibi_diary.db")
        entry_id = memory.save_entry_sync(
            date="2025-01-01",
            raw_text="Had a wonderful day!",
            mood="happy",
            mood_score=0.9,
            summary="A joyful and productive day.",
            chibi_url="https://example.com/chibi.png",
        )
    """

    CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS diary_entries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT    NOT NULL,
            raw_text    TEXT    NOT NULL,
            mood        TEXT    NOT NULL,
            mood_score  REAL    NOT NULL,
            summary     TEXT    NOT NULL,
            chibi_url   TEXT    NOT NULL,
            created_at  TEXT    NOT NULL,
            tags        TEXT    DEFAULT ''
        );
    """

    def __init__(self, db_path: str) -> None:
        """Initialise the LongTermMemory and ensure the schema exists.

        Args:
            db_path: Path to the SQLite .db file (created if missing).
        """
        self.db_path = db_path
        self._ensure_schema()

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing a SQLite connection with auto-commit/rollback.

        Yields:
            An open sqlite3.Connection. Commits on clean exit, rolls back on
            exception, and always closes the connection.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # rows behave like dicts
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        """Create the diary_entries table if it does not already exist."""
        with self._connect() as conn:
            conn.execute(self.CREATE_TABLE_SQL)
            try:
                conn.execute("ALTER TABLE diary_entries ADD COLUMN tags TEXT DEFAULT '';")
            except sqlite3.OperationalError:
                pass

    # -----------------------------------------------------------------------
    # Synchronous API (used by ADK tool functions)
    # -----------------------------------------------------------------------

    def save_entry_sync(
        self,
        date: str,
        raw_text: str,
        mood: str,
        mood_score: float,
        summary: str,
        chibi_url: str,
    ) -> int:
        """Insert a new diary entry and return its database ID.

        Args:
            date: ISO date string YYYY-MM-DD.
            raw_text: Full original diary entry text.
            mood: Mood label (happy/sad/anxious/grateful/excited/neutral).
            mood_score: Mood intensity from 0.0 to 1.0.
            summary: ≤50-word AI-generated summary.
            chibi_url: URL to the chibi illustration.

        Returns:
            The integer primary key (ID) of the newly inserted row.

        Raises:
            sqlite3.Error: If the insert fails.
        """
        created_at = datetime.now(tz=timezone.utc).isoformat()
        sql = """
            INSERT INTO diary_entries
                (date, raw_text, mood, mood_score, summary, chibi_url, created_at)
            VALUES
                (?, ?, ?, ?, ?, ?, ?)
        """
        with self._connect() as conn:
            cursor = conn.execute(
                sql, (date, raw_text, mood, mood_score, summary, chibi_url, created_at)
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def get_entries_sync(self, limit: int = 7) -> list[dict]:
        """Return the most recent diary entries, newest first.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            A list of dicts with keys: id, date, mood, mood_score,
            summary, chibi_url, created_at. raw_text is excluded for brevity.
        """
        sql = """
            SELECT id, date, mood, mood_score, summary, chibi_url, created_at
            FROM   diary_entries
            ORDER  BY created_at DESC
            LIMIT  ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_entries_by_mood_sync(self, mood: str, limit: int = 30) -> list[dict]:
        """Return diary entries filtered by a specific mood label.

        Args:
            mood: Mood label to filter by (e.g., "happy").
            limit: Maximum number of entries to return.

        Returns:
            A list of matching entry dicts, newest first.
        """
        sql = """
            SELECT id, date, mood, mood_score, summary, chibi_url, created_at
            FROM   diary_entries
            WHERE  mood = ?
            ORDER  BY created_at DESC
            LIMIT  ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (mood, limit)).fetchall()
            return [dict(row) for row in rows]

    def get_weekly_recap_sync(self) -> dict:
        """Generate a simple weekly mood summary from the last 7 diary entries.

        Computes:
          - Total entries in the last 7 days
          - Most common mood
          - Average mood score
          - List of entry summaries

        Returns:
            A dict with keys: period, total_entries, dominant_mood,
            average_score, entries (list of summary strings).
        """
        sql = """
            SELECT mood, mood_score, summary, date
            FROM   diary_entries
            WHERE  date >= date('now', '-7 days')
            ORDER  BY date DESC
        """
        with self._connect() as conn:
            rows = [dict(r) for r in conn.execute(sql).fetchall()]

        if not rows:
            return {
                "period": "last_7_days",
                "total_entries": 0,
                "dominant_mood": "neutral",
                "average_score": 0.0,
                "entries": [],
            }

        mood_counts = Counter(r["mood"] for r in rows)
        dominant_mood = mood_counts.most_common(1)[0][0]
        avg_score = round(sum(r["mood_score"] for r in rows) / len(rows), 2)

        return {
            "period": "last_7_days",
            "total_entries": len(rows),
            "dominant_mood": dominant_mood,
            "average_score": avg_score,
            "entries": [r["summary"] for r in rows],
        }

    def search_entries_sync(self, keyword: str, limit: int = 10) -> list[dict]:
        """Perform full-text search across raw_text and summary fields.

        Args:
            keyword: The search keyword.
            limit: Maximum number of entries to return.

        Returns:
            A list of matching entry dicts, newest first, excluding raw_text.
        """
        sql = """
            SELECT id, date, mood, mood_score, summary, created_at
            FROM diary_entries
            WHERE raw_text LIKE ? OR summary LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (f"%{keyword}%", f"%{keyword}%", limit)).fetchall()
            return [dict(row) for row in rows]

    def get_mood_trend_sync(self, days: int = 7) -> dict:
        """Get the mood trend over the last N days.

        Args:
            days: The number of days of history to include.

        Returns:
            A dictionary containing trend analysis.
        """

        sql = """
            SELECT date, mood, mood_score
            FROM diary_entries
            WHERE date >= date('now', ?)
            ORDER BY date ASC
        """
        with self._connect() as conn:
            rows = [dict(r) for r in conn.execute(sql, (f"-{days} days",)).fetchall()]

        if not rows:
            return {
                "period_days": days,
                "total_entries": 0,
                "trend": [],
                "average_score": 0.0,
                "mood_frequency": {},
                "dominant_mood": "neutral",
            }

        trend = [{"date": r["date"], "mood": r["mood"], "score": r["mood_score"]} for r in rows]
        avg = sum(r["mood_score"] for r in rows) / len(rows)
        moods = [r["mood"] for r in rows]
        mood_counts = Counter(moods)
        most_common_mood = mood_counts.most_common(1)[0][0]

        return {
            "period_days": days,
            "total_entries": len(rows),
            "trend": trend,
            "average_score": round(avg, 2),
            "mood_frequency": dict(mood_counts),
            "dominant_mood": most_common_mood,
        }

    def get_monthly_recap_sync(self) -> dict:
        """Generate a simple monthly mood summary from the last 30 days of diary entries.

        Returns:
            A dict with keys: period, total_entries, dominant_mood,
            average_score, entries (list of summary strings).
        """
        sql = """
            SELECT mood, mood_score, summary, date
            FROM   diary_entries
            WHERE  date >= date('now', '-30 days')
            ORDER  BY date DESC
        """
        with self._connect() as conn:
            rows = [dict(r) for r in conn.execute(sql).fetchall()]

        if not rows:
            return {
                "period": "last_30_days",
                "total_entries": 0,
                "dominant_mood": "neutral",
                "average_score": 0.0,
                "entries": [],
            }

        mood_counts = Counter(r["mood"] for r in rows)
        dominant_mood = mood_counts.most_common(1)[0][0]
        avg_score = round(sum(r["mood_score"] for r in rows) / len(rows), 2)

        return {
            "period": "last_30_days",
            "total_entries": len(rows),
            "dominant_mood": dominant_mood,
            "average_score": avg_score,
            "entries": [r["summary"] for r in rows],
        }

    def get_streak_sync(self) -> dict:
        """Count how many consecutive days (ending today) have at least one diary entry.

        Returns:
            A dict with keys: current_streak_days, last_entry_date.
        """
        from datetime import date, timedelta

        sql = """
            SELECT DISTINCT date FROM diary_entries
            WHERE date >= date('now', '-60 days')
            ORDER BY date DESC
        """
        with self._connect() as conn:
            rows = conn.execute(sql).fetchall()
            entry_dates = {row["date"] for row in rows}

        if not entry_dates:
            return {"current_streak_days": 0, "last_entry_date": None}

        # The SQL is ordered by date DESC, so the first row has the latest date in the last 60 days
        last_entry_date = rows[0]["date"]

        today = date.today()
        check_date = today
        if today.isoformat() not in entry_dates and (today - timedelta(days=1)).isoformat() in entry_dates:
            check_date = today - timedelta(days=1)

        current_streak_days = 0
        while check_date.isoformat() in entry_dates:
            current_streak_days += 1
            check_date -= timedelta(days=1)

        return {
            "current_streak_days": current_streak_days,
            "last_entry_date": last_entry_date,
        }

    # -----------------------------------------------------------------------
    # Async API (for future FastAPI / aiosqlite upgrade)
    # -----------------------------------------------------------------------

    async def save_entry(
        self,
        date: str,
        raw_text: str,
        mood: str,
        mood_score: float,
        summary: str,
        chibi_url: str,
    ) -> int:
        """Async version of save_entry_sync.

        Day 2: Replace with aiosqlite for true non-blocking I/O.

        Args:
            date: ISO date string YYYY-MM-DD.
            raw_text: Full diary entry text.
            mood: Mood label.
            mood_score: Mood intensity 0.0–1.0.
            summary: ≤50-word summary.
            chibi_url: Chibi illustration URL.

        Returns:
            The integer primary key of the inserted row.
        """
        # Temporary: delegate to sync version until aiosqlite is wired in.
        return self.save_entry_sync(date, raw_text, mood, mood_score, summary, chibi_url)

    async def get_entries(self, limit: int = 7) -> list[dict]:
        """Async version of get_entries_sync.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of recent entry dicts.
        """
        return self.get_entries_sync(limit=limit)

    async def get_entries_by_mood(self, mood: str, limit: int = 30) -> list[dict]:
        """Async version of get_entries_by_mood_sync.

        Args:
            mood: Mood label to filter by.
            limit: Maximum entries to return.

        Returns:
            List of matching entry dicts.
        """
        return self.get_entries_by_mood_sync(mood=mood, limit=limit)

    async def get_weekly_recap(self) -> dict:
        """Async version of get_weekly_recap_sync.

        Returns:
            Weekly mood summary dict.
        """
        return self.get_weekly_recap_sync()

    async def search_entries(self, keyword: str, limit: int = 10) -> list[dict]:
        """Async version of search_entries_sync."""
        return self.search_entries_sync(keyword, limit=limit)

    async def get_mood_trend(self, days: int = 7) -> dict:
        """Async version of get_mood_trend_sync."""
        return self.get_mood_trend_sync(days=days)

    async def get_monthly_recap(self) -> dict:
        """Async version of get_monthly_recap_sync."""
        return self.get_monthly_recap_sync()

    async def get_streak(self) -> dict:
        """Async version of get_streak_sync."""
        return self.get_streak_sync()
