"""Pure helpers for the Assist (LLM) music tools — no Home Assistant imports.

Assist users speak or type speaker names loosely ("phòng khách và bếp", "loa 2",
"tất cả"), so speakers are matched without diacritics or case, by number in the
last listed order, by entity id, or all at once.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

ALL_WORDS = {"tat ca", "tat ca loa", "moi loa", "all", "everywhere", "ca nha", "toan bo"}
SPLIT = re.compile(r"\s*(?:,|;|\+|&|\bva\b|\band\b)\s*")
SEARCH_LIMIT = 10


def fold(text: Any) -> str:
    text = unicodedata.normalize("NFD", str(text or "")).replace("đ", "d").replace("Đ", "D")
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text).strip().lower()


def format_duration(seconds: Any) -> str:
    try:
        value = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return ""
    hours, rest = divmod(value, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def numbered_results(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "so": number,
            "ten": str(item.get("title") or item.get("id") or ""),
            "kenh": str(item.get("channel") or item.get("artist") or ""),
            "thoi_luong": format_duration(item.get("duration")),
        }
        for number, item in enumerate(items[:SEARCH_LIMIT], 1)
    ]


SAFE_INT_PATTERN = re.compile(r"^[0-9]{1,4}$")


def parse_safe_integer(value: Any, min_val: int = 1, max_val: int = 1000) -> int | None:
    """Safely parse an integer bounded by min_val and max_val, rejecting non-ASCII digits, booleans, and giant numbers."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        val = value
    elif isinstance(value, str):
        s = value.strip()
        if not SAFE_INT_PATTERN.fullmatch(s):
            return None
        val = int(s)
    else:
        return None
    if min_val <= val <= max_val:
        return val
    return None


def match_speakers(query: Any, speakers: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    """Return (entity_ids, unmatched words). ``speakers`` = [{entity_id, name}] in listed order."""
    text = fold(query)
    if not text or text in ALL_WORDS:
        return [speaker["entity_id"] for speaker in speakers], []
    chosen: list[str] = []
    missing: list[str] = []
    for part in [p for p in SPLIT.split(text) if p]:
        # "loa 2", "tivi LG": try the whole phrase first (a name may start with
        # "Tivi"), then without the leading device word.
        short = re.sub(r"^(loa|tivi|ti vi|man hinh)\s+", "", part).strip()
        found = None
        for attempt in dict.fromkeys(x for x in (part, short) if x):
            idx = parse_safe_integer(attempt, min_val=1, max_val=len(speakers))
            if idx is not None:
                found = speakers[idx - 1]["entity_id"]
            else:
                found = next((speaker["entity_id"] for speaker in speakers
                              if attempt in {speaker["entity_id"], fold(speaker["name"])}
                              or (len(attempt) >= 3 and attempt in fold(speaker["name"]))), None)
            if found:
                break
        if found is None:
            missing.append(part)
        elif found not in chosen:
            chosen.append(found)
    return chosen, missing


def match_playlist(query: Any, playlists: list[dict[str, Any]]) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Find a playlist by 1-based number, exact id, or loosely matched name.

    Returns a single playlist dict if exactly one matches, a list of candidate dicts
    if multiple match, or None if none match.
    """
    if not query or not playlists:
        return None
    idx = parse_safe_integer(query, min_val=1, max_val=len(playlists))
    if idx is not None:
        return playlists[idx - 1]
    raw = str(query).strip()
    for p in playlists:
        if str(p.get("id") or "") == raw:
            return p
    f_q = fold(raw)
    if not f_q:
        return None
    exact_matches = [p for p in playlists if fold(p.get("name") or "") == f_q]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        return exact_matches
    sub_matches = [p for p in playlists if f_q in fold(p.get("name") or "")]
    if len(sub_matches) == 1:
        return sub_matches[0]
    if len(sub_matches) > 1:
        return sub_matches
    return None


def format_playlists(playlists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format household playlists numbered 1..SEARCH_LIMIT for Assist."""
    return [
        {
            "so": number,
            "id": str(p.get("id") or ""),
            "ten": str(p.get("name") or p.get("id") or ""),
            "so_bai": len(p.get("items") or []),
        }
        for number, p in enumerate(playlists[:SEARCH_LIMIT], 1)
    ]


def format_queue(queue: dict[str, Any]) -> dict[str, Any]:
    """Format queue state and numbered items for Assist."""
    items = queue.get("items") or []
    current = queue.get("current")
    return {
        "tong_so": len(items),
        "che_do": "video" if queue.get("mode") == "video" else "audio",
        "thu_tu": "tron_bai" if queue.get("order") == "shuffle" else "lan_luot",
        "bai_hat": [
            {
                "so": idx,
                "ten": str(item.get("title") or item.get("id") or ""),
                "ca_si": str(item.get("artist") or item.get("channel") or ""),
                "thoi_luong": format_duration(item.get("duration_seconds", item.get("duration"))),
                "dang_phat": item.get("uid") == current,
            }
            for idx, item in enumerate(items[:SEARCH_LIMIT], 1)
        ],
    }


def match_queue_item(query: Any, queue: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Find a queued item by 1-based number, uid, or loosely matched title.

    Returns a single item dict if exactly one matches, a list of candidate dicts
    if multiple match, or None if none match.
    """
    items = queue.get("items") or []
    if not query or not items:
        return None
    idx = parse_safe_integer(query, min_val=1, max_val=len(items))
    if idx is not None:
        return items[idx - 1]
    raw = str(query).strip()
    for item in items:
        if str(item.get("uid") or "") == raw:
            return item
    f_q = fold(raw)
    if not f_q:
        return None
    exact_matches = [item for item in items if fold(item.get("title") or "") == f_q]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        return exact_matches
    sub_matches = [item for item in items if f_q in fold(item.get("title") or "")]
    if len(sub_matches) == 1:
        return sub_matches[0]
    if len(sub_matches) > 1:
        return sub_matches
    return None


PLAYLIST_SOURCES = ("kho", "youtube")
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
MAX_URL_LENGTH = 2048

from .suggestions import VIDEO_ID


def extract_item_id(target: Any, source: str = "youtube") -> str | None:
    """Validate and extract clean YouTube video id from video id or URL."""
    if not target or not isinstance(target, (str, int)):
        return None
    raw = str(target).strip()
    if source != "youtube":
        return None
    if len(raw) > MAX_URL_LENGTH or any(char.isspace() for char in raw):
        return None
    if ".." in raw:
        return None
    if VIDEO_ID.fullmatch(raw):
        return raw
    try:
        from urllib.parse import parse_qs, urlsplit
        parsed = urlsplit(raw)
    except Exception:
        return None
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.username or parsed.password:
        return None
    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        return None
    if host == "youtu.be":
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if parts and VIDEO_ID.fullmatch(parts[0]):
            return parts[0]
        return None
    if parsed.path == "/watch":
        vid = parse_qs(parsed.query).get("v", [""])[0]
        if VIDEO_ID.fullmatch(vid):
            return vid
        return None
    if parsed.path.startswith(("/shorts/", "/embed/", "/live/")):
        vid = parsed.path.rstrip("/").rsplit("/", 1)[-1]
        if VIDEO_ID.fullmatch(vid):
            return vid
        return None
    return None


YOUTUBE_PLAYLIST_ID = re.compile(r"^(PL|UU|FL|RD|OLAK5uy_)[A-Za-z0-9_-]{10,64}$")


def is_valid_youtube_playlist(target: Any) -> bool:
    """Validate YouTube playlist id or playlist URL."""
    if not target or not isinstance(target, str):
        return False
    raw = target.strip()
    if len(raw) > MAX_URL_LENGTH or any(char.isspace() for char in raw):
        return False
    if ".." in raw:
        return False
    if YOUTUBE_PLAYLIST_ID.fullmatch(raw):
        return True
    try:
        from urllib.parse import parse_qs, urlsplit
        parsed = urlsplit(raw)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        return False
    list_id = parse_qs(parsed.query).get("list", [""])[0]
    return bool(YOUTUBE_PLAYLIST_ID.fullmatch(list_id))
