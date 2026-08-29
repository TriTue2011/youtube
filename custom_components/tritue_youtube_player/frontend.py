"""Serve and auto-register the bundled Lovelace card through Home Assistant."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.loader import async_get_integration

from .const import CARD_URL, DOMAIN, LOGGER
from .http import TriTueCapabilitiesView, TriTueSearchView


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card, register the views, and auto-register the card resource."""
    card_path = Path(__file__).with_name("www") / "tritue-youtube-player-card.js"
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(card_path), cache_headers=False)]
        )
    except RuntimeError:
        pass  # Static path already registered on a previous setup.
    hass.http.register_view(TriTueSearchView)
    hass.http.register_view(TriTueCapabilitiesView)

    integration = await async_get_integration(hass, DOMAIN)
    versioned_url = f"{CARD_URL}?v={integration.version}"

    async def _register_resource(_event: Any = None) -> None:
        await _async_register_card_resource(hass, versioned_url)

    # Registering during startup can wipe the (not-yet-loaded) resource list, so
    # wait until Home Assistant has finished starting.
    if hass.state is CoreState.running:
        await _register_resource()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_resource)


async def _async_register_card_resource(hass: HomeAssistant, versioned_url: str) -> None:
    """Add or update the card in the storage-mode Lovelace resource list."""
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None)
    # A YAML-mode resource collection is read-only (no async_create_item), and
    # LovelaceData exposes no reliable "mode" attribute, so detect writability by
    # capability. If we can't write resources, load the card globally instead.
    if resources is None or not hasattr(resources, "async_create_item"):
        add_extra_js_url(hass, versioned_url)
        return

    try:
        # Force the collection to load from storage before we read or write it,
        # so we never operate on (and then persist) an empty list.
        if hasattr(resources, "async_get_info"):
            await resources.async_get_info()
        elif hasattr(resources, "async_load"):
            await resources.async_load()
        items = list(resources.async_items())
        existing = next(
            (
                item
                for item in items
                if str(item.get("url", "")).split("?", 1)[0] == CARD_URL
            ),
            None,
        )
        if existing is not None:
            if existing.get("url") != versioned_url:
                await resources.async_update_item(
                    existing["id"], {"res_type": "module", "url": versioned_url}
                )
                LOGGER.info("Updated card resource to %s", versioned_url)
        elif items:
            # Other resources are present, so the list really did load; safe to add.
            await resources.async_create_item(
                {"res_type": "module", "url": versioned_url}
            )
            LOGGER.info("Auto-registered card resource %s", versioned_url)
        else:
            # Empty collection (fresh dashboard, or not loaded): don't risk a
            # create that could clobber; load the card globally instead.
            add_extra_js_url(hass, versioned_url)
    except Exception as error:  # noqa: BLE001 - never break setup over the card
        LOGGER.warning(
            "Could not register card resource, loading it globally instead: %s",
            error,
        )
        add_extra_js_url(hass, versioned_url)
