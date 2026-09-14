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
            if attempt.isdigit() and 1 <= int(attempt) <= len(speakers):
                found = speakers[int(attempt) - 1]["entity_id"]
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
