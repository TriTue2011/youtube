"""Playback sessions: one per group of speakers.

Pure helpers (no Home Assistant imports) so the rules run in the unit tests:
which sessions are active, the next/previous queue item, the compact form
shown on the entity, and how a speaker finishing a track is recognised.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

FINISHED_STATES = {"idle", "off", "standby"}
PLAYING_STATES = {"playing", "buffering"}
# A speaker that stops this far before the end was stopped by someone, not by
# the track ending — don't jump to the next song.
END_TOLERANCE_SECONDS = 15
MAX_ATTRIBUTE_SESSIONS = 16


def controller_id(entry_id: str) -> str:
    return f"ha:{entry_id}"


def active_sessions(status: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Sessions playing on speakers, newest first.

    Player servers before sessions (add-on 0.6) only report ``session``; that one
    session is treated as ours when it has speakers."""
    status = status if isinstance(status, dict) else {}
    sessions = status.get("sessions")
    if not isinstance(sessions, list):
        legacy = status.get("session")
        sessions = [legacy] if isinstance(legacy, dict) else []
    return [
        session
        for session in sessions
        if isinstance(session, dict)
        and session.get("state") == "playing"
        and session.get("output_entity_ids")
    ]


def find_session(status: dict[str, Any] | None, session_id: str | None) -> dict[str, Any] | None:
    for session in active_sessions(status):
        if not session_id or session.get("session_id") == session_id:
            return session
    return None


def is_controlled_by(session: dict[str, Any], entry_id: str) -> bool:
    controller = str(session.get("controller") or "")
    return controller == controller_id(entry_id) or (not controller and "session_id" not in session)


def queue_item(session: dict[str, Any], step: int) -> tuple[int, dict[str, Any]] | None:
    """Return (index, item) ``step`` places from the current track, if any."""
    queue = session.get("queue") or {}
    items = queue.get("items") or []
    index = int(queue.get("index", -1)) + int(step)
    if int(queue.get("index", -1)) < 0 or not 0 <= index < len(items):
        return None
    item = items[index]
    if not isinstance(item, dict) or not (item.get("url") or item.get("id")):
        return None
    return index, item


def item_target(item: dict[str, Any]) -> str:
    return str(item.get("url") or item.get("id") or "")


def compact_sessions(status: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Small per-session summary for entity attributes (no queues)."""
    out = []
    for session in active_sessions(status)[:MAX_ATTRIBUTE_SESSIONS]:
        item = session.get("item") or {}
        queue = session.get("queue") or {}
        out.append(
            {
                "session_id": session.get("session_id"),
                "revision": session.get("revision"),
                "source": item.get("source"),
                "id": item.get("id"),
                "url": item.get("url"),
                "title": item.get("title"),
                "artist": item.get("artist"),
                "thumbnail": item.get("thumbnail"),
                "duration": item.get("duration"),
                "output_entity_ids": list(session.get("output_entity_ids") or []),
                "queue_index": queue.get("index", -1),
                "queue_size": len(queue.get("items") or []),
                "auto_advance": session.get("auto_advance", True),
            }
        )
    return out


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def observe_track(
    tracker: dict[str, Any],
    state: str,
    attributes: dict[str, Any],
    now: datetime,
) -> bool:
    """Feed one speaker state; return True once when the track has finished.

    Finished = the speaker was seen playing, then went idle/off/standby near the
    end of the track. Pause never counts; a stop well before the end does not
    count either."""
    if state in PLAYING_STATES:
        tracker["seen_playing"] = True
        position = _number(attributes.get("media_position"))
        if position is not None:
            updated = attributes.get("media_position_updated_at")
            if isinstance(updated, str):
                try:
                    updated = datetime.fromisoformat(updated)
                except ValueError:
                    updated = None
            tracker["position"] = position
            tracker["position_at"] = updated if isinstance(updated, datetime) else now
        duration = _number(attributes.get("media_duration"))
        if duration:
            tracker["duration"] = duration
        return False
    if state not in FINISHED_STATES or not tracker.get("seen_playing"):
        return False
    tracker["seen_playing"] = False
    duration = tracker.get("duration")
    position = tracker.get("position")
    if not duration or position is None:
        return True
    elapsed = max(0.0, (now - tracker["position_at"]).total_seconds())
    return position + elapsed >= duration - END_TOLERANCE_SECONDS
