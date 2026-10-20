"""Mã chia sẻ ``TTPL1.`` (nút chia sẻ của thẻ) dùng được cho play_playlist / phat_playlist.

Mã mang cả nội dung playlist: ``"TTPL1." + base64url(zlib(JSON))`` (định dạng của máy phát, xem
``youtube_player/app/playlists.py``). Phát thì phải có playlist trong kho, nên lần đầu mã được NHẬP vào kho
(đúng việc thẻ làm khi dán mã vào ô Playlist). Để một automation chạy hằng ngày không đẻ ra bản trùng, ánh xạ
«băm của mã → id playlist đã nhập» được nhớ lại trong bộ nhớ của Home Assistant; lần sau thấy id đó còn trong
kho thì dùng lại, không nhập nữa.

Tích hợp KHÔNG giải mã nội dung: máy phát mới là nơi kiểm định từng bài (một nơi duy nhất, khỏi lệch luật).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import re
import zlib
from typing import Any
from urllib.parse import urlsplit

from homeassistant.helpers.storage import Store

from .api import AuthenticationError, CannotConnectError, YouTubePlayerApiError
from .code_input import clean_code
from .const import DOMAIN

SHARE_PREFIX = "TTPL1."
#: Cùng trần với máy phát (playlists.MAX_SHARE_CODE) — mã dài hơn chắc chắn bị máy phát từ chối.
MAX_SHARE_CODE = 300_000
#: Số ánh xạ «mã → id» được nhớ; đầy thì bỏ cái cũ nhất.
MAX_SHARE_IMPORTS = 200
STORE_VERSION = 1
STORE_KEY = f"{DOMAIN}_share_imports"

PLAYLIST_ID = re.compile(r"^[a-z0-9]{12}$")
#: base64url, có thể còn dấu «=» đệm; đủ để loại rác sớm mà không phải giải mã.
SHARE_BODY = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")
#: Mã lỗi ổn định của máy phát cho một mã chia sẻ không dùng được (xem api _async_request).
_SERVER_BAD_CODE = {"invalid_share_code", "playlist_empty"}

#: Cùng trần với máy phát (playlists.MAX_SHARE_JSON) khi giải nén chỉ để SO SÁNH nội dung.
MAX_SHARE_JSON = 2_000_000
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_FACEBOOK_ID = re.compile(r"^[0-9]{5,25}$")
_ZING_SONG_ID = re.compile(r"^[A-Za-z0-9]{8,16}$")
#: Một khoá cho mỗi mã đang nhập: hai lần gọi cùng mã chạy chồng nhau (automation kích hai lần, thẻ + action) chỉ nhập MỘT lần.
_NHAP_KHOA: dict[str, asyncio.Lock] = {}
_NHAP_KHOA_TOI_DA = 64


def is_share_code(text: Any) -> bool:
    return str(text or "").strip().startswith(SHARE_PREFIX)


def _item_key(source: Any, item_id: Any, url: Any = "") -> tuple[str, str] | None:
    """Khoá (nguồn, id) của một bài theo ĐÚNG luật của máy phát (playlists.normalize_item); None = máy phát sẽ bỏ bài này."""
    source = str(source or "").strip().lower()
    item_id = str(item_id or "").strip()
    if source == "youtube":
        return (source, item_id) if _VIDEO_ID.fullmatch(item_id) else None
    if source == "facebook":
        return (source, item_id) if _FACEBOOK_ID.fullmatch(item_id) else None
    if source == "zing":
        parsed = urlsplit(str(url or "").strip())
        host = (parsed.hostname or "").lower()
        song_id = parsed.path.rsplit("/", 1)[-1].removesuffix(".html")
        if (
            parsed.scheme == "https"
            and (host == "zingmp3.vn" or host.endswith(".zingmp3.vn"))
            and parsed.path.startswith("/bai-hat/")
            and _ZING_SONG_ID.fullmatch(song_id)
        ):
            return (source, song_id)
    return None


def share_code_keys(code: str) -> list[tuple[str, str]] | None:
    """Danh sách (nguồn, id) theo thứ tự trong mã, bỏ bài trùng/không hợp lệ như máy phát; None nếu không đọc được.

    CHỈ để nhận ra «playlist này đã có trong kho» — kết quả KHÔNG dùng để phát (máy phát vẫn là nơi kiểm định duy nhất khi nhập).
    Sai/lệch ở đây chỉ làm mất cơ hội dùng lại (nhập thêm một bản), không bao giờ phát nhầm nội dung.
    """
    body = code[len(SHARE_PREFIX):]
    try:
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        decompressor = zlib.decompressobj()
        text = decompressor.decompress(raw, MAX_SHARE_JSON)
        if decompressor.unconsumed_tail:
            return None
        data = json.loads(text)
    except (ValueError, zlib.error):
        return None
    rows = data.get("i") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return None
    keys: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows[:500]:
        if not isinstance(row, list) or len(row) < 2:
            continue
        key = _item_key(row[0], row[1], row[2] if len(row) > 2 else "")
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def _existing_playlist_id(playlists: list[Any], keys: list[tuple[str, str]] | None) -> str | None:
    """Id playlist trong kho có ĐÚNG các bài này theo đúng thứ tự (không xét tên: đổi tên không làm nó thành bản khác)."""
    if not keys:
        return None
    for playlist in playlists:
        if not isinstance(playlist, dict) or not PLAYLIST_ID.fullmatch(str(playlist.get("id") or "")):
            continue
        have = [
            (str(item.get("source") or "").lower(), str(item.get("id") or ""))
            for item in playlist.get("items") or []
            if isinstance(item, dict)
        ]
        if have == keys:
            return str(playlist["id"])
    return None


def _khoa_nhap(digest: str) -> asyncio.Lock:
    lock = _NHAP_KHOA.get(digest)
    if lock is None:
        if len(_NHAP_KHOA) >= _NHAP_KHOA_TOI_DA:
            for key in [k for k, v in _NHAP_KHOA.items() if not v.locked()]:
                _NHAP_KHOA.pop(key, None)
        lock = _NHAP_KHOA[digest] = asyncio.Lock()
    return lock


async def async_playlist_id_from_code(
    hass: Any, client: Any, code: Any, *, store: Any | None = None
) -> str:
    """Id playlist trong kho cho một id kho hoặc một mã chia sẻ ``TTPL1.``.

    ValueError: ``invalid_playlist_code`` (mã sai khuôn / máy phát chê mã), ``playlist_empty`` (mã không có bài
    phát được), ``playlist_import_failed`` (nhập xong nhưng máy phát không trả id hợp lệ).
    Lỗi kết nối / xác thực của máy phát (YouTubePlayerApiError) được để nguyên cho nơi gọi.
    """
    code = "".join(clean_code(code, "playlist_code").split())
    if PLAYLIST_ID.fullmatch(code):
        return code
    body = code[len(SHARE_PREFIX):]
    if (
        not code.startswith(SHARE_PREFIX)
        or not body
        or len(code) > MAX_SHARE_CODE
        or not SHARE_BODY.fullmatch(body)
    ):
        raise ValueError("invalid_playlist_code")

    digest = hashlib.sha256(code.encode("ascii")).hexdigest()
    store = store if store is not None else Store(hass, STORE_VERSION, STORE_KEY)
    # Cả «đọc kho → nhập → ghi ánh xạ» nằm trong MỘT khoá theo mã: gọi lại/gọi chồng cùng mã không nhập đôi.
    async with _khoa_nhap(digest):
        known = dict((await store.async_load()) or {})
        playlists = (await client.async_playlists()).get("playlists") or []

        remembered = known.get(digest)
        if remembered and any(isinstance(p, dict) and p.get("id") == remembered for p in playlists):
            return remembered

        # Playlist giống hệt đã có trong kho (nhập từ thẻ, từ bản cũ, hoặc người dùng tự dán) → dùng lại, KHÔNG nhập thêm bản sao.
        existing = _existing_playlist_id(playlists, share_code_keys(code))
        if existing:
            await _nho_anh_xa(store, known, digest, existing)
            return existing

        try:
            result = await client.async_playlist_action({"action": "import", "text": code})
        except (CannotConnectError, AuthenticationError):
            raise
        except YouTubePlayerApiError as error:
            if str(error) in _SERVER_BAD_CODE:
                raise ValueError("playlist_empty" if str(error) == "playlist_empty" else "invalid_playlist_code") from error
            raise
        new_id = str((result.get("playlist") or {}).get("id") or "") if isinstance(result, dict) else ""
        if not PLAYLIST_ID.fullmatch(new_id):
            raise ValueError("playlist_import_failed")

        await _nho_anh_xa(store, known, digest, new_id)
        return new_id


async def _nho_anh_xa(store: Any, known: dict[str, Any], digest: str, playlist_id: str) -> None:
    known.pop(digest, None)
    known[digest] = playlist_id
    while len(known) > MAX_SHARE_IMPORTS:
        known.pop(next(iter(known)))
    await store.async_save(known)
