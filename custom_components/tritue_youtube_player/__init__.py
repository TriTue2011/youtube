"""TriTue YouTube Player integration."""

from homeassistant.const import CONF_URL, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant, callback
from datetime import timedelta

from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .advance import SessionAutoAdvance
from .api import YouTubePlayerClient
from .const import CONF_TOKEN, DOMAIN
from .coordinator import YouTubePlayerConfigEntry, YouTubePlayerCoordinator
from .dung_loa import async_dung_loa_luong
from .frontend import async_register_frontend
from .llm_api import async_register_llm_api
from .lua_chon_action import async_cap_nhat_lua_chon, huy_hen_lua_chon
from .queue_store import get_queue_store
from .services import async_register_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
#: Máy phát im liền ngần này giây (3 lượt hỏi 5 s) mới dừng loa — một lượt mạng chớp không được cắt nhạc.
IM_DUNG_LOA_GIAY = 15
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
    _async_theo_doi_vong_doi(hass, entry, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Ô chọn playlist/hàng đợi trong giao diện action: nạp một lần rồi làm mới định kỳ (thẻ cũng gọi khi đổi).
    await async_cap_nhat_lua_chon(hass, entry=entry)

    async def _lam_moi_lua_chon(_now) -> None:
        await async_cap_nhat_lua_chon(hass)

    entry.async_on_unload(async_track_time_interval(hass, _lam_moi_lua_chon, timedelta(minutes=10)))
    return True


@callback
def _async_theo_doi_vong_doi(hass: HomeAssistant, entry: YouTubePlayerConfigEntry,
                             coordinator: YouTubePlayerCoordinator) -> None:
    """Xoá hẳn nhạc ra loa khi máy phát ngừng trả lời (add-on dừng / gỡ) và khi Home Assistant dừng."""
    hen: dict[str, object] = {}

    async def _con_im(_now) -> None:
        hen.pop("huy", None)
        if not coordinator.last_update_success:
            await async_dung_loa_luong(hass, ly_do="Máy phát ngừng trả lời")

    @callback
    def _doi_trang_thai() -> None:
        # Coordinator chỉ gọi listener khi KẾT QUẢ ĐỔI (thành công ↔ lỗi) — nên hẹn kiểm lại, không đếm lượt lỗi.
        if coordinator.last_update_success:
            if huy := hen.pop("huy", None):
                huy()
        elif "huy" not in hen:
            hen["huy"] = async_call_later(hass, IM_DUNG_LOA_GIAY, _con_im)

    async def _ha_dung(_event: Event) -> None:
        hen["ha_dung"] = True
        await async_dung_loa_luong(hass, ly_do="Home Assistant dừng / khởi động lại")

    entry.async_on_unload(coordinator.async_add_listener(_doi_trang_thai))
    bo_nghe = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _ha_dung)

    @callback
    def _don() -> None:
        if huy := hen.pop("huy", None):
            huy()
        if not hen.get("ha_dung"):
            bo_nghe()                               # đã chạy rồi thì HA tự gỡ — gỡ lần nữa là báo lỗi

    entry.async_on_unload(_don)


async def async_unload_entry(
    hass: HomeAssistant, entry: YouTubePlayerConfigEntry
) -> bool:
    """Unload a configured player server — gỡ / tắt / nạp lại tích hợp thì dừng hẳn nhạc ra loa trước."""
    await async_dung_loa_luong(hass, ly_do="Gỡ / tắt tích hợp")
    huy_hen_lua_chon(hass)
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await async_cap_nhat_lua_chon(hass, reset=True)     # trả hai ô về dạng gõ chữ gốc
    return ok
