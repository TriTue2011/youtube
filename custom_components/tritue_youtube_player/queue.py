"""Queue — the songs to play next, kept in Home Assistant storage.

The household has ONE queue (0.27.18+), identified by a random 12-character code
(``secrets.token_hex(6)``, generated once, stored in the queue document as ``{"id": ...}``).
Old per-speaker / per-device keys (``media_player.x``, ``device:<id>``) are still accepted
but ALL point at the same queue — the SPEAKERS that play it are chosen separately
(action's speaker field / the card's ticked speakers). The queue lives in ``.storage``
like pinned videos, so it survives reloads, restarts and integration updates.

Limitation: several speakers playing from the shared queue share ONE «current / played»
pointer — advancing on one speaker moves it for the others too.

When a song ends, ``advance_queue`` picks the next one — in order, or shuffled
among the songs not played yet — for the speakers (``advance.py``, with every
browser closed) and for a device (the card asks the view).

Pure helpers only (no Home Assistant imports) so they run in the unit tests.
"""

from __future__ import annotations

import random
import re
import secrets
from typing import Any, Callable

from .suggestions import FACEBOOK_ID, MAX_URL, VIDEO_ID, _text, _thumbnail

STORAGE_VERSION = 1
STORAGE_KEY = "tritue_youtube_player.queue"
MAX_ITEMS = 200
MAX_QUEUES = 300

#: Hàng đợi DUY NHẤT của nhà, mã ngẫu nhiên 12 ký tự (giống mã playlist). Khoá cũ theo loa/máy (`media_player.x`, `device:<mã>`) vẫn được nhận
#: nhưng đều trỏ về hàng đợi duy nhất này — loa PHÁT chọn riêng, không còn «hàng đợi của loa».
QUEUE_ID = re.compile(r"^[a-z0-9]{12}$")
QUEUE_KEY = re.compile(r"^([a-z0-9]{12}|media_player\.[a-z0-9_]+|device:[a-z0-9-]{8,64})$")
# Mã Zing theo khuôn rộng của máy phát (streaming.py): chữ hoa lẫn thường, 8–16 ký tự.
ZING_ID = re.compile(r"^[A-Za-z0-9]{8,16}$")
ITEM_ID = {"youtube": VIDEO_ID, "facebook": FACEBOOK_ID, "zing": ZING_ID}
UID = re.compile(r"^[a-f0-9]{8,32}$")
MODES = ("video", "audio")
ORDERS = ("sequential", "shuffle")
CONTENT_TYPES = ("video", "music")


def empty_queue() -> dict[str, Any]:
    return {"items": [], "current": None, "mode": "video", "order": "sequential", "played": []}


def normalize_item(value: Any) -> dict[str, Any] | None:
    """One queued song, or None when malformed. ``uid`` tells two copies apart."""
    if not isinstance(value, dict):
        return None
    source = _text(value.get("source"), 16).lower() or "youtube"
    pattern = ITEM_ID.get(source)
    item_id = _text(value.get("id") or value.get("video_id"), 32)
    if pattern is None or not pattern.fullmatch(item_id):
        return None
    uid = _text(value.get("uid"), 32)
    title = _text(value.get("title"))
    if not UID.fullmatch(uid) or not title:
        return None
    url = _text(value.get("url"), MAX_URL)
    if url and not url.startswith("https://"):
        url = ""
    try:
        seconds = int(value.get("duration_seconds", value.get("duration", 0)) or 0)
    except (TypeError, ValueError):
        seconds = 0
    kind = _text(value.get("media_content_type"), 16)
    return {
        "uid": uid,
        "source": source,
        "id": item_id,
        "url": url,
        "title": title,
        "artist": _text(value.get("artist") or value.get("channel")),
        "duration_seconds": max(0, min(seconds, 24 * 3600)),
        "thumbnail_url": _thumbnail(value.get("thumbnail_url") or value.get("thumbnail")),
        "media_content_type": kind if kind in CONTENT_TYPES else "",
    }


def normalize_queue(value: Any) -> dict[str, Any]:
    queue = empty_queue()
    if not isinstance(value, dict):
        return queue
    seen: set[str] = set()
    for candidate in value.get("items") or []:
        item = normalize_item(candidate)
        if item and item["uid"] not in seen:
            seen.add(item["uid"])
            queue["items"].append(item)
    queue["items"] = queue["items"][:MAX_ITEMS]
    uids = {item["uid"] for item in queue["items"]}
    current = value.get("current")
    queue["current"] = current if current in uids else None
    if value.get("mode") in MODES:
        queue["mode"] = value["mode"]
    if value.get("order") in ORDERS:
        queue["order"] = value["order"]
    queue["played"] = [uid for uid in dict.fromkeys(value.get("played") or []) if uid in uids]
    return queue


def new_queue_id() -> str:
    return secrets.token_hex(6)


def _merge_queues(queues: list[dict[str, Any]]) -> dict[str, Any]:
    """Gộp các hàng đợi cũ (mỗi loa/máy một cái) thành MỘT: bài nối tiếp nhau, bỏ bài trùng (nguồn + id); chế độ/thứ tự/bài hiện tại lấy từ
    hàng đợi có bài đầu tiên (ưu tiên cái đang có «bài hiện tại»)."""
    co_bai = [q for q in queues if q["items"]]
    if not co_bai:
        return queues[0] if queues else empty_queue()
    chinh = next((q for q in co_bai if q["current"]), co_bai[0])
    items: list[dict[str, Any]] = []
    seen_item: set[tuple[str, str]] = set()
    seen_uid: set[str] = set()
    for q in [chinh, *[x for x in co_bai if x is not chinh]]:
        for it in q["items"]:
            khoa = (it["source"], it["id"])
            if khoa in seen_item or it["uid"] in seen_uid or len(items) >= MAX_ITEMS:
                continue
            seen_item.add(khoa)
            seen_uid.add(it["uid"])
            items.append(it)
    uids = {it["uid"] for it in items}
    return {
        "items": items,
        "current": chinh["current"] if chinh["current"] in uids else None,
        "mode": chinh["mode"],
        "order": chinh["order"],
        "played": [u for u in chinh["played"] if u in uids],
    }


def normalize_document(value: Any) -> dict[str, Any]:
    """Tài liệu lưu: `{"id": <12 ký tự>, "queues": {<id>: hàng đợi}}`. Tài liệu cũ (khoá theo loa/máy) được gộp vào hàng đợi duy nhất."""
    queues = value.get("queues") if isinstance(value, dict) else None
    luu_id = value.get("id") if isinstance(value, dict) else None
    qid = luu_id if isinstance(luu_id, str) and QUEUE_ID.fullmatch(luu_id) else new_queue_id()
    chinh: dict[str, Any] | None = None
    cu: list[dict[str, Any]] = []
    for key, queue in (queues or {}).items() if isinstance(queues, dict) else []:
        if isinstance(key, str) and QUEUE_KEY.fullmatch(key) and len(cu) < MAX_QUEUES:
            q = normalize_queue(queue)
            if key == qid:
                chinh = q                      # hàng đợi mang mã chính làm gốc gộp
            else:
                cu.append(q)
    gop = _merge_queues(([chinh] if chinh else []) + cu)
    out: dict[str, Any] = {qid: gop} if (gop["items"] or gop != empty_queue()) else {}
    return {"id": qid, "queues": out}


def queue_key(value: Any) -> str:
    key = str(value or "")
    if not QUEUE_KEY.fullmatch(key):
        raise ValueError("invalid_queue_key")
    return key


def _chinh(document: dict[str, Any], key: str) -> str:
    """Mọi khoá hợp lệ đều trỏ về hàng đợi duy nhất của tài liệu (tài liệu thuần không có `id` thì giữ nguyên khoá — dùng cho test đơn vị)."""
    return document.get("id") or key


def get_queue(document: dict[str, Any], key: str) -> dict[str, Any]:
    return document["queues"].get(_chinh(document, key)) or empty_queue()


def _with_queue(document: dict[str, Any], key: str, queue: dict[str, Any]) -> dict[str, Any]:
    key = _chinh(document, key)
    queues = dict(document["queues"])
    if queue["items"]:
        queues[key] = queue
    else:
        # Hết bài thì bỏ hẳn bản ghi, nhưng giữ lựa chọn chế độ/thứ tự của người dùng.
        queues[key] = {**empty_queue(), "mode": queue["mode"], "order": queue["order"]}
        if queues[key] == empty_queue():
            queues.pop(key)
    if len(queues) > MAX_QUEUES:
        raise ValueError("too_many_queues")
    return {**document, "queues": queues}


def pick_next(queue: dict[str, Any], rng: random.Random | None = None) -> dict[str, Any] | None:
    """The song after ``current``: the next one in order, or a random one not
    played yet when shuffled. None = the queue is done."""
    items = queue["items"]
    if not items:
        return None
    if queue["order"] == "shuffle":
        played = set(queue["played"]) | {queue["current"]}
        left = [item for item in items if item["uid"] not in played]
        return (rng or random).choice(left) if left else None
    uids = [item["uid"] for item in items]
    position = uids.index(queue["current"]) + 1 if queue["current"] in uids else 0
    return items[position] if position < len(items) else None


def pick_prev(queue: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Bài TRƯỚC `current` (nút lùi bài): lần lượt = bài đứng trước; trộn = bài vừa
    phát trước bài này (lùi theo lịch sử). Trả (Queue mới, bài) — None = đã ở đầu."""
    items = queue["items"]
    uids = [item["uid"] for item in items]
    if queue["current"] not in uids:
        return queue, None
    if queue["order"] == "shuffle":
        lich_su = [u for u in queue["played"] if u in uids]
        if len(lich_su) < 2 or lich_su[-1] != queue["current"]:
            return queue, None
        truoc = lich_su[-2]
        # Bài vừa rời được trả lại cho lượt bốc ngẫu nhiên sau.
        return {**queue, "current": truoc, "played": lich_su[:-1]}, items[uids.index(truoc)]
    vi_tri = uids.index(queue["current"]) - 1
    if vi_tri < 0:
        return queue, None
    return _select(queue, uids[vi_tri]), items[vi_tri]


def _select(queue: dict[str, Any], uid: str) -> dict[str, Any]:
    return {**queue, "current": uid, "played": [*[u for u in queue["played"] if u != uid], uid]}


def advance_queue(
    document: dict[str, Any], key: str, rng: random.Random | None = None
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Move ``key``'s queue to its next song; return (document, that song or None)."""
    queue = get_queue(document, key)
    item = pick_next(queue, rng)
    if item is None:
        return document, None
    return _with_queue(document, key, _select(queue, item["uid"])), item


def apply_queue_change(
    document: dict[str, Any], payload: Any, new_uid: Callable[[], str]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Apply one card action; return (document, song to play or None).

    Raise ValueError with an error code on bad input."""
    if not isinstance(payload, dict):
        raise ValueError("invalid_request")
    # 0.27.19: không gửi «key» = hàng đợi DUY NHẤT của tài liệu (GET đã làm vậy từ 0.27.18; POST trước đây 400).
    ma_tai_lieu = document.get("id") if isinstance(document, dict) else None
    key = queue_key(payload.get("key") or ma_tai_lieu)
    queue = get_queue(document, key)
    action = payload.get("action")
    if action == "add":
        raw = payload.get("items")
        if not isinstance(raw, list) or not raw:
            raise ValueError("invalid_items")
        added = [normalize_item({**entry, "uid": new_uid()}) for entry in raw if isinstance(entry, dict)]
        if not added or None in added:
            raise ValueError("invalid_items")
        if len(queue["items"]) + len(added) > MAX_ITEMS:
            raise ValueError("queue_full")
        return _with_queue(document, key, {**queue, "items": [*queue["items"], *added]}), None
    if action == "remove":
        uid = payload.get("uid")
        if uid is None and "index" in payload:
            try:
                idx = int(payload["index"])
                if 0 <= idx < len(queue["items"]):
                    uid = queue["items"][idx]["uid"]
            except (TypeError, ValueError):
                pass
        uids = [item["uid"] for item in queue["items"]]
        if uid not in uids:
            raise ValueError("item_not_found")
        items = [item for item in queue["items"] if item["uid"] != uid]
        current = queue["current"]
        if current == uid:
            # Bài kế theo thứ tự vẫn là bài đứng sau bài vừa xoá.
            position = uids.index(uid)
            current = uids[position - 1] if position > 0 else None
        played = [u for u in queue["played"] if u != uid]
        return _with_queue(document, key, {**queue, "items": items, "current": current, "played": played}), None
    if action == "clear":
        return _with_queue(document, key, {**queue, "items": [], "current": None, "played": []}), None
    if action == "set":
        changed = dict(queue)
        if "mode" in payload:
            if payload["mode"] not in MODES:
                raise ValueError("invalid_mode")
            changed["mode"] = payload["mode"]
        if "order" in payload:
            if payload["order"] not in ORDERS:
                raise ValueError("invalid_order")
            if payload["order"] != queue["order"]:
                # Đổi thứ tự là bắt đầu một vòng mới: mọi bài lại được chọn.
                changed["played"] = [queue["current"]] if queue["current"] else []
            changed["order"] = payload["order"]
        return _with_queue(document, key, changed), None
    if action == "select":
        uid = payload.get("uid")
        if uid is None and "index" in payload:
            try:
                idx = int(payload["index"])
                if 0 <= idx < len(queue["items"]):
                    uid = queue["items"][idx]["uid"]
            except (TypeError, ValueError):
                pass
        item = next((entry for entry in queue["items"] if entry["uid"] == uid), None)
        if item is None:
            raise ValueError("item_not_found")
        return _with_queue(document, key, _select(queue, uid)), item
    if action == "next":
        return advance_queue(document, key)
    if action == "prev":
        moi, item = pick_prev(queue)
        return (_with_queue(document, key, moi), item) if item else (document, None)
    raise ValueError("invalid_action")
