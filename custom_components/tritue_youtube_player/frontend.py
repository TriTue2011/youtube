"""Serve and auto-register the bundled Lovelace card through Home Assistant."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers.event import async_call_later
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
    # YAML-mode dashboards (or an unavailable collection) can't take a stored
    # resource; fall back to loading the card globally instead.
    if getattr(lovelace, "mode", "yaml") != "storage" or resources is None:
        add_extra_js_url(hass, versioned_url)
        return

    async def _apply(_now: Any = None) -> None:
        try:
            if not getattr(resources, "loaded", False):
                await resources.async_load()
            if not getattr(resources, "loaded", False):
                async_call_later(hass, 5, _apply)
                return
            existing = next(
                (
                    item
                    for item in resources.async_items()
                    if str(item.get("url", "")).split("?", 1)[0] == CARD_URL
                ),
                None,
            )
            if existing is None:
                await resources.async_create_item(
                    {"res_type": "module", "url": versioned_url}
                )
                LOGGER.info("Auto-registered card resource %s", versioned_url)
            elif existing.get("url") != versioned_url:
                await resources.async_update_item(
                    existing["id"], {"res_type": "module", "url": versioned_url}
                )
                LOGGER.info("Updated card resource to %s", versioned_url)
        except Exception as error:  # noqa: BLE001 - never break setup over the card
            LOGGER.warning(
                "Could not register card resource, loading it globally instead: %s",
                error,
            )
            add_extra_js_url(hass, versioned_url)

    await _apply()
