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
    """Target chuẩn để phát một bài: URL trước, id sau.

    Máy phát chuẩn hoá được từ URL với youtube/facebook nhưng BẮT BUỘC URL đầy
    đủ với zing (`validate_zing_target`), nên thứ tự url-trước đúng với MỌI
    nguồn. Mọi đường phát (action, Assist, hàng đợi, next) đều phải qua đây
    thay vì tự chọn `id`/`url` theo thứ tự riêng (NV201: hai chỗ chọn id-trước
    làm bài Zing không phát được).
    """
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


#: Loa còn "giữ" bài: đang phát, tạm dừng (TTS chen giữa / Pause), đang nạp. "on" cho loa chỉ báo bật/tắt.
DANG_PHAT = frozenset({"playing", "paused", "buffering", "on"})


def loa_phat_luong(trang_thai: dict[str, tuple[str, dict[str, Any]]],
                   bo_qua: frozenset[str] | set[str] = frozenset()) -> list[str]:
    """Loa đang phát LUỒNG của máy phát (URL có ký ``/api/stream/<token>``), kể cả khi máy phát đã QUÊN phiên.

    06/10/2026, tái hiện trên loa camera thật: máy phát xoá phiên giữa bài (add-on dừng / máy phát khởi động lại) →
    thực thể YouTube báo idle, thẻ thấy «không có gì đang phát», nút Stop không gửi gì xuống loa — loa vẫn phát tiếp
    vì luồng còn chạy. Dò theo LUỒNG trên loa chứ không theo danh sách phiên thì không sót loa nào.
    ``trang_thai``: entity_id → (state, attributes); ``bo_qua``: thực thể của chính tích hợp."""
    return sorted(
        entity_id
        for entity_id, (state, attributes) in trang_thai.items()
        if entity_id not in bo_qua
        and state in DANG_PHAT
        and stream_target((attributes or {}).get("media_content_id")) is not None
    )


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
        tracker.pop("tam_dung_vi_tri", None)
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
    if state == "paused":
        # Tạm dừng: đóng băng vị trí bài ở lúc dừng. Không đóng băng thì thời gian nằm tạm dừng bị cộng vào «vị trí ước tính», rồi TTS/Assist
        # lên loa và dứt → idle → mã thấy «vị trí cũ + thời gian trôi ≥ độ dài bài» và nhảy sang bài kế (nhóm báo 28/10/2026: «bấm tạm
        # dừng, phát TTS, xong TTS nó next bài rồi phát tiếp»).
        if tracker.get("seen_playing") and "tam_dung_vi_tri" not in tracker:
            position, position_at = tracker.get("position"), tracker.get("position_at")
            if position is None and tracker.get("playing_since") is not None:
                position, position_at = 0.0, tracker["playing_since"]
            if position is not None and position_at is not None:
                tracker["tam_dung_vi_tri"] = position + max(0.0, (now - position_at).total_seconds())
            else:
                tracker["tam_dung_vi_tri"] = None
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
        if not duration:
            # Không biết thời lượng (ví dụ bài dài, nguồn không khai) thì không phân biệt được hết bài / luồng cắt / nút trên
            # loa. Báo cho nơi gọi quyết định (sang bài kế hoặc dừng hẳn) thay vì im lặng để phiên «playing» mà loa đã im.
            tracker["het_khong_ro"] = True
        return False
    if "tam_dung_vi_tri" in tracker:
        # Từng Tạm dừng rồi loa về idle (thường do TTS/Assist chen vào rồi dứt): vị trí là lúc tạm dừng, không cộng thời gian nằm im. Chưa tới cuối
        # bài thì đây KHÔNG phải hết bài và cũng không phải nút Stop: không nhảy bài, không gỡ loa khỏi phiên.
        vi_tri_dung = tracker.pop("tam_dung_vi_tri")
        return vi_tri_dung is not None and vi_tri_dung >= duration - END_TOLERANCE_SECONDS
    elapsed = max(0.0, (now - position_at).total_seconds())
    if position + elapsed >= duration - END_TOLERANCE_SECONDS:
        return True
    tracker["dung_som"] = True        # stopped well before the end — Stop thật (nút trên loa/remote hay trong Home Assistant)
    return False


#: Loa về idle/tạm dừng rồi nội dung lạ lên sóng trong khoảng này (giây) sau lúc ngừng phát luồng của mình thì vẫn là CHEN
#: giữa bài (một số loa, ví dụ R1 và loa camera, idle vài giây giữa luồng và TTS). Lâu hơn thì là người dùng đã dừng.
CHO_CHEN_SAU_NGUNG_GIAY = 15


def _ghi_nhan_luong_dang_phat(tracker: dict[str, Any], state: str, attributes: dict[str, Any], now: datetime,
                              item: dict[str, Any] | None) -> None:
    """Ghi «loa đang phát luồng của phiên» và lúc nó NGỪNG phát (idle/tạm dừng/tắt).

    Báo 28/10/2026: dừng nhạc rồi TTS ra loa thì TTS xong video đã dừng tự chạy lại: cờ `luong_minh` («từng phát luồng của
    mình») không hết hạn nên mọi nội dung lạ sau này đều bị coi là chen giữa bài. Chỉ được coi là chen khi loa VỪA ĐANG
    phát luồng của mình (xem ``_vua_phat_luong_minh``)."""
    if "chen_tu" in tracker:
        return                                        # đang bị chen: trạng thái của nội dung chen không đổi gì ở đây
    if state == "paused":
        # Người dùng CHỦ ĐỘNG tạm dừng (nhóm báo 28/10/2026: «pause nhạc rồi phát TTS/gọi Assist, xong nó tự phát tiếp nhạc, không giữ
        # trạng thái»). Khoảng ân hạn chỉ dành cho idle/tắt thoáng qua giữa luồng và TTS (R1, loa camera), không phải cho Tạm dừng:
        # đã tạm dừng thì nội dung lạ lên loa sau đó KHÔNG phải «chen giữa bài» và không được phát tiếp.
        tracker.pop("luong_dang", None)
        tracker.pop("luong_ngung_luc", None)
        return
    if state in PLAYING_STATES:
        if stream_target(attributes.get("media_content_id")) is not None and plays_item(attributes, item, tracker):
            tracker["luong_dang"] = True
            tracker.pop("luong_ngung_luc", None)
        return
    if tracker.pop("luong_dang", False):
        tracker["luong_ngung_luc"] = now


def _vua_phat_luong_minh(tracker: dict[str, Any], now: datetime) -> bool:
    if tracker.get("luong_dang"):
        return True
    ngung = tracker.get("luong_ngung_luc")
    return ngung is not None and (now - ngung).total_seconds() <= CHO_CHEN_SAU_NGUNG_GIAY


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
    _ghi_nhan_luong_dang_phat(tracker, state, attributes, now, item)
    if target is not None:
        if plays_item(attributes, item, tracker):
            tracker.pop("chen_tu", None)             # đang (hoặc lại) phát đúng bài của phiên
            tracker["luong_minh"] = True
        return None
    if state in PLAYING_STATES and mcid and _vua_phat_luong_minh(tracker, now) and "chen_tu" not in tracker:
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
        tracker.pop("luong_dang", None)
        tracker.pop("luong_ngung_luc", None)
        return tracker.pop("chen_tu")
    return None


_SESSION_QUEUES: dict[str, str] = {}


def attach_session_queue(session_id: Any, queue_key: Any) -> None:
    """Attach a queue key to an active playback session."""
    if session_id and queue_key:
        _SESSION_QUEUES[str(session_id)] = str(queue_key)


def session_queue_key(session: dict[str, Any] | None) -> str | None:
    """Get the queue key attached to this session."""
    if not isinstance(session, dict):
        return None
    session_id = session.get("session_id")
    if not session_id:
        return None
    return _SESSION_QUEUES.get(str(session_id))


def detach_session_queue(session_id: Any) -> None:
    """Detach queue key when a session ends."""
    if session_id:
        _SESSION_QUEUES.pop(str(session_id), None)
