"""Mã chia sẻ ``TTPL1.`` (nút chia sẻ của thẻ) dùng được cho play_playlist / phat_playlist.

Mã mang cả nội dung playlist: ``"TTPL1." + base64url(zlib(JSON))`` (định dạng của máy phát, xem
``youtube_player/app/playlists.py``). Phát thì phải có playlist trong kho, nên lần đầu mã được NHẬP vào kho
(đúng việc thẻ làm khi dán mã vào ô Playlist). Để một automation chạy hằng ngày không đẻ ra bản trùng, ánh xạ
«băm của mã → id playlist đã nhập» được nhớ lại trong bộ nhớ của Home Assistant; lần sau thấy id đó còn trong
kho thì dùng lại, không nhập nữa.

Tích hợp KHÔNG giải mã nội dung: máy phát mới là nơi kiểm định từng bài (một nơi duy nhất, khỏi lệch luật).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from homeassistant.helpers.storage import Store

from .api import AuthenticationError, CannotConnectError, YouTubePlayerApiError
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


def is_share_code(text: Any) -> bool:
    return str(text or "").strip().startswith(SHARE_PREFIX)


async def async_playlist_id_from_code(
    hass: Any, client: Any, code: Any, *, store: Any | None = None
) -> str:
    """Id playlist trong kho cho một id kho hoặc một mã chia sẻ ``TTPL1.``.

    ValueError: ``invalid_playlist_code`` (mã sai khuôn / máy phát chê mã), ``playlist_empty`` (mã không có bài
    phát được), ``playlist_import_failed`` (nhập xong nhưng máy phát không trả id hợp lệ).
    Lỗi kết nối / xác thực của máy phát (YouTubePlayerApiError) được để nguyên cho nơi gọi.
    """
    code = "".join(str(code or "").split())
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
    known = dict((await store.async_load()) or {})

    remembered = known.get(digest)
    playlists = (await client.async_playlists()).get("playlists") or []
    if remembered and any(isinstance(p, dict) and p.get("id") == remembered for p in playlists):
        return remembered

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

    known.pop(digest, None)
    known[digest] = new_id
    while len(known) > MAX_SHARE_IMPORTS:
        known.pop(next(iter(known)))
    await store.async_save(known)
    return new_id
