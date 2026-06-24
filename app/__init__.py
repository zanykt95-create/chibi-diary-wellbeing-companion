"""
app/__init__.py

Chibi Diary app package initialiser.

ADK's CLI discovers the root agent by importing this package and looking for
`root_agent` at the package level. We re-export it here so both
`adk run app/` and `adk run app/orchestrator.py` work correctly.
"""

from app.orchestrator import root_agent  # noqa: F401  — re-exported for ADK discovery

__all__ = ["root_agent"]
