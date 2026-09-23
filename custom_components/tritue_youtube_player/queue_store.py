"""The Queue store shared by the card's HTTP view and server-side auto-advance.

One object per Home Assistant instance (``hass.data``), loaded once at setup so
``advance.py`` can check synchronously, inside a state-change callback, whether
a speaker's queue has a next song.
"""

from __future__ import annotations

import asyncio
import secrets
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .queue import (
    STORAGE_KEY as QUEUE_STORAGE_KEY,
    STORAGE_VERSION as QUEUE_STORAGE_VERSION,
    advance_queue,
    apply_queue_change,
    get_queue,
    normalize_document,
    pick_next,
    queue_key,
)

DATA_KEY = f"{DOMAIN}_queue_store"


class QueueStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store(hass, QUEUE_STORAGE_VERSION, QUEUE_STORAGE_KEY)
        self._doc: dict[str, Any] | None = None
        self._lock = asyncio.Lock()

    async def async_load(self) -> None:
        async with self._lock:
            if self._doc is None:
                self._doc = normalize_document(await self._store.async_load())

    def has_next(self, key: str) -> bool:
        """Sync check for auto-advance; False before the store is loaded."""
        if self._doc is None:
            return False
        try:
            return pick_next(get_queue(self._doc, queue_key(key))) is not None
        except ValueError:
            return False

    async def async_get(self, key: Any) -> dict[str, Any]:
        await self.async_load()
        return get_queue(self._doc, queue_key(key))

    async def async_change(self, payload: Any) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Apply a card action; return (the queue, song to play). ValueError on bad input."""
        await self.async_load()
        async with self._lock:
            document, item = apply_queue_change(self._doc, payload, lambda: secrets.token_hex(8))
            if document is not self._doc:
                await self._store.async_save(document)
                self._doc = document
            return get_queue(document, queue_key(payload.get("key"))), item

    async def async_advance(self, key: str) -> dict[str, Any] | None:
        """Move ``key``'s queue to its next song and return it (None = done)."""
        await self.async_load()
        async with self._lock:
            document, item = advance_queue(self._doc, queue_key(key))
            if item is not None:
                await self._store.async_save(document)
                self._doc = document
            return item


def get_queue_store(hass: HomeAssistant) -> QueueStore:
    store = hass.data.get(DATA_KEY)
    if store is None:
        store = hass.data[DATA_KEY] = QueueStore(hass)
    return store
