"""Search keywords and pinned videos the household curates, kept in storage.

The card ships a fixed list of search tags and suggestion groups. Every home
listens to something different, so the owner can add their own keywords and pin
videos they play often. The list lives in ``.storage`` rather than in each
card's YAML, so it is shared by every dashboard and every device, and adding or
removing a card never loses it.

Pure helpers only (no Home Assistant imports) so they run in the unit tests,
mirroring ``hidden_players.py``.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

STORAGE_VERSION = 1
STORAGE_KEY = "tritue_youtube_player.suggestions"

MAX_TAGS = 40
MAX_GROUPS = 20
MAX_SONGS_PER_GROUP = 50
MAX_TEXT = 120
MAX_URL = 500

# YouTube video ids are a fixed 11-character alphabet; anything else is refused
# rather than stored and played back at whoever opens the card.
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
# Facebook video ids are a plain run of digits — a different shape, so each source
# gets its own pattern instead of one loose pattern that would let either through.
FACEBOOK_ID = re.compile(r"^[0-9]{5,25}$")
#: Nguồn ghim được. Bản ghi cũ không có trường này nên mặc định là YouTube — đúng
#: những gì đã lưu trước khi có Facebook, không phải đoán.
PINNABLE_SOURCES = ("youtube", "facebook")
GROUP_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


def _text(value: Any, limit: int = MAX_TEXT) -> str:
    """Return a trimmed single-line string, capped, or '' when unusable."""
    if not isinstance(value, str):
        return ""
    cleaned = " ".join(value.split())
    return cleaned[:limit]


def _thumbnail(value: Any) -> str:
    """Only plain http(s) thumbnails; no data:, no javascript:, no credentials."""
    url = _text(value, MAX_URL)
    if not url.startswith(("http://", "https://")):
        return ""
    return url


def normalize_song(value: Any) -> dict[str, Any] | None:
    """Return one pinned video, or None when it is malformed."""
    if not isinstance(value, dict):
        return None
    source = _text(value.get("source"), 16).lower() or "youtube"
    if source not in PINNABLE_SOURCES:
        return None
    video_id = _text(value.get("video_id") or value.get("id"), 32)
    # Mỗi nguồn một khuôn riêng: mã Facebook là chuỗi số, mã YouTube là 11 ký tự.
    # Dùng một khuôn lỏng cho cả hai là mở cửa cho mã rác của nguồn kia lọt vào.
    if not (FACEBOOK_ID if source == "facebook" else VIDEO_ID).fullmatch(video_id):
        return None
    title = _text(value.get("title"))
    if not title:
        return None
    duration = value.get("duration_seconds", value.get("duration", 0))
    try:
        seconds = int(duration)
    except (TypeError, ValueError):
        seconds = 0
    return {
        "id": video_id,
        "video_id": video_id,
        "source": source,
        "title": title,
        "artist": _text(value.get("artist") or value.get("channel")),
        "duration_seconds": max(0, min(seconds, 24 * 3600)),
        "thumbnail_url": _thumbnail(value.get("thumbnail_url") or value.get("thumbnail")),
    }


def normalize_group(value: Any) -> dict[str, Any] | None:
    """Return one keyword group with its pinned videos, or None when malformed."""
    if not isinstance(value, dict):
        return None
    group_id = _text(value.get("id"), 32).lower().replace(" ", "-")
    name = _text(value.get("name"))
    if not GROUP_ID.fullmatch(group_id) or not name:
        return None
    songs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in value.get("songs") or []:
        song = normalize_song(candidate)
        if song and song["id"] not in seen:
            seen.add(song["id"])
            songs.append(song)
    return {
        "id": group_id,
        "name": name,
        "icon": _text(value.get("icon"), 48) or "mdi:music",
        "songs": songs[:MAX_SONGS_PER_GROUP],
    }


def normalize_suggestions(value: Any) -> dict[str, Any]:
    """Return the stored document with anything malformed dropped."""
    if not isinstance(value, dict):
        return {"tags": [], "groups": [], "seeded": False}
    # Phải đúng là list. Nhận bừa rồi lặp qua một chuỗi sẽ tách nó thành TỪNG KÝ TỰ:
    # {"tags": "abc"} biến thành ["a", "b", "c"] chứ không bị loại.
    raw_tags = value.get("tags")
    raw_groups = value.get("groups")
    if not isinstance(raw_tags, list):
        raw_tags = []
    if not isinstance(raw_groups, list):
        raw_groups = []
    tags: list[str] = []
    for candidate in raw_tags:
        tag = _text(candidate)
        if tag and tag not in tags:
            tags.append(tag)
    groups: list[dict[str, Any]] = []
    ids: set[str] = set()
    for candidate in raw_groups:
        group = normalize_group(candidate)
        if group and group["id"] not in ids:
            ids.add(group["id"])
            groups.append(group)
    return {
        "tags": tags[:MAX_TAGS],
        "groups": groups[:MAX_GROUPS],
        # Đã nạp danh sách mặc định vào kho lần đầu hay chưa. Từ lúc nạp xong, KHO LÀ
        # NGUỒN DUY NHẤT — nhờ vậy xoá là xoá thật khỏi dữ liệu, không cần danh sách
        # ẩn nào và không để lại dấu vết.
        "seeded": bool(value.get("seeded")),
    }


def apply_suggestion_change(current: dict[str, Any], payload: Any) -> dict[str, Any]:
    """Apply one edit and return the new document; raise ValueError on bad input.

    Actions mirror the playlists view the card already speaks to:
    ``add_tag`` / ``remove_tag`` (``text``), ``add_group`` / ``remove_group``
    (``id``, ``name``, ``icon``) and ``pin_song`` / ``unpin_song``
    (``id`` plus ``item``/``video_id``).
    """
    if not isinstance(payload, dict):
        raise ValueError("invalid_request")
    action = payload.get("action")
    document = normalize_suggestions(current)
    tags: list[str] = document["tags"]
    groups: list[dict[str, Any]] = document["groups"]

    if action == "seed":
        # Nạp danh sách mặc định vào kho ĐÚNG MỘT LẦN.
        if document["seeded"]:
            # Đã nạp rồi thì không nạp lại — nếu không, xoá sạch xong lần tải sau lại
            # thấy mọi thứ quay về, tức xoá không có tác dụng thật.
            return document
        # GỘP, tuyệt đối không ghi đè. Kho có thể ĐÃ CÓ dữ liệu trước lần nạp đầu:
        # nhà tự thêm từ khoá ở bản cũ (khi chưa có cờ seeded). Ghi đè là xoá mất
        # công của họ — đo trên máy chủ nhà thấy đúng tình huống này: tags đã có
        # một từ khoá tự thêm mà seeded thì chưa có.
        mac_dinh = normalize_suggestions({
            "tags": payload.get("tags"),
            "groups": payload.get("groups"),
        })
        da_co_id = {group["id"] for group in document["groups"]}
        return normalize_suggestions({
            "tags": document["tags"]
            + [tag for tag in mac_dinh["tags"] if tag not in document["tags"]],
            "groups": document["groups"]
            + [g for g in mac_dinh["groups"] if g["id"] not in da_co_id],
            "seeded": True,
        })

    if action == "add_tag":
        tag = _text(payload.get("text"))
        if not tag:
            raise ValueError("invalid_text")
        if tag not in tags:
            if len(tags) >= MAX_TAGS:
                raise ValueError("too_many_tags")
            tags.append(tag)
        return {**document, "tags": tags, "groups": groups}

    if action == "remove_tag":
        tag = _text(payload.get("text"))
        if not tag:
            raise ValueError("invalid_text")
        # Xoá THẬT khỏi dữ liệu, không ghi lại dấu vết ở đâu cả.
        return {**document, "tags": [item for item in tags if item != tag]}

    if action == "add_group":
        group = normalize_group(
            {
                "id": payload.get("id") or _slug(payload.get("name")),
                "name": payload.get("name"),
                "icon": payload.get("icon"),
                "songs": [],
            }
        )
        if group is None:
            raise ValueError("invalid_group")
        if any(existing["id"] == group["id"] for existing in groups):
            raise ValueError("group_exists")
        if len(groups) >= MAX_GROUPS:
            raise ValueError("too_many_groups")
        groups.append(group)
        return {**document, "tags": tags, "groups": groups}

    if action == "remove_group":
        group_id = _text(payload.get("id"), 32)
        if not group_id:
            raise ValueError("invalid_group")
        # Xoá THẬT cả mục và mọi video đã gắn trong đó; không giữ lại dấu vết.
        return {**document, "groups": [g for g in groups if g["id"] != group_id]}

    if action in ("pin_song", "unpin_song"):
        group_id = _text(payload.get("id"), 32)
        target = next((item for item in groups if item["id"] == group_id), None)
        if target is None:
            raise ValueError("unknown_group")
        if action == "unpin_song":
            video_id = _text(payload.get("video_id"), 32)
            target["songs"] = [s for s in target["songs"] if s["id"] != video_id]
            return {**document, "tags": tags, "groups": groups}
        song = normalize_song(payload.get("item"))
        if song is None:
            raise ValueError("invalid_song")
        if any(existing["id"] == song["id"] for existing in target["songs"]):
            return {**document, "tags": tags, "groups": groups}
        if len(target["songs"]) >= MAX_SONGS_PER_GROUP:
            raise ValueError("too_many_songs")
        target["songs"].append(song)
        return {**document, "tags": tags, "groups": groups}

    raise ValueError("unknown_action")


def _slug(value: Any) -> str:
    """Build a group id from its name when the caller did not supply one.

    Vietnamese names must lose their diacritics first. Without this, every marked
    vowel falls outside ``[a-z0-9]`` and collapses to a hyphen: "Nhạc tối" becomes
    "nh-c-t-i" — unreadable, and two different names can land on the same id and be
    refused with ``group_exists`` for no reason the owner can see.
    """
    text = _text(value, 64).lower().replace("đ", "d")
    stripped = "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if not unicodedata.combining(char)
    )
    slug = re.sub(r"[^a-z0-9]+", "-", stripped).strip("-")
    return slug[:32]
