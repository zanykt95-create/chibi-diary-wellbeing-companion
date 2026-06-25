"""
app/tools/placeholder_tools.py

Stub (placeholder) implementations of all Chibi Diary tools.

Philosophy: Stubs return *realistic* data so that the full agent pipeline can
be exercised and tested without any real API keys or external services. Each
stub is designed to be a drop-in replacement — swapping in the real
implementation on Day 2+ requires only changing the function body, not the
signature or return schema.

All tool functions follow ADK tool rules:
  - Clear Google-style docstrings (sent to the LLM as tool descriptions)
  - Type hints on every parameter and return type
  - Return type is dict (JSON-serializable)
  - No ToolContext parameter unless state access is explicitly needed
  - No default parameter values (ADK generates better schemas without them)
"""

from __future__ import annotations

import os
import random
import re
from datetime import date, datetime

from chibi_diary.memory.long_term_memory import LongTermMemory
from chibi_diary.memory.session_memory import SessionMemory

# ---------------------------------------------------------------------------
# Module-level singletons
# In a real async app these would be dependency-injected. For the prototype,
# singletons are fine and keep the tool signatures simple.
# ---------------------------------------------------------------------------
_session_memory = SessionMemory()
_db_path = os.environ.get("DATABASE_PATH", "./chibi_diary.db")
_long_term_memory = LongTermMemory(db_path=_db_path)
_memory = _long_term_memory


# ===========================================================================
# capture_agent tools
# ===========================================================================

def validate_entry(text: str) -> dict:
    """Validate and clean a raw diary entry text.

    Checks that the entry is non-empty and contains at least a few words.
    Strips leading/trailing whitespace and normalises internal whitespace.

    Args:
        text: The raw diary entry text submitted by the user.

    Returns:
        A dict with keys:
          - valid (bool): True if the entry passes validation.
          - cleaned_text (str): The whitespace-normalised entry text.
          - word_count (int): Number of words in the cleaned text.
          - reason (str): Human-readable validation message.
    """
    # Clear session state at the start of each new diary pipeline run.
    _session_memory.clear()

    # Strip outer whitespace
    cleaned = text.strip()

    # Normalise multiple internal spaces/newlines to single spaces
    cleaned = re.sub(r"\s+", " ", cleaned)

    word_count = len(cleaned.split()) if cleaned else 0

    if not cleaned:
        return {
            "valid": False,
            "cleaned_text": "",
            "word_count": 0,
            "reason": "Entry is empty. Please write at least a sentence about your day.",
        }

    if word_count < 3:
        return {
            "valid": False,
            "cleaned_text": cleaned,
            "word_count": word_count,
            "reason": f"Entry is too short ({word_count} words). Please share a bit more!",
        }

    # Store in session memory for downstream agents
    _session_memory.set("raw_entry", cleaned)

    return {
        "valid": True,
        "cleaned_text": cleaned,
        "word_count": word_count,
        "reason": "Entry validated successfully.",
    }


# ===========================================================================
# mood_analysis_agent tools
# ===========================================================================

# Mood keyword hints used by the stub to simulate realistic analysis
_MOOD_KEYWORDS: dict[str, list[str]] = {
    "happy": ["great", "wonderful", "joy", "love", "fantastic", "amazing", "proud", "excited", "vui", "hạnh phúc", "tuyệt vời"],
    "sad": ["sad", "upset", "cry", "miss", "lonely", "disappointed", "hurt", "lost", "buồn", "khóc", "tệ"],
    "anxious": ["worried", "stress", "nervous", "anxiety", "panic", "fear", "overwhelm", "dread", "lo lắng", "lo âu", "hồi hộp"],
    "grateful": ["grateful", "thankful", "blessed", "appreciate", "fortune", "lucky", "glad", "biết ơn", "cảm ơn", "cảm kích"],
    "excited": ["excited", "thrilled", "can't wait", "pumped", "energised", "fired up", "hyped", "hào hứng", "phấn khích", "thăng chức"],
    "neutral": [],  # fallback
}


def analyze_mood(text: str) -> dict:
    """Analyse the emotional tone of a diary entry.

    Identifies the primary emotion, rates its intensity on a 0.0–1.0 scale,
    and extracts the most emotionally significant keywords from the text.

    Args:
        text: The diary entry text to analyse.

    Returns:
        A dict with keys:
          - mood (str): Primary emotion — one of: happy, sad, anxious,
            grateful, excited, neutral.
          - score (float): Intensity score from 0.0 (mild) to 1.0 (intense).
          - keywords (list[str]): Up to 5 emotionally significant words.
          - confidence (float): Model confidence in the mood classification.
    """
    # STUB LOGIC: Detect mood from keyword presence.
    # Day 2: Replace with a real Gemini API call or dedicated sentiment model.
    text_lower = text.lower()
    detected_mood = "neutral"
    matched_keywords: list[str] = []

    for mood, hints in _MOOD_KEYWORDS.items():
        hits = [w for w in hints if w in text_lower]
        if len(hits) > len(matched_keywords):
            detected_mood = mood
            matched_keywords = hits

    # If no keywords matched, look for positive/negative word counts
    positive_words = ["good", "nice", "well", "happy", "fine", "great", "okay", "tốt", "ổn", "vui"]
    negative_words = ["bad", "terrible", "awful", "horrible", "rough", "hard", "tệ", "chán", "buồn"]

    if detected_mood == "neutral":
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        if pos_count > neg_count:
            detected_mood = "happy"
        elif neg_count > pos_count:
            detected_mood = "sad"

    # Score: base on word count of emotional language (stub heuristic)
    word_count = len(text.split())
    base_score = min(0.9, 0.3 + (len(matched_keywords) * 0.15))
    # Add small random variance to simulate model uncertainty
    score = round(min(1.0, base_score + random.uniform(-0.05, 0.05)), 2)

    # Extract up to 5 keywords — prefer matched hints, then fill with nouns
    keywords = matched_keywords[:5]
    if not keywords:
        # Fallback: return the 3 longest words as proxy "keywords"
        words = [w.strip(".,!?") for w in text.split() if len(w) > 4]
        keywords = sorted(set(words), key=len, reverse=True)[:3]

    # Store in session memory
    _session_memory.set("mood", detected_mood)
    _session_memory.set("mood_score", score)
    _session_memory.set("mood_keywords", keywords)

    return {
        "mood": detected_mood,
        "score": score,
        "keywords": keywords,
        "confidence": round(random.uniform(0.75, 0.95), 2),
    }


# ===========================================================================
# chibi_illustrator_agent tools
# ===========================================================================

# Mood → chibi art style hints for the stub
_CHIBI_MOOD_STYLES: dict[str, str] = {
    "happy": "sunny meadow background, flower crown, big sparkling eyes",
    "sad": "rainy window scene, small tears, cozy blanket",
    "anxious": "swirling thoughts backdrop, wide worried eyes, fidgeting hands",
    "grateful": "warm golden light, pressed hands, soft smile",
    "excited": "confetti explosion, jumping pose, star-filled eyes",
    "neutral": "cozy reading nook, peaceful expression, soft indoor lighting",
}


def generate_chibi_image(prompt: str) -> dict:
    """Generate a chibi-style illustration for the diary entry.

    Builds a chibi character image based on the provided mood-aware prompt.
    Returns a URL to the generated image.

    NOTE (Day 1): This is a STUB implementation. It returns a placeholder URL.
    On Day 2 this function will be replaced with a real MCP server call to
    an image generation API (e.g., Imagen via Vertex AI).

    Args:
        prompt: A descriptive image prompt including chibi style, mood cues,
            and scene details. Should reference kawaii/chibi aesthetic.

    Returns:
        A dict with keys:
          - image_url (str): URL to the generated chibi illustration.
          - prompt_used (str): The exact prompt sent to the image model.
          - model (str): The image generation model used.
          - status (str): "success" or "error".
    """
    # STUB: Return a realistic placeholder.
    # The URL format mimics what a real image generation API would return.
    # Day 2: Call MCP image server at MCP_IMAGE_SERVER_URL and return real URL.
    mcp_server_url = os.environ.get("MCP_IMAGE_SERVER_URL", "http://localhost:8080")

    # Store prompt in session memory for debugging / regeneration
    _session_memory.set("chibi_prompt", prompt)

    return {
        "image_url": "https://placeholder.chibi.art/sample.png",
        "prompt_used": prompt,
        "model": "stub-v1-day1",  # Day 2: will be "imagen-3" or similar
        "status": "success",
        "note": (
            f"STUB: Real image generation via MCP server at {mcp_server_url} "
            "will be connected on Day 2."
        ),
    }


# ===========================================================================
# memory_agent tools
# ===========================================================================

def save_entry(
    date: str,
    text: str,
    mood: str,
    mood_score: float,
    summary: str,
    chibi_url: str,
) -> dict:
    """Save a complete diary entry to long-term SQLite storage.

    Persists the diary entry with its mood classification, ≤50-word summary,
    and chibi illustration URL. Uses today's date as the entry date.

    Args:
        date: ISO-format date string (YYYY-MM-DD) for the diary entry.
        text: The full cleaned diary entry text.
        mood: Primary mood label (happy/sad/anxious/grateful/excited/neutral).
        mood_score: Mood intensity from 0.0 (mild) to 1.0 (intense).
        summary: A ≤50-word summary of the entry.
        chibi_url: URL to the generated chibi illustration.

    Returns:
        A dict with keys:
          - success (bool): True if the entry was saved successfully.
          - entry_id (int): The database row ID of the saved entry.
          - message (str): Human-readable confirmation or error message.
    """

    try:
        entry_id = _long_term_memory.save_entry_sync(
            date=date,
            raw_text=text,
            mood=mood,
            mood_score=float(mood_score),
            summary=summary,
            chibi_url=chibi_url,
        )
        return {
            "success": True,
            "entry_id": entry_id,
            "message": f"Diary entry saved successfully (ID: {entry_id}).",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "entry_id": -1,
            "message": f"Failed to save entry: {exc}",
        }


def get_recent_entries(limit: int) -> list:
    """Retrieve the most recent diary entries from long-term storage.

    Useful for providing the memory agent with recent context so it can
    detect mood trends or reference past events.

    Args:
        limit: Maximum number of recent entries to return (e.g., 7 for a week).

    Returns:
        A list of dicts, each containing: id, date, mood, mood_score,
        summary, chibi_url, created_at. Returns an empty list on error.
    """
    try:
        return _long_term_memory.get_entries_sync(limit=limit)
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc)}]


def search_entries(keyword: str) -> str:
    """Search diary entries for a keyword.

    Args:
        keyword: The keyword to search for.

    Returns:
        A formatted string of search results.
    """
    try:
        entries = _memory.search_entries_sync(keyword, limit=5)
        result = f'SEARCH_RESULTS for "{keyword}":\n\n'
        if not entries:
            result += "No results found."
        else:
            lines = []
            for entry in entries:
                lines.append(
                    f"- [{entry['date']}] {entry['mood']} ({entry['mood_score']}): {entry['summary']}"
                )
            result += "\n".join(lines)
        return result
    except Exception as exc:  # noqa: BLE001
        return f"Error searching entries: {exc}"


def get_mood_trend(days: int = 7) -> str:
    """Retrieve mood trend statistics over the last N days.

    Args:
        days: The number of days of history to include.

    Returns:
        A formatted string summarizing the mood trend.
    """
    try:
        trend_data = _memory.get_mood_trend_sync(days)
        result = (
            f"MOOD_TREND last {days} days:\n\n"
            f"Entries: {trend_data['total_entries']} | "
            f"Dominant: {trend_data['dominant_mood']} | "
            f"Avg score: {trend_data['average_score']}\n\n"
            "Daily: "
        )
        if not trend_data["trend"]:
            result += "No entries found."
        else:
            daily_strs = [
                f"{t['date']}: {t['mood']} ({t['score']})" for t in trend_data["trend"]
            ]
            result += ", ".join(daily_strs)
        return result
    except Exception as exc:  # noqa: BLE001
        return f"Error getting mood trend: {exc}"


def get_monthly_recap() -> str:
    """Retrieve a monthly mood recap.

    Returns:
        A formatted string of the monthly recap.
    """
    try:
        recap = _memory.get_monthly_recap_sync()
        result = (
            f"MONTHLY_RECAP:\n\n"
            f"Period: {recap['period']}\n"
            f"Entries: {recap['total_entries']} | "
            f"Dominant: {recap['dominant_mood']} | "
            f"Avg score: {recap['average_score']}\n\n"
            "Summaries:\n"
        )
        if not recap["entries"]:
            result += "No entries found."
        else:
            result += "\n".join(f"- {s}" for s in recap["entries"])
        return result
    except Exception as exc:  # noqa: BLE001
        return f"Error getting monthly recap: {exc}"


def get_streak() -> str:
    """Retrieve the current journaling streak.

    Returns:
        A formatted string summarizing the streak.
    """
    try:
        streak = _memory.get_streak_sync()
        return f"STREAK: {streak['current_streak_days']} day(s) | Last entry: {streak['last_entry_date']}"
    except Exception as exc:  # noqa: BLE001
        return f"Error getting streak: {exc}"
