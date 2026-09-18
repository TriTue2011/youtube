"""Authenticated Home Assistant HTTP API for the Lovelace card."""

from __future__ import annotations

import asyncio
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
        if source not in {"youtube", "zing"}:
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
        if source not in {"youtube", "zing", "youtube_video"} or not 1 <= len(target) <= 2048:
            return self.json({"error": "invalid_request"}, HTTPStatus.BAD_REQUEST)
        try:
            max_height = int(payload.get("max_height") or 0) if source == "youtube_video" else 0
        except (TypeError, ValueError):
            max_height = 0
        try:
            stream = await entry.runtime_data.client.async_create_stream(
                source, target, max_height=max_height or None
            )
        except YouTubePlayerApiError:
            return self.json(
                {"error": "stream_unavailable"}, HTTPStatus.BAD_GATEWAY
            )
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
