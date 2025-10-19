"""Utilities for storing and retrieving conversation history."""
from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Dict, List

DATA_DIR = Path(__file__).resolve().parent / "data"
HISTORY_DIR = DATA_DIR / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

_LOCK = Lock()


def _history_path(session_id: str) -> Path:
    return HISTORY_DIR / f"{session_id}.json"


def get_history(session_id: str) -> List[Dict[str, str]]:
    """Return the stored messages for a session."""

    path = _history_path(session_id)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as history_file:
        return json.load(history_file)


def append_message(session_id: str, role: str, content: str) -> List[Dict[str, str]]:
    """Append a message to the session history and return the updated history."""

    with _LOCK:
        history = get_history(session_id)
        history.append({"role": role, "content": content})
        path = _history_path(session_id)
        with path.open("w", encoding="utf-8") as history_file:
            json.dump(history, history_file, ensure_ascii=False, indent=2)
    return history


def overwrite_history(session_id: str, messages: List[Dict[str, str]]) -> None:
    """Persist the provided message list for the session."""

    with _LOCK:
        path = _history_path(session_id)
        with path.open("w", encoding="utf-8") as history_file:
            json.dump(messages, history_file, ensure_ascii=False, indent=2)


def clear_history(session_id: str) -> None:
    """Remove history for a session if it exists."""

    with _LOCK:
        path = _history_path(session_id)
        if path.exists():
            path.unlink()
