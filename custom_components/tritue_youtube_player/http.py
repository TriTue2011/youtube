"""Authenticated Home Assistant HTTP API for the Lovelace card."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import time
from datetime import timedelta
from http import HTTPStatus
from urllib.parse import urlsplit

from aiohttp import ClientError, ClientTimeout, web
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .actions import speaker_base_url
from .api import YouTubePlayerApiError
from .const import DOMAIN
from .hidden_players import (
    STORAGE_KEY,
    STORAGE_VERSION,
    apply_hidden_change,
    normalize_hidden,
)
# Both storage modules export STORAGE_KEY/STORAGE_VERSION, so alias this one —
# importing it plainly would silently shadow the hidden-players store and write
# both features into the same file.
from .suggestions import (
    STORAGE_KEY as SUGGESTIONS_STORAGE_KEY,
    STORAGE_VERSION as SUGGESTIONS_STORAGE_VERSION,
    apply_suggestion_change,
    normalize_suggestions,
)
from .playback import build_target_capabilities


_LOGGER = logging.getLogger(__name__)

PROXY_URL = "/api/tritue_youtube_player/proxy/{token}"
PROXY_DATA = f"{DOMAIN}_proxy_links"
PROXY_SECONDS = 3600
PROXY_MAX_LINKS = 200
RELAY_HEADERS = ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges")


def _through_home_assistant(hass, upstream):
    """A signed path on this Home Assistant that relays a player-server stream.

    The browser showing the card reaches Home Assistant at whatever address it opened
    (home network, a public HTTPS name, Nabu Casa), but not necessarily the player
    server: owner 15/09/2026 on 5G got "NotSupportedError" because the card handed the
    phone http://172.16.10.38:3030/… — a home address, and plain HTTP inside an HTTPS
    page. Only links this integration received from its own server are relayed."""
    links = hass.data.setdefault(PROXY_DATA, {})
    now = time.monotonic()
    for token in [token for token, (_, until) in links.items() if until < now]:
        del links[token]
    while len(links) >= PROXY_MAX_LINKS:
        del links[next(iter(links))]
    token = secrets.token_urlsafe(18)
    links[token] = (upstream, now + PROXY_SECONDS)
    return async_sign_path(hass, PROXY_URL.format(token=token), timedelta(seconds=PROXY_SECONDS))


def _loaded_entry(hass, entry_id):
    entry = hass.config_entries.async_get_entry(entry_id)
    if (
        entry is None
        or entry.domain != DOMAIN
        or entry.state is not ConfigEntryState.LOADED
    ):
        return None
    return entry


_MA_VIDEO = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _trang_nhung(host: str, video: str, mute: str, start: int, gui_origin: bool) -> str:
    """Trang trung gian cùng nguồn với Home Assistant.

    Safari trên máy Mac bỏ thuộc tính ``referrerpolicy`` của khung và theo
    ``Referrer-Policy: no-referrer`` của trang HA, nên YouTube không biết ai đang
    nhúng và trả lỗi 153. Trang này tự khai chính sách referrer của nó, rồi mới
    nhúng YouTube. Lệnh điều khiển đi qua postMessage được chuyển tiếp hai chiều.
    """
    cau_hinh = json.dumps(
        {"host": host, "video": video, "mute": mute, "start": start, "origin": gui_origin},
        ensure_ascii=True,
    )
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="referrer" content="strict-origin-when-cross-origin">
<style>html,body{{margin:0;height:100%;background:#000}}iframe{{position:absolute;inset:0;width:100%;height:100%;border:0}}</style>
</head><body>
<iframe id="yt" referrerpolicy="strict-origin-when-cross-origin" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>
<script>
const c = {cau_hinh};
const src = new URL("https://" + c.host + "/embed/" + c.video);
src.searchParams.set("autoplay", "1");
src.searchParams.set("mute", c.mute);
src.searchParams.set("enablejsapi", "1");
src.searchParams.set("playsinline", "1");
src.searchParams.set("rel", "0");
if (c.start) src.searchParams.set("start", String(c.start));
if (c.origin) src.searchParams.set("origin", location.origin);
const yt = document.getElementById("yt");
yt.src = src.toString();
window.addEventListener("message", (event) => {{
  if (!yt.contentWindow) return;
  if (event.source === yt.contentWindow) parent.postMessage(event.data, location.origin);
  else if (event.source === parent) yt.contentWindow.postMessage(event.data, "https://" + c.host);
}});
</script>
</body></html>"""


class TriTueEmbedView(HomeAssistantView):
    """Trang nhúng YouTube cho Safari máy Mac — xem chú thích của ``_trang_nhung``."""

    url = "/api/tritue_youtube_player/nhung"
    name = "api:tritue_youtube_player:nhung"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        video = str(request.query.get("v") or "")
        if not _MA_VIDEO.fullmatch(video):
            return web.Response(status=HTTPStatus.BAD_REQUEST, text="bad video")
        host = "www.youtube-nocookie.com" if request.query.get("goc") == "nocookie" else "www.youtube.com"
        mute = "1" if request.query.get("mute") == "1" else "0"
        start_raw = str(request.query.get("start") or "0")
        start = int(start_raw) if start_raw.isdigit() else 0
        html = _trang_nhung(host, video, mute, start, request.query.get("bo_origin") != "1")
        return web.Response(
            text=html,
            content_type="text/html",
            headers={
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Content-Security-Policy": (
                    "default-src 'none'; "
                    "frame-src https://www.youtube.com https://www.youtube-nocookie.com; "
                    "script-src 'unsafe-inline'; style-src 'unsafe-inline'"
                ),
                "Cache-Control": "no-store",
            },
        )


class TriTueSearchView(HomeAssistantView):
    """Proxy card searches through the configured local add-on client."""

    url = "/api/tritue_youtube_player/search"
    name = "api:tritue_youtube_player:search"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return normalized results without exposing the add-on bearer token."""
        hass = request.app["hass"]
        entry_id = str(request.query.get("entry_id") or "")
        source = str(request.query.get("source") or "youtube").lower()
        query = str(request.query.get("q") or "").strip()
        try:
            limit = int(request.query.get("limit", "20"))
        except ValueError:
            limit = 0
        entry = _loaded_entry(hass, entry_id)
        if entry is None:
            return self.json(
                {"error": "entry_unavailable"}, HTTPStatus.NOT_FOUND
            )
        # Cửa chặn của đường TÌM KIẾM — khác với cửa chặn của đường luồng bên dưới.
        # Thiếu "facebook" ở đây thì tích hợp chặn ngay, yêu cầu không bao giờ tới máy
        # phát, và người dùng chỉ thấy "không tìm kiếm được" mà không rõ vì sao.
        if source not in {"youtube", "zing", "facebook"}:
            return self.json(
                {"error": "invalid_search_source"}, HTTPStatus.BAD_REQUEST
            )
        # Pasted YouTube links run long; the player server checks the exact rule
        # (120 characters of text, 2048 for a link).
        if not 1 <= len(query) <= 2048 or not 1 <= limit <= 30:
            return self.json(
                {"error": "invalid_search_query"}, HTTPStatus.BAD_REQUEST
            )
        try:
            payload = await entry.runtime_data.client.async_search(
                query, source=source, limit=limit
            )
        except YouTubePlayerApiError:
            return self.json(
                {"error": "search_unavailable"}, HTTPStatus.BAD_GATEWAY
            )
        return self.json(payload)


class TriTueStreamView(HomeAssistantView):
    """Stream URLs for the device showing the card: a song's sound, or the picture of
    a video YouTube refuses to embed (``youtube_video``)."""

    url = "/api/tritue_youtube_player/stream"
    name = "api:tritue_youtube_player:stream"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Return the player server's short-lived stream URL for one song."""
        hass = request.app["hass"]
        try:
            payload = await request.json()
        except ValueError:
            payload = None
        if not isinstance(payload, dict):
            return self.json({"error": "invalid_request"}, HTTPStatus.BAD_REQUEST)
        entry = _loaded_entry(hass, str(payload.get("entry_id") or ""))
        if entry is None:
            return self.json(
                {"error": "entry_unavailable"}, HTTPStatus.NOT_FOUND
            )
        source = payload.get("source")
        target = str(payload.get("target") or "").strip()
        # Danh sách này là CỬA CHẶN THỨ HAI, độc lập với `STREAM_SOURCES` của máy phát.
        # Thêm nguồn mới mà quên chỗ này thì tích hợp chặn ngay, add-on không bao giờ
        # nhận được yêu cầu, và triệu chứng chỉ là "không phát được" chung chung.
        if source not in {"youtube", "zing", "youtube_video", "facebook", "facebook_video"} or not 1 <= len(target) <= 2048:
            return self.json({"error": "invalid_request"}, HTTPStatus.BAD_REQUEST)
        try:
            max_height = (
                int(payload.get("max_height") or 0)
                if source in {"youtube_video", "facebook_video"}
                else 0
            )
        except (TypeError, ValueError):
            max_height = 0
        try:
            stream = await entry.runtime_data.client.async_create_stream(
                source, target, max_height=max_height or None,
                # ĐỊA CHỈ LOA/MÁY TẢI ĐƯỢC — phải gửi kèm, y như đường dịch vụ.
                #
                # Add-on nằm sau NAT của Supervisor: mọi lời gọi của tích hợp đến nó
                # đều xuất phát từ 172.30.32.1, mà dải ấy bị chính add-on từ chối (loa
                # không với tới được), nên nó KHÔNG BAO GIỜ tự học ra địa chỉ dùng được.
                # Thiếu gợi ý thì add-on trả 409 «public_base_url_required», tích hợp
                # quy hết về 502 «stream_unavailable», và thẻ chỉ hiện "Không lấy được
                # tiếng bài này" — giấu mất nguyên nhân.
                #
                # Đo trên máy chủ máy (.28, add-on 0.9.7) ngày 21/09/2026: nhật ký
                # add-on ghi «POST /api/integration/stream 409» cho MỌI nguồn, kể cả
                # Zing vốn không dùng yt-dlp. «actions.py» đã gửi gợi ý này ở hai chỗ
                # phát ra loa; riêng đường của THẺ đây thì bị bỏ quên.
                public_base_url=speaker_base_url(hass, entry.runtime_data.client),
            )
        except YouTubePlayerApiError as loi:
            # ĐỪNG NUỐT MÃ LỖI CỦA MÁY PHÁT.
            # Add-on nói rõ "public_base_url_required", tích hợp đổi thành
            # "stream_unavailable", thế là nguyên nhân biến mất và người soát lỗi đi
            # tìm yt-dlp suốt một tiếng (21/09/2026, máy .28). Mã của máy phát là thứ
            # duy nhất nêu đích danh nguyên nhân — chuyển nguyên văn ra ngoài, và ghi
            # một dòng nhật ký để lần sau chỉ cần mở log là thấy.
            ma = str(loi).strip() or "stream_unavailable"
            _LOGGER.warning(
                "Máy phát từ chối dựng luồng (%s/%s): %s", source, target[:60], ma
            )
            return self.json({"error": ma}, HTTPStatus.BAD_GATEWAY)
        body = {
            key: stream.get(key)
            for key in ("stream_url", "media_content_type", "direct_url", "height", "bitrate_kbps")
            if key in stream
        }
        upstream = str(body.get("stream_url") or "")
        if urlsplit(upstream).scheme not in {"http", "https"}:
            return self.json({"error": "stream_unavailable"}, HTTPStatus.BAD_GATEWAY)
        body["stream_url"] = _through_home_assistant(hass, upstream)
        return self.json(body)


class TriTueProxyView(HomeAssistantView):
    """Relay one stream from the player server to the browser showing the card."""

    url = PROXY_URL
    name = "api:tritue_youtube_player:proxy"
    requires_auth = True

    async def get(self, request: web.Request, token: str) -> web.StreamResponse:
        hass = request.app["hass"]
        link = hass.data.get(PROXY_DATA, {}).get(token)
        if link is None or link[1] < time.monotonic():
            return web.Response(status=HTTPStatus.NOT_FOUND)
        headers = {"Accept-Encoding": "identity"}
        range_header = request.headers.get("Range", "")
        if re.fullmatch(r"bytes=\d*-\d*", range_header):
            headers["Range"] = range_header
        session = async_get_clientsession(hass)
        try:
            upstream = await session.get(
                link[0], headers=headers, timeout=ClientTimeout(total=None, sock_connect=15, sock_read=60)
            )
        except (ClientError, TimeoutError):
            return web.Response(status=HTTPStatus.BAD_GATEWAY)
        async with upstream:
            response = web.StreamResponse(status=upstream.status)
            for header in RELAY_HEADERS:
                if value := upstream.headers.get(header):
                    response.headers[header] = value
            response.headers["Cache-Control"] = "private, no-store"
            await response.prepare(request)
            try:
                async for chunk in upstream.content.iter_chunked(64 * 1024):
                    await response.write(chunk)
            except (ClientError, ConnectionResetError, TimeoutError):
                # The browser moved on (seek, next song) or the server went away.
                pass
            return response

    async def head(self, request: web.Request, token: str) -> web.StreamResponse:
        """Tiêu đề của luồng (kiểu, cỡ, có tua được không) mà không tải tiếng.

        VÌ SAO CẦN: cả hai máy phát đều trả lời HEAD — c2a có tuyến riêng, add-on có
        «head_stream» — nhưng lớp tiếp sức này trước đây chỉ khai «get», nên aiohttp
        trả 405 cho mọi lời hỏi HEAD, và người hỏi coi như luồng hỏng. Đo trên máy nhà
        20/09/2026, cùng một địa chỉ: GET kèm «Range: bytes=0-1» trả 206 đúng chuẩn,
        HEAD trả 405. Một khả năng máy phát có mà lớp tiếp sức làm mất.

        HỎI BẰNG MỘT BYTE, KHÔNG HỎI HEAD LÊN MÁY PHÁT: cách này đúng với cả hai máy
        phát lẫn bản add-on đời cũ chưa có «head_stream», và lấy luôn được cỡ tệp thật
        từ «Content-Range» — chính cách «head_stream» của add-on đang làm.
        """
        hass = request.app["hass"]
        link = hass.data.get(PROXY_DATA, {}).get(token)
        if link is None or link[1] < time.monotonic():
            return web.Response(status=HTTPStatus.NOT_FOUND)
        session = async_get_clientsession(hass)
        try:
            upstream = await session.get(
                link[0],
                headers={"Accept-Encoding": "identity", "Range": "bytes=0-0"},
                timeout=ClientTimeout(total=None, sock_connect=15, sock_read=30),
            )
        except (ClientError, TimeoutError):
            return web.Response(status=HTTPStatus.BAD_GATEWAY)
        async with upstream:
            if upstream.status >= HTTPStatus.BAD_REQUEST:
                return web.Response(status=upstream.status)
            response = web.StreamResponse(status=HTTPStatus.OK)
            if value := upstream.headers.get("Content-Type"):
                response.headers["Content-Type"] = value
            response.headers["Accept-Ranges"] = "bytes"
            response.headers["Cache-Control"] = "private, no-store"
            tong = (upstream.headers.get("Content-Range") or "").rsplit("/", 1)[-1].strip()
            if tong.isdigit():
                # Đặt qua thuộc tính, KHÔNG qua headers: đo bằng aiohttp 3.12.15 thì
                # cách này trả đúng «Content-Length» và không kèm thân, còn ghi thẳng
                # vào headers là để aiohttp tự tính lại thành 0.
                response.content_length = int(tong)
            await response.prepare(request)
            return response


class TriTuePlaylistsView(HomeAssistantView):
    """Household playlists on the player server (the add-on or c2a)."""

    url = "/api/tritue_youtube_player/playlists"
    name = "api:tritue_youtube_player:playlists"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """List every playlist."""
        entry = _loaded_entry(request.app["hass"], str(request.query.get("entry_id") or ""))
        if entry is None:
            return self.json({"error": "entry_unavailable"}, HTTPStatus.NOT_FOUND)
        try:
            return self.json(await entry.runtime_data.client.async_playlists())
        except YouTubePlayerApiError as error:
            return self.json({"error": str(error)}, HTTPStatus.BAD_GATEWAY)

    async def post(self, request: web.Request) -> web.Response:
        """Run one command; the server's error code comes back for the card to explain."""
        try:
            payload = await request.json()
        except ValueError:
            payload = None
        if not isinstance(payload, dict):
            return self.json({"error": "invalid_request"}, HTTPStatus.BAD_REQUEST)
        entry = _loaded_entry(request.app["hass"], str(payload.pop("entry_id", "") or ""))
        if entry is None:
            return self.json({"error": "entry_unavailable"}, HTTPStatus.NOT_FOUND)
        try:
            return self.json(await entry.runtime_data.client.async_playlist_action(payload))
        except YouTubePlayerApiError as error:
            code = str(error)
            status = HTTPStatus.BAD_GATEWAY if code in {"playlist_unavailable", "cannot_connect"} else HTTPStatus.BAD_REQUEST
            return self.json({"error": code}, status)


class TriTueCapabilitiesView(HomeAssistantView):
    """Expose source/transport compatibility without leaking registry details."""

    url = "/api/tritue_youtube_player/capabilities"
    name = "api:tritue_youtube_player:capabilities"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return the supported source matrix for physical media players."""
        hass = request.app["hass"]
        entry_id = str(request.query.get("entry_id") or "")
        if _loaded_entry(hass, entry_id) is None:
            return self.json(
                {"error": "entry_unavailable"}, HTTPStatus.NOT_FOUND
            )

        registry = er.async_get(hass)
        items = []
        for state in hass.states.async_all("media_player"):
            registry_entry = registry.async_get(state.entity_id)
            platform = registry_entry.platform if registry_entry else None
            device_class = state.attributes.get("device_class")
            supported_features = int(
                state.attributes.get("supported_features") or 0
            )
            capability = build_target_capabilities(
                target_platform=platform,
                target_device_class=device_class,
                supported_features=supported_features,
            )
            items.append(
                {
                    "entity_id": state.entity_id,
                    "platform": platform,
                    "device_class": device_class,
                    "supported_features": supported_features,
                    **capability,
                }
            )
        return self.json({"items": items})


class TriTueHiddenPlayersView(HomeAssistantView):
    """Players hidden from the card, persisted in Home Assistant storage."""

    url = "/api/tritue_youtube_player/hidden_players"
    name = "api:tritue_youtube_player:hidden_players"
    requires_auth = True

    def __init__(self) -> None:
        self._store: Store | None = None
        self._hidden: list[str] | None = None
        self._lock = asyncio.Lock()

    async def _load(self, hass) -> list[str]:
        if self._store is None:
            self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        if self._hidden is None:
            self._hidden = normalize_hidden(await self._store.async_load())
        return self._hidden

    async def get(self, request: web.Request) -> web.Response:
        """Return the hidden players (any signed-in user sees the same card)."""
        async with self._lock:
            hidden = await self._load(request.app["hass"])
        return self.json({"entity_ids": hidden})

    async def post(self, request: web.Request) -> web.Response:
        """Hide or restore players; admin only, like editing a dashboard."""
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            return self.json({"error": "admin_required"}, HTTPStatus.FORBIDDEN)
        try:
            payload = await request.json()
        except ValueError:
            return self.json({"error": "invalid_request"}, HTTPStatus.BAD_REQUEST)
        if not isinstance(payload, dict):
            return self.json({"error": "invalid_request"}, HTTPStatus.BAD_REQUEST)
        async with self._lock:
            current = await self._load(request.app["hass"])
            try:
                hidden = apply_hidden_change(
                    current, payload.get("entity_ids"), payload.get("hidden")
                )
            except ValueError as error:
                return self.json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            await self._store.async_save({"entity_ids": hidden})
            self._hidden = hidden
        return self.json({"entity_ids": hidden})


class TriTueSuggestionsView(HomeAssistantView):
    """Household search keywords and pinned videos, persisted in storage."""

    url = "/api/tritue_youtube_player/suggestions"
    name = "api:tritue_youtube_player:suggestions"
    requires_auth = True

    def __init__(self) -> None:
        self._store: Store | None = None
        self._doc: dict | None = None
        self._lock = asyncio.Lock()

    async def _load(self, hass) -> dict:
        if self._store is None:
            self._store = Store(
                hass, SUGGESTIONS_STORAGE_VERSION, SUGGESTIONS_STORAGE_KEY
            )
        if self._doc is None:
            self._doc = normalize_suggestions(await self._store.async_load())
        return self._doc

    async def get(self, request: web.Request) -> web.Response:
        """Return the keywords and pinned videos (same list for everyone)."""
        async with self._lock:
            document = await self._load(request.app["hass"])
        return self.json(document)

    async def post(self, request: web.Request) -> web.Response:
        """Add or remove a keyword, group or pinned video; admin only."""
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            return self.json({"error": "admin_required"}, HTTPStatus.FORBIDDEN)
        try:
            payload = await request.json()
        except ValueError:
            return self.json({"error": "invalid_request"}, HTTPStatus.BAD_REQUEST)
        async with self._lock:
            current = await self._load(request.app["hass"])
            try:
                document = apply_suggestion_change(current, payload)
            except ValueError as error:
                return self.json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            await self._store.async_save(document)
            self._doc = document
        return self.json(document)
