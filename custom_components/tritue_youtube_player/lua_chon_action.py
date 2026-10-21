"""Danh sách CHỌN cho giao diện action: ô `playlist_code` (`play_playlist`), ô `queue_code` (`play_queue`) và ô LOA (`entity_id`, tích nhiều loa như thẻ).

Giao diện action của Home Assistant đọc ô nhập từ `services.yaml` (tĩnh), nên mặc định chỉ có ô gõ chữ — người dùng phải chép mã từ thẻ.
Home Assistant cho tích hợp ĐẶT LẠI mô tả của một action lúc đang chạy (`async_set_service_schema`): ta nạp mô tả gốc từ `services.yaml`,
chỉ thay bộ chọn của hai ô trên bằng danh sách playlist / hàng đợi hiện có (`custom_value: true` nên vẫn dán được mã như cũ).
Danh sách được làm mới khi tích hợp nạp, khi thẻ tạo/sửa playlist hay hàng đợi, và mỗi 10 phút.

NV227: `async_set_service_schema` CHỈ cập nhật bộ nhớ đệm mô tả phía HA — giao diện (tab Hành động) đã tải
mô tả một lần trong phiên và không tự tải lại. Muốn frontend thấy danh sách mới phải bắn sự kiện
`service_registered` SAU khi đặt mô tả, đúng như `ServiceRegistry.async_register` của HA làm
(`homeassistant/core.py`); frontend nghe sự kiện này để tải lại mô tả action. Thiếu bước này thì
playlist/queue mới tạo chỉ hiện sau khi tải lại trang hoặc khởi động lại HA.

Phần dựng danh sách là hàm thuần (`dung_lua_chon_playlist`, `dung_lua_chon_queue`) để chạy được trong test đơn vị.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntryState

try:
    from homeassistant.const import EVENT_SERVICE_REGISTERED
except ImportError:  # môi trường test tối thiểu: đúng giá trị của HA (`homeassistant.const`)
    EVENT_SERVICE_REGISTERED = "service_registered"
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.service import async_set_service_schema
from homeassistant.util.yaml import load_yaml

from .api import YouTubePlayerApiError
from .const import DOMAIN, LOGGER, SERVICE_PLAY_ON_PLAYERS, SERVICE_PLAY_PLAYLIST, SERVICE_PLAY_QUEUE
from .hidden_players import STORAGE_KEY as HIDDEN_KEY, STORAGE_VERSION as HIDDEN_VERSION, normalize_hidden
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


def dung_lua_chon_queue(code: str, so_bai: int) -> list[dict[str, str]]:
    """Hàng đợi DUY NHẤT của nhà: một mục `{value: mã 12 ký tự, label: «Hàng đợi (N bài)»}` (kể cả khi trống). Loa PHÁT chọn riêng ở ô loa."""
    if not code:
        return []
    return [{"value": code, "label": f"Hàng đợi ({so_bai} bài)" if so_bai else "Hàng đợi (trống)"}]


def dung_lua_chon_loa(players: list[tuple[str, str]], an: set[str]) -> list[dict[str, str]]:
    """[{value: entity_id, label: tên}] các loa như THẺ liệt kê: bỏ loa bị ẩn trên thẻ, xếp theo tên; trùng tên thì thêm entity_id."""
    rows = [(eid, " ".join(str(ten or eid).split())) for eid, ten in players if eid not in an]
    rows.sort(key=lambda r: (r[1].casefold(), r[0]))
    dem: dict[str, int] = {}
    for _eid, ten in rows:
        dem[ten.casefold()] = dem.get(ten.casefold(), 0) + 1
    return [
        {"value": eid, "label": f"{ten} · {eid}" if dem[ten.casefold()] > 1 else ten}
        for eid, ten in rows[:TOI_DA_LUA_CHON]
    ]


def _chon(options: list[dict[str, str]]) -> dict[str, Any]:
    return {"select": {"options": options, "custom_value": True, "mode": "dropdown"}}


def _chon_loa(options: list[dict[str, str]]) -> dict[str, Any]:
    """Danh sách TÍCH CHỌN nhiều loa (ô tích như thẻ). Không `custom_value`: chế độ danh sách không có ô gõ tay — ai cần entity ngoài danh sách dùng YAML."""
    return {"select": {"options": options, "multiple": True, "mode": "list"}}


def ap_lua_chon(
    base: dict[str, Any],
    playlist_opts: list[dict[str, str]],
    queue_opts: list[dict[str, str]],
    loa_opts: list[dict[str, str]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Mô tả của các action sau khi thay bộ chọn (bản sao; `base` giữ nguyên). Danh sách rỗng thì giữ ô gốc."""
    out: dict[str, dict[str, Any]] = {}
    for service, field, opts, tao in (
        (SERVICE_PLAY_PLAYLIST, "playlist_code", playlist_opts, _chon),
        (SERVICE_PLAY_QUEUE, "queue_code", queue_opts, _chon),
        (SERVICE_PLAY_PLAYLIST, "entity_id", loa_opts or [], _chon_loa),
        (SERVICE_PLAY_QUEUE, "entity_id", loa_opts or [], _chon_loa),
        (SERVICE_PLAY_ON_PLAYERS, "entity_id", loa_opts or [], _chon_loa),
    ):
        desc = out.get(service) or copy.deepcopy(base.get(service) or {})
        if opts and field in (desc.get("fields") or {}):
            desc["fields"][field]["selector"] = tao(opts)
        out[service] = desc
    return out


def _doc_services_yaml() -> dict[str, Any]:
    data = load_yaml(str(SERVICES_YAML))
    return data if isinstance(data, dict) else {}


async def async_cap_nhat_lua_chon(hass: HomeAssistant, *, reset: bool = False, entry: Any = None) -> None:
    """Đặt lại mô tả hai action. `reset=True` (lúc gỡ tích hợp) trả về ô gõ chữ gốc. Mọi lỗi chỉ ghi log — không bao giờ làm hỏng tích hợp."""
    try:
        base = await hass.async_add_executor_job(_doc_services_yaml)
        playlist_opts: list[dict[str, str]] = []
        queue_opts: list[dict[str, str]] = []
        loa_opts: list[dict[str, str]] = []
        if not reset:
            registry = er.async_get(hass)
            loa = []
            for st in hass.states.async_all("media_player"):
                reg = registry.async_get(st.entity_id)
                if (reg is not None and reg.platform == DOMAIN) or st.state == "unavailable":
                    continue                                 # loa ảo của chính tích hợp, hoặc loa mất kết nối: thẻ cũng không liệt kê
                loa.append((st.entity_id, st.name))
            an = set(normalize_hidden(await Store(hass, HIDDEN_VERSION, HIDDEN_KEY).async_load()))
            loa_opts = dung_lua_chon_loa(loa, an)
            # Lúc `async_setup_entry` đang chạy, cấu hình CHƯA ở trạng thái LOADED (đang SETUP_IN_PROGRESS) nên lọc theo LOADED sẽ bỏ sót
            # chính tích hợp vừa nạp → danh sách playlist trống tới lần làm mới sau (báo cáo chủ máy 20/10/2026). Nơi gọi truyền entry thẳng vào.
            entries = [entry] if entry is not None else [
                e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED
            ]
            if entries:
                try:
                    data = await entries[0].runtime_data.client.async_playlists()
                except YouTubePlayerApiError:
                    return                                   # máy phát chưa trả lời: giữ nguyên danh sách lần trước
                playlist_opts = dung_lua_chon_playlist(data.get("playlists") or [])
            store = get_queue_store(hass)
            await store.async_load()
            queue_opts = dung_lua_chon_queue(store.code, len((await store.async_get(store.code)).get("items") or []))
        mo_ta = ap_lua_chon(base, playlist_opts, queue_opts, loa_opts)
        for service, desc in mo_ta.items():
            async_set_service_schema(hass, DOMAIN, service, desc)
        # Báo cho frontend biết mô tả đã đổi để nó tải lại (NV227 — xem docstring đầu tệp). Đặt hết mô tả
        # TRƯỚC rồi mới bắn: frontend tải lại ngay khi nhận sự kiện là thấy ngay bản mới; lỗi bắn chỉ mất
        # lần báo này (ngoại lệ bị bắt ở ngoài, chỉ ghi log), không làm mất mô tả đã đặt.
        for service in mo_ta:
            hass.bus.async_fire(EVENT_SERVICE_REGISTERED, {"domain": DOMAIN, "service": service})
    except Exception as err:  # noqa: BLE001 — danh sách chọn chỉ là tiện lợi, lỗi gì cũng không được kéo theo tích hợp
        LOGGER.debug("Không cập nhật được danh sách chọn của action: %s", type(err).__name__)


_HEN_KEY = f"{DOMAIN}_lua_chon_hen"
TRE_LAM_MOI_GIAY = 3


@callback
def lam_moi_lua_chon_sau(hass: HomeAssistant) -> None:
    """ĐIỂM BÁO ĐỔI DUY NHẤT của danh sách chọn (NV227): MỌI thay đổi kho playlist/queue phải đi qua đây —
    thẻ tạo/sửa/xoá playlist (POST /playlists), kho queue đổi (QueueStore), nhập playlist bằng mã TTPL1.
    Hẹn làm mới sau vài giây (gộp nhiều lần đổi liên tiếp thành MỘT lần gọi máy phát); gọi lại thì hẹn lại.

    Báo đổi là việc PHỤ: lỗi ở đây (kể cả hass thiếu mảnh trong môi trường lạ) chỉ ghi log, TUYỆT ĐỐI
    không được phá việc tạo/sửa vừa thành công của nơi gọi — đúng luật «lỗi làm mới chỉ log» của NV227."""
    try:
        if huy := hass.data.pop(_HEN_KEY, None):
            huy()
        if not any(e.state is ConfigEntryState.LOADED for e in hass.config_entries.async_entries(DOMAIN)):
            return                                              # chưa/không còn tích hợp nào nạp: không có gì để làm mới

        async def _chay(_now) -> None:
            hass.data.pop(_HEN_KEY, None)
            await async_cap_nhat_lua_chon(hass)

        hass.data[_HEN_KEY] = async_call_later(hass, TRE_LAM_MOI_GIAY, _chay)
    except Exception as err:  # noqa: BLE001 — báo đổi hỏng thì danh sách tự khớp lại ở lần nạp/10 phút sau
        LOGGER.debug("Không hẹn được làm mới danh sách chọn của action: %s", type(err).__name__)


@callback
def huy_hen_lua_chon(hass: HomeAssistant) -> None:
    """Huỷ lần làm mới đang hẹn (gỡ tích hợp: không để hẹn giờ mồ côi sống tiếp)."""
    if huy := hass.data.pop(_HEN_KEY, None):
        huy()
