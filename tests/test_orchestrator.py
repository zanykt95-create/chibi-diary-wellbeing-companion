"""
tests/test_orchestrator.py

Smoke tests for the Chibi Diary pipeline.

Philosophy: These tests verify that:
  1. All modules import without errors.
  2. The root agent is correctly defined as an ADK SequentialAgent.
  3. The four sub-agents are wired up in the correct order.
  4. Each stub tool returns a dict with the expected keys.
  5. The SQLite memory layer creates the schema and round-trips data correctly.

We do NOT test LLM responses here (non-deterministic). For LLM quality,
see the eval datasets in tests/eval/ (added on Day 3).

Run with: uv run pytest tests/ -v
"""

from __future__ import annotations

import os
import tempfile as _tempfile
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Ensure environment is set up before imports trigger ADK authentication.
# In CI/CD, set these via secrets. In local dev, use a .env file.
# ---------------------------------------------------------------------------
os.environ.setdefault("GOOGLE_API_KEY", "test-key-placeholder")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")

# Set a temp DB path for tests so we don't pollute the dev database
_TMP_DB_FILE = _tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP_DB = _TMP_DB_FILE.name
_TMP_DB_FILE.close()
os.environ["DATABASE_PATH"] = _TMP_DB

from chibi_diary.tools.placeholder_tools import (
    save_entry,
    get_recent_entries,
    search_entries,
    get_mood_trend,
    get_monthly_recap,
    get_streak,
)


# ===========================================================================
# Import tests — verify the module structure is intact
# ===========================================================================

class TestImports:
    """Verify all modules import cleanly without runtime errors."""

    def test_orchestrator_imports(self) -> None:
        """Root orchestrator module should import and expose root_agent."""
        from chibi_diary.orchestrator import root_agent  # noqa: F401

        assert root_agent is not None

    def test_capture_agent_imports(self) -> None:
        """Capture agent module should expose a capture_agent variable."""
        from chibi_diary.agents.capture_agent import capture_agent  # noqa: F401

        assert capture_agent is not None

    def test_mood_analysis_agent_imports(self) -> None:
        """Mood agent module should expose mood_analysis_agent."""
        from chibi_diary.agents.mood_analysis_agent import mood_analysis_agent  # noqa: F401

        assert mood_analysis_agent is not None

    def test_chibi_illustrator_agent_imports(self) -> None:
        """Illustrator agent module should expose chibi_illustrator_agent."""
        from chibi_diary.agents.chibi_illustrator_agent import chibi_illustrator_agent  # noqa: F401

        assert chibi_illustrator_agent is not None

    def test_memory_agent_imports(self) -> None:
        """Memory agent module should expose memory_agent."""
        from chibi_diary.agents.memory_agent import memory_agent  # noqa: F401

        assert memory_agent is not None


# ===========================================================================
# Agent structure tests
# ===========================================================================

class TestOrchestratorStructure:
    """Verify the orchestrator agent is wired up correctly."""

    def test_root_agent_is_sequential(self) -> None:
        """root_agent should be an ADK SequentialAgent (deterministic workflow agent)."""
        from google.adk.agents import SequentialAgent as SeqType

        from chibi_diary.orchestrator import root_agent

        assert isinstance(root_agent, SeqType), (
            f"Expected SequentialAgent, got {type(root_agent).__name__}"
        )

    def test_root_agent_name(self) -> None:
        """root_agent should be named chibi_diary_orchestrator."""
        from chibi_diary.orchestrator import root_agent

        assert root_agent.name == "chibi_diary_orchestrator"

    def test_root_agent_has_four_sub_agents(self) -> None:
        """Pipeline must have exactly four sub-agents."""
        from chibi_diary.orchestrator import root_agent

        assert len(root_agent.sub_agents) == 4, (
            f"Expected 4 sub-agents, found {len(root_agent.sub_agents)}"
        )

    def test_sub_agent_order(self) -> None:
        """Sub-agents must be in the correct pipeline order."""
        from chibi_diary.orchestrator import root_agent

        expected_names = [
            "capture_agent",
            "mood_analysis_agent",
            "chibi_illustrator_agent",
            "memory_agent",
        ]
        actual_names = [agent.name for agent in root_agent.sub_agents]
        assert actual_names == expected_names, (
            f"Sub-agent order mismatch.\nExpected: {expected_names}\nGot: {actual_names}"
        )

    def test_sub_agents_use_correct_model(self) -> None:
        """All LlmAgents should use a gemini model (gemini-2.5-flash)."""
        from google.adk.agents import Agent

        from chibi_diary.orchestrator import root_agent

        for sub in root_agent.sub_agents:
            if isinstance(sub, Agent):
                assert "gemini" in str(sub.model).lower(), (
                    f"Agent {sub.name} uses unexpected model: {sub.model}"
                )


# ===========================================================================
# Stub tool tests
# ===========================================================================

class TestStubTools:
    """Verify stub tools return dicts with the expected keys."""

    def test_validate_entry_valid(self) -> None:
        """validate_entry should accept a well-formed diary entry."""
        from chibi_diary.tools.placeholder_tools import validate_entry

        result = validate_entry("Today was a great day! I finished my project.")
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert "cleaned_text" in result
        assert "word_count" in result
        assert result["word_count"] >= 3

    def test_validate_entry_empty(self) -> None:
        """validate_entry should reject an empty string."""
        from chibi_diary.tools.placeholder_tools import validate_entry

        result = validate_entry("")
        assert result["valid"] is False

    def test_validate_entry_too_short(self) -> None:
        """validate_entry should reject a one-word entry."""
        from chibi_diary.tools.placeholder_tools import validate_entry

        result = validate_entry("Hi")
        assert result["valid"] is False

    def test_analyze_mood_returns_required_keys(self) -> None:
        """analyze_mood must return mood, score, and keywords."""
        from chibi_diary.tools.placeholder_tools import analyze_mood

        result = analyze_mood("Today was a great day! I finished my project and felt really proud.")
        assert isinstance(result, dict)
        assert "mood" in result
        assert "score" in result
        assert "keywords" in result

    def test_analyze_mood_score_range(self) -> None:
        """Mood score must be between 0.0 and 1.0."""
        from chibi_diary.tools.placeholder_tools import analyze_mood

        result = analyze_mood("I had a wonderful, joyful, amazing day full of love and laughter!")
        assert 0.0 <= result["score"] <= 1.0

    def test_analyze_mood_valid_label(self) -> None:
        """Mood label must be one of the six allowed values."""
        from chibi_diary.tools.placeholder_tools import analyze_mood

        allowed = {"happy", "sad", "anxious", "grateful", "excited", "neutral"}
        result = analyze_mood("Today was a great day! I finished my project.")
        assert result["mood"] in allowed, f"Unexpected mood label: {result['mood']}"

    def test_generate_chibi_image_returns_url(self) -> None:
        """generate_chibi_image stub must return a dict with image_url."""
        from chibi_diary.tools.placeholder_tools import generate_chibi_image

        prompt = "A cute chibi character beaming with joy, sunny meadow background"
        result = generate_chibi_image(prompt)
        assert isinstance(result, dict)
        assert "image_url" in result
        assert result["image_url"].startswith("http")
        assert "prompt_used" in result
        assert result["prompt_used"] == prompt

    def test_save_entry_returns_success(self) -> None:
        """save_entry should return success with a positive entry_id."""
        from chibi_diary.tools.placeholder_tools import save_entry

        result = save_entry(
            date="2025-01-01",
            text="Today was a great day! I finished my project and felt really proud.",
            mood="happy",
            mood_score=0.8,
            summary="Had a productive and fulfilling day completing a personal project.",
            chibi_url="https://placeholder.chibi.art/sample.png",
        )
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["entry_id"] > 0

    def test_get_recent_entries_returns_list(self) -> None:
        """get_recent_entries should return a list (possibly empty)."""
        from chibi_diary.tools.placeholder_tools import get_recent_entries

        result = get_recent_entries(limit=5)
        assert isinstance(result, list)


# ===========================================================================
# Memory layer tests
# ===========================================================================

class TestSessionMemory:
    """Verify SessionMemory basic operations."""

    def test_set_and_get(self) -> None:
        """Values set should be retrievable by key."""
        from chibi_diary.memory.session_memory import SessionMemory

        mem = SessionMemory()
        mem.set("mood", "happy")
        assert mem.get("mood") == "happy"

    def test_get_missing_key_returns_default(self) -> None:
        """Getting a missing key should return the default value."""
        from chibi_diary.memory.session_memory import SessionMemory

        mem = SessionMemory()
        assert mem.get("nonexistent") is None
        assert mem.get("nonexistent", "fallback") == "fallback"

    def test_clear(self) -> None:
        """clear() should remove all stored values."""
        from chibi_diary.memory.session_memory import SessionMemory

        mem = SessionMemory()
        mem.set("a", 1)
        mem.set("b", 2)
        mem.clear()
        assert mem.get_all() == {}

    def test_get_all(self) -> None:
        """get_all() should return a copy of the full store."""
        from chibi_diary.memory.session_memory import SessionMemory

        mem = SessionMemory()
        mem.set("x", 10)
        mem.set("y", 20)
        all_data = mem.get_all()
        assert all_data == {"x": 10, "y": 20}


class TestLongTermMemory:
    """Verify LongTermMemory schema creation and basic CRUD."""

    @pytest.fixture()
    def db(self) -> Any:
        """Provide a fresh LongTermMemory backed by a temp SQLite file."""
        import tempfile

        from chibi_diary.memory.long_term_memory import LongTermMemory

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield LongTermMemory(db_path=db_path)

    def test_schema_creation(self, db: Any) -> None:
        """LongTermMemory init should create the diary_entries table."""
        import sqlite3

        conn = sqlite3.connect(db.db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        table_names = [t[0] for t in tables]
        assert "diary_entries" in table_names

    def test_save_and_retrieve(self, db: Any) -> None:
        """Saved entries should be retrievable via get_entries_sync."""
        entry_id = db.save_entry_sync(
            date="2025-01-15",
            raw_text="Today was a great day! I finished my project.",
            mood="happy",
            mood_score=0.85,
            summary="Completed project with pride and joy.",
            chibi_url="https://placeholder.chibi.art/sample.png",
        )
        assert entry_id > 0

        entries = db.get_entries_sync(limit=10)
        assert len(entries) == 1
        assert entries[0]["mood"] == "happy"
        assert entries[0]["date"] == "2025-01-15"

    def test_weekly_recap_empty(self, db: Any) -> None:
        """Weekly recap on empty DB should return 0 total_entries."""
        recap = db.get_weekly_recap_sync()
        assert recap["total_entries"] == 0
        assert recap["dominant_mood"] == "neutral"

    def test_get_by_mood(self, db: Any) -> None:
        """Mood-filtered queries should return only matching entries."""
        db.save_entry_sync("2025-01-01", "Happy day", "happy", 0.9, "Great day", "http://a.png")
        db.save_entry_sync("2025-01-02", "Sad day", "sad", 0.7, "Hard day", "http://b.png")

        happy_entries = db.get_entries_by_mood_sync("happy")
        assert len(happy_entries) == 1
        assert happy_entries[0]["mood"] == "happy"


# ===========================================================================
# End-to-end pipeline smoke test (tool stubs only — no real LLM call)
# ===========================================================================

class TestPipelineSmoke:
    """Smoke test: verify the pipeline tools produce a complete response shape
    when called in the correct order (no LLM invocation required)."""

    def test_full_pipeline_tools_sequence(self) -> None:
        """Simulate the pipeline by calling each tool in order and asserting
        the final response has all required keys."""
        from chibi_diary.tools.placeholder_tools import (
            analyze_mood,
            generate_chibi_image,
            save_entry,
            validate_entry,
        )

        sample_entry = "Today was a great day! I finished my project and felt really proud."

        # Stage 1: capture
        capture_result = validate_entry(sample_entry)
        assert capture_result["valid"] is True
        cleaned_text = capture_result["cleaned_text"]

        # Stage 2: mood analysis
        mood_result = analyze_mood(cleaned_text)
        mood = mood_result["mood"]
        score = mood_result["score"]

        # Stage 3: chibi art
        prompt = f"A cute chibi character feeling {mood}, soft pastel colours, kawaii"
        art_result = generate_chibi_image(prompt)
        chibi_url = art_result["image_url"]

        # Stage 4: memory
        save_result = save_entry(
            date="2025-01-01",
            text=cleaned_text,
            mood=mood,
            mood_score=score,
            summary="Had a productive and fulfilling day completing a personal project.",
            chibi_url=chibi_url,
        )

        # Assemble the expected final response shape
        final_response = {
            "entry": cleaned_text,
            "mood": mood,
            "mood_score": score,
            "chibi_url": chibi_url,
            "summary": "Had a productive and fulfilling day completing a personal project.",
        }

        # Assert all required keys are present
        required_keys = {"entry", "mood", "chibi_url", "summary"}
        for key in required_keys:
            assert key in final_response, f"Missing key in final response: {key}"

        # Assert types
        assert isinstance(final_response["entry"], str)
        assert isinstance(final_response["mood"], str)
        assert isinstance(final_response["mood_score"], float)
        assert isinstance(final_response["chibi_url"], str)
        assert isinstance(final_response["summary"], str)

        # Assert the DB was written
        assert save_result["success"] is True
        assert save_result["entry_id"] > 0


class TestMemoryAgentTools:
    """Tests for new Day 3 memory tools."""

    def test_search_entries_no_results(self):
        """search_entries returns 'No results' for unknown keyword."""
        result = search_entries("zzz_nonexistent_xyz")
        assert "No results" in result or "SEARCH_RESULTS" in result

    def test_get_mood_trend_structure(self):
        """get_mood_trend returns MOOD_TREND string."""
        result = get_mood_trend(days=7)
        assert "MOOD_TREND" in result

    def test_get_monthly_recap_structure(self):
        """get_monthly_recap returns MONTHLY_RECAP string."""
        result = get_monthly_recap()
        assert "MONTHLY_RECAP" in result or "recap" in result.lower()

    def test_get_streak_structure(self):
        """get_streak returns STREAK string."""
        result = get_streak()
        assert "STREAK" in result

    def test_long_term_memory_search(self, tmp_path):
        """LongTermMemory.search_entries_sync returns matching entries."""
        from chibi_diary.memory.long_term_memory import LongTermMemory
        db = LongTermMemory(db_path=str(tmp_path / "test.db"))
        db.save_entry_sync("2025-01-01", "I love hiking in the mountains", "happy", 0.9, "Great day hiking", "")
        db.save_entry_sync("2025-01-02", "Tired from work", "sad", 0.3, "Tiring workday", "")
        results = db.search_entries_sync("hiking")
        assert len(results) == 1
        assert results[0]["date"] == "2025-01-01"

    def test_mood_trend_empty_db(self, tmp_path):
        """get_mood_trend_sync returns zeroed dict on empty DB."""
        from chibi_diary.memory.long_term_memory import LongTermMemory
        db = LongTermMemory(db_path=str(tmp_path / "empty.db"))
        trend = db.get_mood_trend_sync(days=7)
        assert trend["total_entries"] == 0
        assert trend["dominant_mood"] == "neutral"
        assert trend["average_score"] == 0.0

    def test_streak_with_entries(self, tmp_path):
        """get_streak_sync counts consecutive days correctly."""
        from chibi_diary.memory.long_term_memory import LongTermMemory
        from datetime import date, timedelta
        db = LongTermMemory(db_path=str(tmp_path / "streak.db"))
        today = date.today()
        for i in range(3):
            d = (today - timedelta(days=i)).isoformat()
            db.save_entry_sync(d, f"Entry {i}", "happy", 0.8, f"Summary {i}", "")
        streak = db.get_streak_sync()
        assert streak["current_streak_days"] >= 3


# Cleanup temp DB after test session
import atexit as _atexit
import os as _os
_atexit.register(lambda: _os.path.exists(_TMP_DB) and _os.unlink(_TMP_DB))
