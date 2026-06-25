"""
chibi_diary/agents/capture_agent.py

Capture Agent — Stage 1 of the Chibi Diary pipeline.

Responsibility: Receive the raw diary entry from the user, validate that it
is non-empty and meaningful, strip excess whitespace, and pass the cleaned
text downstream via ADK session state.

Why a separate validation agent?
  Keeping validation as an explicit, isolated stage means we can add richer
  checks later (e.g., language detection, profanity filtering, minimum word
  count) without touching the other agents.
"""

from __future__ import annotations

import re
from collections import deque
from datetime import datetime, timezone
from google.adk.agents import Agent
from chibi_diary.tools.placeholder_tools import validate_entry


# ---------------------------------------------------------------------------
# Security Features
# ---------------------------------------------------------------------------

SECURITY_AUDIT_LOG: deque = deque(maxlen=1000)  # bounded audit log — keeps last 1000 events

def log_security_event(entry_preview: str, flags: list[str]):
    """Log suspicious inputs for audit trail."""
    SECURITY_AUDIT_LOG.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry_preview": entry_preview[:50] + "..." if len(entry_preview) > 50 else entry_preview,
        "flags": flags
    })


class InputSanitizer:
    MAX_ENTRY_LENGTH = 2000  # characters
    BLOCKED_PATTERNS = [
        r"(?i)(ignore (previous|above|all) instructions?)",
        r"(?i)(you are now|pretend you are|act as)",
        r"(?i)(system prompt|jailbreak)",
        r"<script[^>]*>",
        r"(?i)(DROP TABLE|SELECT \*|INSERT INTO)",  # basic SQL injection
    ]
    
    @staticmethod
    def sanitize(text: str) -> tuple[str, list[str]]:
        """
        Returns (sanitized_text, list_of_warnings).
        - Truncates to MAX_ENTRY_LENGTH
        - Detects and flags prompt injection patterns
        - Strips HTML tags
        - Returns warnings list (non-empty if suspicious content found)
        """
        # Strip HTML tags
        clean_text = re.sub(r"<[^>]*>", "", text)
        
        # Check warnings
        warnings = []
        for pattern in InputSanitizer.BLOCKED_PATTERNS:
            if re.search(pattern, text):
                warnings.append(f"Suspicious pattern matched: {pattern}")
                
        # Truncate
        if len(clean_text) > InputSanitizer.MAX_ENTRY_LENGTH:
            clean_text = clean_text[:InputSanitizer.MAX_ENTRY_LENGTH]
            
        if warnings:
            log_security_event(text, warnings)
            
        return clean_text, warnings


def sanitize_input(text: str) -> dict:
    """Sanitize the raw diary entry to prevent prompt injection and SQL injection.

    Args:
        text: The raw diary entry text.

    Returns:
        A dict with keys:
          - sanitized_text (str): The clean, truncated text.
          - security_flags (list[str]): List of warnings (empty if clean).
    """
    sanitized, warnings = InputSanitizer.sanitize(text)
    return {
        "sanitized_text": sanitized,
        "security_flags": warnings,
    }


# ---------------------------------------------------------------------------
# Capture Agent definition
# ---------------------------------------------------------------------------
capture_agent = Agent(
    name="capture_agent",
    model="gemini-2.5-flash",
    description="Receives, sanitizes, and validates the raw diary text entry from the user.",
    instruction="""
You are the Capture Agent for Chibi Diary. Your only job is to receive a diary
entry, sanitize it, validate it, and pass the cleaned version forward.

Steps:
1. Call the `sanitize_input` tool with the user's raw diary text.
2. Remember if the tool returned any `security_flags`.
3. Call the `validate_entry` tool with the `sanitized_text` returned by `sanitize_input`.
4. If `validate_entry` returns `valid: false`, respond with a warm, encouraging message
   asking the user to write a bit more (e.g., "Write at least a sentence!").
5. If `validate_entry` returns `valid: true`, your final response MUST be:
   - If the `security_flags` list was empty: output ONLY the `cleaned_text` value and absolutely nothing else (no commentary, no markdown).
   - If the `security_flags` list was not empty: output a JSON block containing keys "captured_entry" (the `cleaned_text`) and "security_flags" (the list of warnings).

Important: Your output will be read by the next agent in the pipeline, so keep
your response clean.
""",
    tools=[sanitize_input, validate_entry],
    # output_key writes the agent's final text response into session state
    # under the key "captured_entry". The next agent can read it via {captured_entry}.
    output_key="captured_entry",
)

