"""
chibi_diary/agents/mood_analysis_agent.py

Mood Analysis Agent — Stage 2 of the Chibi Diary pipeline.

Responsibility: Analyse the emotional tone of the diary entry captured in
Stage 1 and return a structured mood classification with an intensity score
and a list of emotional keywords.

Design note: We intentionally limit the emotion vocabulary to six categories
(happy, sad, anxious, grateful, excited, neutral) in this prototype. This
keeps the downstream chibi-art prompt simple and the SQLite queries efficient.
More granular emotions (e.g., "nostalgic", "proud") can be added in Day 3.
"""

from __future__ import annotations

from google.adk.agents import Agent

from chibi_diary.tools.placeholder_tools import analyze_mood


# ---------------------------------------------------------------------------
# Mood Analysis Agent definition
# ---------------------------------------------------------------------------
mood_analysis_agent = Agent(
    name="mood_analysis_agent",
    model="gemini-2.5-flash",
    description=(
        "Analyzes the emotional tone of a diary entry and returns a mood "
        "classification with intensity score and keywords."
    ),
    instruction="""
You are the Mood Analysis Agent for Chibi Diary. Your job is to detect the
emotional tone of the diary entry and produce a structured mood report.

The diary entry to analyse is: {captured_entry}

Steps:
1. Call the `analyze_mood` tool with the diary entry text.
2. The tool returns a dict with keys: mood, score, keywords.
3. Allowed mood values: happy, sad, anxious, grateful, excited, neutral.
4. Score is a float 0.0 (mild) to 1.0 (intense).
5. Format your response exactly like this, one line per field:
   MOOD: <mood>
   SCORE: <score>
   KEYWORDS: <comma-separated keywords>

Do not add any other text. This structured format is parsed by the next agent.
""",
    tools=[analyze_mood],
    # Writes mood report string into session state under "mood_report".
    # The chibi illustrator reads this via {mood_report}.
    output_key="mood_report",
)
