"""
chibi_diary/orchestrator.py

Root orchestrator agent for Chibi Diary & Wellbeing Companion.

ADK 2.x: using Workflow (replaces deprecated SequentialAgent)

Architecture decision: We wire the four specialist sub-agents into a deterministic pipeline rather than relying on LLM-based routing.
This gives us predictable, observable behaviour — every diary entry always goes through all four stages in the same order.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# ADK 2.x: using Workflow (replaces deprecated SequentialAgent)
try:
    from google.adk.agents import Workflow as SequentialAgent
except ImportError:
    from google.adk.agents import SequentialAgent  # fallback for older ADK

# Load .env before any credential-dependent import.
# This must happen before Agent instantiation so the model can authenticate.
load_dotenv()

# ---------------------------------------------------------------------------
# Import the four specialist sub-agents.
# Each module exposes a module-level Agent variable named after the agent.
# ---------------------------------------------------------------------------
from chibi_diary.agents.capture_agent import capture_agent
from chibi_diary.agents.chibi_illustrator_agent import chibi_illustrator_agent
from chibi_diary.agents.memory_agent import memory_agent
from chibi_diary.agents.mood_analysis_agent import mood_analysis_agent

# ---------------------------------------------------------------------------
# Routing callbacks — purely for observability (no control-flow effect).
# These print statements let us see which agent is being invoked in the logs.
# ---------------------------------------------------------------------------

def _log_pipeline_start() -> None:
    """Log that the orchestrator has started routing to sub-agents."""
    print("\n" + "=" * 60)
    print("🎀  Chibi Diary Orchestrator — pipeline starting")
    print("=" * 60)
    print("  [1/4] → capture_agent          (validate & clean entry)")
    print("  [2/4] → mood_analysis_agent     (detect emotion & intensity)")
    print("  [3/4] → chibi_illustrator_agent (generate chibi art via MCP)")
    print("  [4/4] → memory_agent            (save to SQLite)")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Root SequentialAgent
#
# Why SequentialAgent instead of a plain LlmAgent with sub_agents?
# SequentialAgent guarantees deterministic execution order — all four agents
# always run in sequence, regardless of what the LLM might decide.
# An LlmAgent with sub_agents would use the model to *choose* which sub-agent
# to call, which is non-deterministic and inappropriate for a save-everything
# journaling pipeline.
# ---------------------------------------------------------------------------
# ADK 2.x uses Workflow; older versions used SequentialAgent.
# The try/import above aliased whichever is available to SequentialAgent.
root_agent = SequentialAgent(
    name="chibi_diary_orchestrator",
    description=(
        "Chibi Diary orchestrator: accepts a daily diary entry and sequentially "
        "routes it through capture, mood analysis, chibi-art generation (Imagen 3 "
        "via MCP), and memory persistence."
    ),
    sub_agents=[
        capture_agent,            # Stage 1: validate & clean
        mood_analysis_agent,      # Stage 2: emotion detection
        chibi_illustrator_agent,  # Stage 3: chibi art via MCP
        memory_agent,             # Stage 4: persist to SQLite
    ],
)

# ---------------------------------------------------------------------------
# Log the pipeline topology on import (visible when `adk run` starts up).
# ---------------------------------------------------------------------------
_log_pipeline_start()
