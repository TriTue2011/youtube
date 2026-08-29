"""Serve and auto-register the bundled Lovelace card through Home Assistant."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import CARD_URL, DOMAIN
from .http import TriTueCapabilitiesView, TriTueSearchView


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card, auto-load it, and register the authenticated views."""
    card_path = Path(__file__).with_name("www") / "tritue-youtube-player-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), cache_headers=False)]
    )
    # Auto-load the card so users don't have to add a Lovelace resource by hand,
    # and version the URL so browsers fetch the new card on every integration
    # release instead of serving a stale cached copy.
    integration = await async_get_integration(hass, DOMAIN)
    add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")
    hass.http.register_view(TriTueSearchView)
    hass.http.register_view(TriTueCapabilitiesView)
