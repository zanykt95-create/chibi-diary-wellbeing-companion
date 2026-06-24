"""
mcp_server/chibi_mcp_server.py

MCP Server for Chibi Diary — exposes chibi image generation as an MCP tool.

Run modes:
  stdio (for ADK MCPToolset): python -m mcp_server.chibi_mcp_server
  SSE   (for standalone demo): python -m mcp_server.chibi_mcp_server --sse

The ADK chibi_illustrator_agent connects to this server via StdioServerParameters,
so ADK manages the server lifecycle automatically.
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------
mcp = FastMCP("chibi-art-server")

# Read config from environment (never hardcode)
_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
_OUTPUT_DIR = os.environ.get("CHIBI_IMAGES_DIR", "./output/chibi_images")

# Lazy-init the Imagen client
_imagen_client = None


def _get_client():
    global _imagen_client
    if _imagen_client is None:
        from mcp_server.imagen_client import ImagenClient
        _imagen_client = ImagenClient(
            project=_PROJECT,
            location=_LOCATION,
            output_dir=_OUTPUT_DIR,
        )
    return _imagen_client


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def generate_chibi_image(prompt: str) -> dict:
    """Generate a chibi-style illustration from a descriptive prompt.

    Calls Vertex AI Imagen 3 to create a kawaii chibi character image
    based on the mood and scene description provided.

    Args:
        prompt: A descriptive chibi art prompt including mood, scene details,
                and aesthetic keywords (e.g., 'kawaii', 'pastel colours',
                'anime chibi style').

    Returns:
        A dict with keys:
          - image_path (str): Relative path to the generated PNG file.
          - prompt_used (str): The exact prompt sent to Imagen 3.
          - model (str): The Imagen model used.
          - status (str): 'success' or 'error'.
          - error (str): Error message if status is 'error', else empty string.
    """
    try:
        client = _get_client()
        image_path = client.generate(prompt)
        return {
            "image_path": image_path,
            "prompt_used": prompt,
            "model": "imagen-3.0-generate-001",
            "status": "success",
            "error": "",
        }
    except Exception as exc:
        return {
            "image_path": "",
            "prompt_used": prompt,
            "model": "imagen-3.0-generate-001",
            "status": "error",
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chibi Art MCP Server")
    parser.add_argument(
        "--sse",
        action="store_true",
        help="Run in SSE mode (HTTP server) instead of default stdio mode.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="SSE server host.")
    parser.add_argument("--port", type=int, default=8080, help="SSE server port.")
    args = parser.parse_args()

    if args.sse:
        print(f"Starting Chibi Art MCP Server (SSE) on {args.host}:{args.port}", file=sys.stderr)
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        # stdio mode — used by ADK MCPToolset
        mcp.run()
