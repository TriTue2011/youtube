"""Lý do loa về idle: hết bài / người dùng dừng / lỗi luồng / bị nội dung khác đè.

Nút Stop trên loa, hết bài và luồng đứt tạo ra CÙNG một sự kiện đổi trạng thái (idle, không ngữ cảnh), nên đoán bằng thời lượng
bài chỉ là phương án dự phòng. Tín hiệu thật, nếu loa có, đáng tin hơn:

- Thuộc tính chuẩn ``idle_reason`` trên thực thể media_player: các loa do chính chủ máy viết (R1, loa camera) khai ra.
- Google Cast: giao thức báo ``IdleReason`` (FINISHED / CANCELLED / INTERRUPTED / ERROR) trong ``media_status`` của thực thể,
  nhưng Home Assistant không đưa nó vào thuộc tính trạng thái. Đọc thuộc tính công khai ``media_status.idle_reason`` của thực thể.
- DLNA và AirPlay: giao thức không có mã lý do tin cậy (DLNA gộp STOPPED cho mọi trường hợp) → trả ``None``, dùng thời lượng bài.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import LOGGER

HET_BAI = "het_bai"
DUNG = "dung"
LOI = "loi"
BI_DE = "bi_de"

_THEO_THUOC_TINH = {
    "finished": HET_BAI, "ended": HET_BAI, "completed": HET_BAI,
    "stopped": DUNG, "cancelled": DUNG, "canceled": DUNG, "user_stop": DUNG,
    "error": LOI, "failed": LOI,
    "interrupted": BI_DE, "replaced": BI_DE,
}
_THEO_CAST = {"FINISHED": HET_BAI, "CANCELLED": DUNG, "ERROR": LOI, "INTERRUPTED": BI_DE}


def doc_ly_do_idle(hass: HomeAssistant, entity_id: str, attributes: dict[str, Any]) -> str | None:
    """``HET_BAI`` | ``DUNG`` | ``LOI`` | ``BI_DE``, hoặc ``None`` khi loa không cho biết (khi đó dùng thời lượng bài)."""
    khai = attributes.get("idle_reason")
    if isinstance(khai, str):
        return _THEO_THUOC_TINH.get(khai.strip().lower())
    return _doc_cast(hass, entity_id)


def _doc_cast(hass: HomeAssistant, entity_id: str) -> str | None:
    try:
        from homeassistant.components.media_player import DATA_COMPONENT  # noqa: PLC0415

        component = hass.data.get(DATA_COMPONENT)
        entity = component.get_entity(entity_id) if component is not None else None
        platform = getattr(getattr(entity, "platform", None), "domain", None)
        if platform != "cast":
            return None
        status = getattr(entity, "media_status", None)
        if status is None or not getattr(status, "player_is_idle", False):
            return None
        return _THEO_CAST.get(str(getattr(status, "idle_reason", "") or "").upper())
    except Exception as loi:  # noqa: BLE001 - chi tiết bên trong Home Assistant có thể đổi: lỗi thì dùng thời lượng bài
        LOGGER.debug("Không đọc được idle_reason của %s: %s", entity_id, type(loi).__name__)
        return None
