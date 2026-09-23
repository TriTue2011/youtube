"""TriTue YouTube Player integration."""

from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .advance import SessionAutoAdvance
from .api import YouTubePlayerClient
from .const import CONF_TOKEN, DOMAIN
from .coordinator import YouTubePlayerConfigEntry, YouTubePlayerCoordinator
from .frontend import async_register_frontend
from .llm_api import async_register_llm_api
from .queue_store import get_queue_store
from .services import async_register_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Register domain-wide actions, HTTP API and card assets."""
    async_register_services(hass)
    await async_register_frontend(hass)
    # Queue: loaded once so auto-advance can check a speaker's next song synchronously.
    await get_queue_store(hass).async_load()
    # Assist: conversation agents can enable the "TriTue Music" LLM API.
    async_register_llm_api(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: YouTubePlayerConfigEntry
) -> bool:
    """Set up a configured player server."""
    client = YouTubePlayerClient(
        entry.data[CONF_URL],
        entry.data[CONF_TOKEN],
        async_get_clientsession(hass),
    )
    coordinator = YouTubePlayerCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(SessionAutoAdvance(hass, entry).async_start())
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: YouTubePlayerConfigEntry
) -> bool:
    """Unload a configured player server."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
