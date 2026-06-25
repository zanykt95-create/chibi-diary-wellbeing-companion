"""
chibi_diary/__init__.py

Chibi Diary app package initialiser.

ADK's CLI discovers the root agent by importing this package and looking for
`root_agent` at the package level. We re-export it here so both
`adk run chibi_diary/` and `adk run chibi_diary/orchestrator.py` work correctly.
"""

from chibi_diary.orchestrator import root_agent  # noqa: F401  — re-exported for ADK discovery

__all__ = ["root_agent"]
