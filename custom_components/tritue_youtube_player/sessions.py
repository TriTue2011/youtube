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


def plays_item(attributes: dict[str, Any], item: dict[str, Any] | None,
               tracker: dict[str, Any] | None = None) -> bool:
    """Whether the speaker's reported media is this session's song.

    Right after a new song is sent the speaker still reports the previous song's
    position and duration for a few seconds; reading those as the new song's
    made the picture jump to the old second and could count the old song
    ending as the new one's.

    Issue #3 (30/09/2026): a speaker reporting OTHER content (TTS ``/api/tts_proxy/…``, another source) is not the
    session's song — before, any ``media_content_id`` that was not a player stream counted as the song, so a TTS
    announcement on an idle speaker "finished" the song and the next one started at 22:42. A TV's own YouTube app
    reports the video id itself, which still matches. A speaker reporting no ``media_content_id`` at all is only
    trusted while it never reported this session's stream (``tracker["luong_minh"]``)."""
    if not item:
        return True
    mcid = attributes.get("media_content_id")
    target = stream_target(mcid)
    item_id = str(item.get("id") or "")
    if target is None:
        if mcid:
            return bool(item_id) and str(mcid) in {item_id, str(item.get("url") or "")}
        return not (tracker or {}).get("luong_minh")
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
        if not plays_item(attributes, item, tracker):
            return False
        if stream_target(attributes.get("media_content_id")) is not None:
            tracker["luong_minh"] = True
        tracker["seen_playing"] = True
        tracker.setdefault("playing_since", now)
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
    # Speakers that report no media_duration (a camera speaker) use the song's own duration. Still unknown → an
    # idle speaker is NOT a finished song (issue #3: every Stop pressed on such a speaker skipped to the next song).
    duration = tracker.get("duration") or _number((item or {}).get("duration"))
    position = tracker.get("position")
    position_at = tracker.get("position_at")
    if position is None and tracker.get("playing_since") is not None:
        # Speaker that never reports its position: count from when it was first seen playing this song.
        position, position_at = 0.0, tracker["playing_since"]
    tracker.pop("playing_since", None)
    if not duration or position is None:
        return False
    elapsed = max(0.0, (now - position_at).total_seconds())
    if position + elapsed >= duration - END_TOLERANCE_SECONDS:
        return True
    tracker["dung_som"] = True        # stopped well before the end — the caller takes the speaker out of the session
    return False


def observe_interruption(
    tracker: dict[str, Any],
    state: str,
    attributes: dict[str, Any],
    now: datetime,
    item: dict[str, Any] | None = None,
) -> float | None:
    """Theo dõi loa dẫn bị CHEN (TTS, thông báo) giữa bài; trả GIÂY cần phát tiếp đúng một lần khi loa đọc xong.

    Chủ máy 30/09/2026: "đang phát nhạc, tts thì nhạc dừng không, đặc biệt youtube nữa … loa gg, loa cam, loa r1".
    Loa Google / R1 phát TTS là THAY luôn bài đang phát, không tự phát lại. Dấu hiệu chung mọi loa đều báo: đang
    phát LUỒNG của máy phát (``stream_target`` đọc được) rồi chuyển sang nội dung khác (``media_content_id`` lạ) —
    nhớ giây đang dở; nội dung lạ dứt (loa về idle/off/standby hay tạm dừng) thì phát tiếp. Loa tự quay về luồng
    của mình (loa camera tự phát tiếp sau thông báo) thì thôi, không làm gì.

    ``tracker`` dùng chung với ``observe_track``: khi đang bị chen, bên gọi KHÔNG đưa trạng thái vào
    ``observe_track`` (TTS dứt không phải là hết bài)."""
    mcid = attributes.get("media_content_id")
    target = stream_target(mcid)
    if target is not None:
        if plays_item(attributes, item, tracker):
            tracker.pop("chen_tu", None)             # đang (hoặc lại) phát đúng bài của phiên
            tracker["luong_minh"] = True
        return None
    if state in PLAYING_STATES and mcid and tracker.get("luong_minh") and "chen_tu" not in tracker:
        position = tracker.get("position")
        if position is None:
            return None
        elapsed = max(0.0, (now - tracker.get("position_at", now)).total_seconds())
        duration = tracker.get("duration")
        giay = position + elapsed
        if duration and giay >= duration - END_TOLERANCE_SECONDS:
            return None                               # gần hết bài: để chuyển bài như thường
        tracker["chen_tu"] = giay
        return None
    if "chen_tu" in tracker and (state in FINISHED_STATES or state == "paused"):
        tracker["luong_minh"] = False
        return tracker.pop("chen_tu")
    return None
