"""Authenticated Home Assistant HTTP API for the Lovelace card."""

from __future__ import annotations

import asyncio
from http import HTTPStatus

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .api import YouTubePlayerApiError
from .const import DOMAIN
from .hidden_players import (
    STORAGE_KEY,
    STORAGE_VERSION,
    apply_hidden_change,
    normalize_hidden,
)
from .playback import build_target_capabilities


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
