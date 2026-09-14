"""Playback sessions: one per group of speakers.

Pure helpers (no Home Assistant imports) so the rules run in the unit tests:
which sessions are active, the next/previous queue item, the compact form
shown on the entity, and how a speaker finishing a track is recognised.
"""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from typing import Any

FINISHED_STATES = {"idle", "off", "standby"}
PLAYING_STATES = {"playing", "buffering"}
# A speaker that stops this far before the end was stopped by someone, not by
# the track ending — don't jump to the next song.
END_TOLERANCE_SECONDS = 15
MAX_ATTRIBUTE_SESSIONS = 16
STREAM_TOKEN = re.compile(r"/api/stream/([A-Za-z0-9_-]+)\.[A-Za-z0-9_-]+")


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


def stream_target(media_content_id: Any) -> str | None:
    """Song a speaker is playing, read from the player's signed stream URL.

    The token's payload is plain base64 JSON ({exp, source, target}); only its
    signature is secret. None = not a stream from the player (a TV's own
    YouTube app, another source), so the song can't be told."""
    match = STREAM_TOKEN.search(str(media_content_id or ""))
    if not match:
        return None
    payload = match.group(1)
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (ValueError, TypeError):
        return None
    target = data.get("target") if isinstance(data, dict) else None
    return str(target) if target else None


def plays_item(attributes: dict[str, Any], item: dict[str, Any] | None) -> bool:
    """Whether the speaker's reported media is this session's song.

    Right after a new song is sent the speaker still reports the previous song's
    position and duration for a few seconds; reading those as the new song's
    made the picture jump to the old second and could count the old song
    ending as the new one's."""
    target = stream_target(attributes.get("media_content_id"))
    if target is None or not item:
        return True
    item_id = str(item.get("id") or "")
    return target in {item_id, str(item.get("url") or "")} or bool(item_id and item_id in target)


def observe_track(
    tracker: dict[str, Any],
    state: str,
    attributes: dict[str, Any],
    now: datetime,
    item: dict[str, Any] | None = None,
) -> bool:
    """Feed one speaker state; return True once when the track has finished.

    Finished = the speaker was seen playing, then went idle/off/standby near the
    end of the track. Pause never counts; a stop well before the end does not
    count either. Playing reports of another song than ``item`` are ignored."""
    if state in PLAYING_STATES:
        if not plays_item(attributes, item):
            return False
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
