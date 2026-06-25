"""
app/agents/memory_agent.py

Memory Agent — Stage 4 (final stage) of the Chibi Diary pipeline.

Responsibility:
  1. Summarise the diary entry in ≤50 words.
  2. Parse mood, score, and chibi URL from upstream state.
  3. Persist a complete diary record to SQLite via `save_entry`.
  4. Display the chibi image as an ADK artifact (shows inline in Dev UI).
  5. Return a warm, conversational Vietnamese response to the user.

Why save here (not in the orchestrator)?
  The memory agent has full context from all previous stages via ADK session
  state. Centralising persistence in one agent makes it easy to add
  pre-save hooks (e.g., encryption, cloud backup) without touching other agents.
"""

from __future__ import annotations

import base64
from datetime import date
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.genai import types as genai_types

from chibi_diary.tools.placeholder_tools import (
    get_recent_entries,
    get_monthly_recap,
    get_mood_trend,
    get_streak,
    save_entry,
    search_entries,
)


# ---------------------------------------------------------------------------
# Date tool — gives the model today's date without needing to run code
# ---------------------------------------------------------------------------

def get_today_date() -> dict:
    """Return today's date as a YYYY-MM-DD string.

    Returns:
        dict with key 'today' containing the date string.
    """
    return {"today": date.today().isoformat()}


# ---------------------------------------------------------------------------
# Inline image tool — saves chibi PNG as an ADK artifact so Dev UI shows it
# ---------------------------------------------------------------------------

async def display_chibi_image(image_path: str, tool_context: ToolContext) -> dict:
    """Read the chibi PNG from disk and save it as an ADK artifact.

    ADK Dev UI automatically renders artifacts that have image/* MIME types,
    so the user sees the chibi inline in the chat response.

    Args:
        image_path: Local filesystem path to the generated chibi PNG.

    Returns:
        dict with 'status' and 'filename' keys.
    """
    try:
        path = Path(image_path)
        if not path.exists():
            return {"status": "error", "message": f"Image not found: {image_path}"}

        image_bytes = path.read_bytes()
        artifact = genai_types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        await tool_context.save_artifact(filename="chibi_today.png", artifact=artifact)
        return {"status": "ok", "filename": "chibi_today.png"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Memory Agent definition
# ---------------------------------------------------------------------------
memory_agent = Agent(
    name="memory_agent",
    model="gemini-2.5-flash",
    description=(
        "Saves diary entries to SQLite, recalls mood trends and streak, "
        "displays the chibi image, and returns a warm Vietnamese response."
    ),
    instruction="""
You are the Memory Agent — the warm, caring final stage of Chibi Diary.

You have access to these values from earlier pipeline stages:
- Diary text: {captured_entry}
- Mood report: {mood_report}  (contains lines like "MOOD: happy", "SCORE: 0.45")
- Chibi result: {chibi_result}  (contains a line like "CHIBI_PATH: output/chibi_images/chibi_xxx.png")

Do the following by calling tools one at a time:

1. Call get_mood_trend(days=7) to retrieve the past week's mood history.
2. Call get_streak() to find out how many consecutive days the user has journaled.
3. Call get_today_date() to get today's date.
4. Parse mood, score, chibi_path from the context above.
5. Call save_entry(date=<today from step 3>, text=<diary text>, mood=<mood>, mood_score=<score>, summary=<50-word warm summary>, chibi_url=<chibi_path>).
6. If chibi_path does not contain "error", call display_chibi_image(image_path=<chibi_path>).

After all tool calls are done, write your final reply to the user.
Reply in the SAME LANGUAGE the user wrote their diary entry in.
Do NOT output JSON. Do NOT use curly braces. Write naturally and warmly.

Format your reply like this:
<mood emoji> <one sentence about today's emotion>

<50-word warm summary of the diary>

<1-2 sentences of personal insight based on streak and mood trend. Mention streak if ≥ 2 days. Note mood pattern if the same mood appears ≥ 2 times in the past week.>

<a short encouraging closing line> 🎨
""",
    tools=[
        get_today_date,
        save_entry,
        get_recent_entries,
        search_entries,
        get_mood_trend,
        get_monthly_recap,
        get_streak,
        display_chibi_image,
    ],
    # No output_key — final agent, response goes directly to user.
)
