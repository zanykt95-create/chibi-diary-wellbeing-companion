"""
chibi_diary/memory/session_memory.py

Short-term in-process session memory for Chibi Diary.

Design choice: We use a simple dict-based class rather than ADK's built-in
session state for tool-internal bookkeeping. ADK session state is designed for
inter-agent communication (via output_key / {state_key} injection); this class
serves as a lightweight scratch pad within a single pipeline invocation — for
example, storing the mood score so the `save_entry` tool can read it without
requiring the memory agent to receive it as a parameter.

Thread safety: Not thread-safe. Acceptable for a single-user prototype.
Upgrade to a thread-local or asyncio.local design for multi-user deployments.
"""

from __future__ import annotations

from typing import Any


class SessionMemory:
    """Lightweight in-memory key-value store for the current pipeline session.

    Provides simple get/set/clear semantics. Values are stored as plain Python
    objects (no serialization). Data is lost when the process exits.

    Usage:
        memory = SessionMemory()
        memory.set("mood", "happy")
        mood = memory.get("mood")          # "happy"
        all_data = memory.get_all()        # {"mood": "happy"}
        memory.clear()
    """

    def __init__(self) -> None:
        """Initialise an empty session memory store."""
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """Store a value under the given key.

        Args:
            key: The key to store the value under.
            value: Any Python object. Must be JSON-serializable if you intend
                to persist it later.
        """
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by key.

        Args:
            key: The key to look up.
            default: Value to return if the key is not present. Defaults to None.

        Returns:
            The stored value, or `default` if not found.
        """
        return self._store.get(key, default)

    def clear(self) -> None:
        """Remove all stored key-value pairs.

        Call at the start of each new diary session to avoid stale data
        bleeding into a fresh pipeline run.
        """
        self._store.clear()

    def get_all(self) -> dict[str, Any]:
        """Return a shallow copy of the entire session store.

        Returns:
            A dict containing all currently stored key-value pairs.
        """
        return dict(self._store)

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return f"SessionMemory({self._store!r})"
