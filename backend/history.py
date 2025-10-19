"""Utilities for storing and retrieving conversation history."""
from __future__ import annotations

import json
from datetime import datetime, timezone
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
        history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
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


def list_conversations() -> List[Dict[str, str]]:
    """Return summaries of stored conversations ordered by recency."""

    conversations: List[Dict[str, str]] = []
    for path in sorted(HISTORY_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        with path.open("r", encoding="utf-8") as history_file:
            messages = json.load(history_file)
        if not messages:
            continue

        last_user = next((msg for msg in reversed(messages) if msg.get("role") == "user"), None)
        last_assistant = next((msg for msg in reversed(messages) if msg.get("role") == "assistant"), None)
        timestamp = messages[-1].get("timestamp")
        if not timestamp:
            timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()

        conversations.append(
            {
                "id": path.stem,
                "question": (last_user or {}).get("content", ""),
                "answer": (last_assistant or {}).get("content", ""),
                "createdAt": timestamp,
            }
        )

    return conversations
