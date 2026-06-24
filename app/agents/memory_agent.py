"""
app/agents/memory_agent.py

Memory Agent — Stage 4 (final stage) of the Chibi Diary pipeline.

Responsibility:
  1. Summarise the diary entry in ≤50 words.
  2. Parse mood, score, and chibi URL from upstream state.
  3. Persist a complete diary record to SQLite via `save_entry`.
  4. Return a final structured JSON-like summary that becomes the
     user-facing response from the full pipeline.

Why save here (not in the orchestrator)?
  The memory agent has full context from all previous stages via ADK session
  state. Centralising persistence in one agent makes it easy to add
  pre-save hooks (e.g., encryption, cloud backup) without touching other agents.
"""

from __future__ import annotations

from google.adk.agents import Agent

from app.tools.placeholder_tools import (
    get_recent_entries,
    get_monthly_recap,
    get_mood_trend,
    get_streak,
    save_entry,
    search_entries,
)


# ---------------------------------------------------------------------------
# Memory Agent definition
# ---------------------------------------------------------------------------
memory_agent = Agent(
    name="memory_agent",
    model="gemini-2.5-flash",
    description=(
        "Saves diary entries to SQLite, recalls mood trends and streak, "
        "and generates personalised wellbeing insights."
    ),
    instruction="""
You are the Memory Agent — the caring final stage of Chibi Diary. Your job is to save today's entry AND surface meaningful patterns from the past.

Context from previous stages:
- Diary text:   {captured_entry}
- Mood report:  {mood_report}
- Chibi result: {chibi_result}

EXECUTE THESE STEPS IN ORDER — do not skip any:

STEP 1: Call get_mood_trend with days=7.
STEP 2: Call get_streak.
STEP 3: Write a warm ≤50-word summary of the diary text.
STEP 4: Extract from mood_report and chibi_result:
  - mood: word after "MOOD: "
  - score: number after "SCORE: "
  - chibi_path: text after "CHIBI_PATH: "
  - today_date: today as YYYY-MM-DD
STEP 5: Call save_entry with date=today_date, text={captured_entry}, mood=mood, mood_score=score, summary=your_summary, chibi_url=chibi_path.
STEP 6: Based on get_mood_trend result and get_streak result, write a context_insight: a warm 1-2 sentence observation in Vietnamese. Be specific and kind. Mention streak if ≥2 days. Mention mood pattern if same mood appears ≥2 times.

OUTPUT ONLY (no markdown, no explanation):
{"entry": "<captured_entry>", "mood": "<mood>", "mood_score": <score>, "chibi_path": "<chibi_path>", "summary": "<summary>", "context_insight": "<Vietnamese insight>"}
""",
    tools=[save_entry, get_recent_entries, search_entries, get_mood_trend, get_monthly_recap, get_streak],
    # No output_key here — this is the final agent; its response is returned
    # directly to the user by the SequentialAgent orchestrator.
)
