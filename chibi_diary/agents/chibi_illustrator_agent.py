"""
chibi_diary/agents/chibi_illustrator_agent.py

Chibi Illustrator Agent — Stage 3 of the Chibi Diary pipeline.

Connects to the real MCP server (mcp_server/chibi_mcp_server.py) via
McpToolset using stdio transport. ADK manages the MCP server lifecycle
automatically — no need to start the server manually.

McpToolset is a BaseToolset that can be passed directly in the Agent's tools
list. ADK lazily starts the MCP server subprocess on first tool invocation —
the module-level instantiation below does NOT spawn a subprocess at import time.

Note on env passthrough: _MCP_ENV provides only override values; the full
parent environment ({**os.environ, **_MCP_ENV}) is passed to the subprocess,
so GOOGLE_API_KEY and all other credentials are automatically inherited.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mcp import StdioServerParameters
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

# Project root so we can launch the MCP server as a module
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent)

# Environment to pass to the MCP server subprocess
_MCP_ENV = {
    "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
    "GOOGLE_CLOUD_LOCATION": os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    "GOOGLE_GENAI_USE_VERTEXAI": os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True"),
    "CHIBI_IMAGES_DIR": os.environ.get("CHIBI_IMAGES_DIR", "./output/chibi_images"),
}

_AGENT_INSTRUCTION = """
You are the Chibi Illustrator Agent for Chibi Diary. Your job is to create a
vivid, mood-appropriate chibi art prompt and generate an illustration.

Available context from earlier pipeline stages:
- Diary entry: {captured_entry}
- Mood report: {mood_report}

Steps:
1. Extract the mood, score, and keywords from the mood report.
2. Build a chibi art prompt following this formula:
   "A cute chibi character looking [emotion adjective], [1-2 scene details
   based on diary keywords], soft pastel colours, anime chibi style,
   gentle lighting, kawaii aesthetic"

   Examples by mood:
   - happy:    "A cute chibi character beaming with joy, surrounded by sparkles and sunflowers..."
   - sad:      "A cute chibi character with misty eyes, sitting under a soft rain at a window..."
   - anxious:  "A cute chibi character with wide eyes, clutching a comfort plush in a swirling..."
   - grateful: "A cute chibi character with hands pressed together, warm golden glow around them..."
   - excited:  "A cute chibi character jumping with stars in their eyes, confetti everywhere..."
   - neutral:  "A cute chibi character sitting peacefully in a cozy reading nook..."

3. Call `generate_chibi_image` with the prompt you built.
4. Respond with ONLY this line (no extra text):
   CHIBI_PATH: <image_path from tool response>

If the tool returns status='error', respond:
   CHIBI_PATH: error:<error message>

The result is read by the memory agent in the next stage.
"""

# ---------------------------------------------------------------------------
# McpToolset — connects to the chibi MCP server via stdio transport.
# ADK manages the server subprocess lifecycle automatically.
# ---------------------------------------------------------------------------
_chibi_mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.chibi_mcp_server"],
            cwd=_PROJECT_ROOT,
            env={**os.environ, **_MCP_ENV},
        ),
        timeout=60.0,  # Imagen 3 can take 20-40s — give it 60s
    )
)

# ---------------------------------------------------------------------------
# Chibi Illustrator Agent definition
# ---------------------------------------------------------------------------
chibi_illustrator_agent = Agent(
    name="chibi_illustrator_agent",
    model="gemini-2.5-flash",
    description=(
        "Generates a chibi-style illustration based on mood and diary content "
        "by calling the Imagen 3 MCP server."
    ),
    instruction=_AGENT_INSTRUCTION,
    tools=[_chibi_mcp_toolset],
    output_key="chibi_result",
)


def map_mood_to_chibi_prompt(mood: str) -> str:
    """Map a mood to a chibi style prompt.
    
    Args:
        mood: The detected mood (e.g. 'happy', 'sad').
        
    Returns:
        A prompt string containing appropriate style hints.
    """
    mood_prompts = {
        "happy": "A cute chibi character beaming with joy, smile, sunny, bright, surrounded by sparkles and sunflowers",
        "sad": "A cute chibi character with misty eyes, tears, sitting under a soft rain at a window, blue",
        "anxious": "A cute chibi character with wide eyes, clutching a comfort plush, worry",
        "grateful": "A cute chibi character with hands pressed together, warm golden glow, appreciate",
        "excited": "A cute chibi character jumping with stars in their eyes, confetti everywhere, thrilled",
        "neutral": "A cute chibi character sitting peacefully in a cozy reading nook, quiet",
    }
    return mood_prompts.get(mood.lower(), "A cute chibi character")

