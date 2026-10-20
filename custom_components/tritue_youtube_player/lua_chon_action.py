"""Danh sách CHỌN (thả xuống) cho ô `playlist_code` của `play_playlist` và ô `queue_code` của `play_queue`.

Giao diện action của Home Assistant đọc ô nhập từ `services.yaml` (tĩnh), nên mặc định chỉ có ô gõ chữ — người dùng phải chép mã từ thẻ.
Home Assistant cho tích hợp ĐẶT LẠI mô tả của một action lúc đang chạy (`async_set_service_schema`): ta nạp mô tả gốc từ `services.yaml`,
chỉ thay bộ chọn của hai ô trên bằng danh sách playlist / hàng đợi hiện có (`custom_value: true` nên vẫn dán được mã như cũ).
Danh sách được làm mới khi tích hợp nạp, khi thẻ tạo/sửa playlist hay hàng đợi, và mỗi 10 phút; trang cần tải lại để thấy danh sách mới.

Phần dựng danh sách là hàm thuần (`dung_lua_chon_playlist`, `dung_lua_chon_queue`) để chạy được trong test đơn vị.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.service import async_set_service_schema
from homeassistant.util.yaml import load_yaml

from .api import YouTubePlayerApiError
from .const import DOMAIN, LOGGER, SERVICE_PLAY_PLAYLIST, SERVICE_PLAY_QUEUE
from .queue_store import get_queue_store

SERVICES_YAML = Path(__file__).with_name("services.yaml")
#: Tránh danh sách thả xuống dài vô tận nếu kho bị đầy (máy phát giới hạn 100 playlist, tích hợp 300 hàng đợi).
TOI_DA_LUA_CHON = 300


def dung_lua_chon_playlist(playlists: list[Any]) -> list[dict[str, str]]:
    """[{value: id, label: «tên (N bài)»}]; trùng tên thì thêm 4 ký tự cuối của id để phân biệt."""
    rows = [p for p in playlists if isinstance(p, dict) and str(p.get("id") or "")]
    ten_dem: dict[str, int] = {}
    for p in rows:
        ten = " ".join(str(p.get("name") or "Playlist").split())
        ten_dem[ten] = ten_dem.get(ten, 0) + 1
    out = []
    for p in rows[:TOI_DA_LUA_CHON]:
        ten = " ".join(str(p.get("name") or "Playlist").split())
        so_bai = len(p.get("items") or [])
        nhan = f"{ten} ({so_bai} bài)" + (f" · {str(p['id'])[-4:]}" if ten_dem[ten] > 1 else "")
        out.append({"value": str(p["id"]), "label": nhan})
    return out


def dung_lua_chon_queue(queues: dict[str, Any], ten_loa: dict[str, str]) -> list[dict[str, str]]:
    """[{value: khoá hàng đợi, label: «tên loa (N bài)»}] cho các hàng đợi đang có bài."""
    out = []
    for key, queue in list(queues.items())[:TOI_DA_LUA_CHON]:
        so_bai = len((queue or {}).get("items") or [])
        if not so_bai:
            continue
        ten = ten_loa.get(key) or ("Máy " + key.split(":", 1)[1][:6] if key.startswith("device:") else key)
        out.append({"value": key, "label": f"{ten} ({so_bai} bài)"})
    return out


def _chon(options: list[dict[str, str]]) -> dict[str, Any]:
    return {"select": {"options": options, "custom_value": True, "mode": "dropdown"}}


def ap_lua_chon(base: dict[str, Any], playlist_opts: list[dict[str, str]], queue_opts: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Mô tả của hai action sau khi thay bộ chọn (bản sao; `base` giữ nguyên). Danh sách rỗng thì giữ ô gõ chữ gốc."""
    out: dict[str, dict[str, Any]] = {}
    for service, field, opts in (
        (SERVICE_PLAY_PLAYLIST, "playlist_code", playlist_opts),
        (SERVICE_PLAY_QUEUE, "queue_code", queue_opts),
    ):
        desc = copy.deepcopy(base.get(service) or {})
        if opts and field in (desc.get("fields") or {}):
            desc["fields"][field]["selector"] = _chon(opts)
        out[service] = desc
    return out


def _doc_services_yaml() -> dict[str, Any]:
    data = load_yaml(str(SERVICES_YAML))
    return data if isinstance(data, dict) else {}


async def async_cap_nhat_lua_chon(hass: HomeAssistant, *, reset: bool = False) -> None:
    """Đặt lại mô tả hai action. `reset=True` (lúc gỡ tích hợp) trả về ô gõ chữ gốc. Mọi lỗi chỉ ghi log — không bao giờ làm hỏng tích hợp."""
    try:
        base = await hass.async_add_executor_job(_doc_services_yaml)
        playlist_opts: list[dict[str, str]] = []
        queue_opts: list[dict[str, str]] = []
        if not reset:
            entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
            if entries:
                try:
                    data = await entries[0].runtime_data.client.async_playlists()
                except YouTubePlayerApiError:
                    return                                   # máy phát chưa trả lời: giữ nguyên danh sách lần trước
                playlist_opts = dung_lua_chon_playlist(data.get("playlists") or [])
            store = get_queue_store(hass)
            await store.async_load()
            ten_loa = {}
            queues = await store.async_list()
            for key in queues:
                state = hass.states.get(key)
                if state is not None and state.name:
                    ten_loa[key] = state.name
            queue_opts = dung_lua_chon_queue(queues, ten_loa)
        for service, desc in ap_lua_chon(base, playlist_opts, queue_opts).items():
            async_set_service_schema(hass, DOMAIN, service, desc)
    except Exception as err:  # noqa: BLE001 — danh sách chọn chỉ là tiện lợi, lỗi gì cũng không được kéo theo tích hợp
        LOGGER.debug("Không cập nhật được danh sách chọn của action: %s", type(err).__name__)


_HEN_KEY = f"{DOMAIN}_lua_chon_hen"
TRE_LAM_MOI_GIAY = 3


@callback
def lam_moi_lua_chon_sau(hass: HomeAssistant) -> None:
    """Hẹn làm mới sau vài giây (gộp nhiều lần đổi liên tiếp thành MỘT lần gọi máy phát); gọi lại thì hẹn lại."""
    if huy := hass.data.pop(_HEN_KEY, None):
        huy()
    if not any(e.state is ConfigEntryState.LOADED for e in hass.config_entries.async_entries(DOMAIN)):
        return                                              # chưa/không còn tích hợp nào nạp: không có gì để làm mới

    async def _chay(_now) -> None:
        hass.data.pop(_HEN_KEY, None)
        await async_cap_nhat_lua_chon(hass)

    hass.data[_HEN_KEY] = async_call_later(hass, TRE_LAM_MOI_GIAY, _chay)


@callback
def huy_hen_lua_chon(hass: HomeAssistant) -> None:
    """Huỷ lần làm mới đang hẹn (gỡ tích hợp: không để hẹn giờ mồ côi sống tiếp)."""
    if huy := hass.data.pop(_HEN_KEY, None):
        huy()
