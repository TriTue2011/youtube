"""Dừng hẳn mọi loa đang phát luồng của máy phát.

Dùng khi bấm Stop mà máy phát không còn phiên, khi máy phát ngừng trả lời, khi Home Assistant dừng / khởi động lại,
và khi tích hợp bị gỡ / tắt. Chủ máy 06/10/2026: "khi restart HA, hay gỡ, dừng addon thì xoá hoàn toàn nhạc ra loa"
— trước đó loa giữ bài của phiên cũ, một câu TTS chen vào là nhạc tự phát lại.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import dong_bo
from .const import DOMAIN, LOGGER
from .sessions import DANG_PHAT, loa_phat_luong

STOP, TURN_OFF, PAUSE = 4096, 256, 1
#: Một loa treo (vd loa camera chờ ffmpeg tới 8 s) không được giữ cả lượt dừng — nhất là lúc HA đang tắt.
HET_GIO = 12
#: Sau lệnh dừng, chờ loa thôi «đang phát» tối đa ngần này giây; còn phát thì gửi lại (tối đa ``DUNG_GUI_LAI`` lần). Loa (nhất là DLNA)
#: có thể bỏ qua Stop khi đang nạp luồng, nên một lệnh duy nhất làm người dùng phải bấm Stop 2–3 lần (chủ máy 28/10/2026).
CHO_XAC_NHAN_DUNG_S = 1.2
DUNG_GUI_LAI = 2


async def async_dung_chac(hass: HomeAssistant, entity_id: str, dich_vu: str, ly_do: str) -> bool:
    """Gửi lệnh dừng tới một loa rồi KIỂM loa đã thôi phát chưa; còn phát thì gửi lại. Trả True khi loa đã dừng.

    Cũng huỷ tác vụ đồng bộ vị trí đang chạy cho loa này: nó không được tua loa vừa dừng (tua một số loa làm chúng phát lại)."""
    dong_bo.huy_tac_vu([entity_id])
    for lan in range(DUNG_GUI_LAI + 1):
        await hass.services.async_call("media_player", dich_vu, {ATTR_ENTITY_ID: entity_id}, blocking=True)
        han = time.monotonic() + CHO_XAC_NHAN_DUNG_S
        while True:
            st = hass.states.get(entity_id)
            if st is None or st.state not in ("playing", "buffering"):
                return True
            if time.monotonic() >= han:
                break
            await asyncio.sleep(0.2)
        LOGGER.warning("%s: loa %s vẫn %s sau lệnh %s (lần %d/%d) — gửi lại",
                       ly_do, entity_id, st.state, dich_vu, lan + 1, DUNG_GUI_LAI + 1)
    return False


async def async_dung_loa_luong(hass: HomeAssistant, *, them: Iterable[str] = (), ly_do: str) -> list[str]:
    """Dừng mọi loa đang phát luồng của máy phát (+ ``them`` nếu chúng đang phát). Trả danh sách loa đã gửi lệnh.

    Loa không có STOP thì tắt (TURN_OFF), không có nữa thì tạm dừng (PAUSE) — không bỏ qua im lặng loa nào."""
    registry = er.async_get(hass)
    cua_minh = {e.entity_id for e in registry.entities.values() if e.platform == DOMAIN}
    trang_thai = {s.entity_id: (s.state, dict(s.attributes)) for s in hass.states.async_all("media_player")}
    loa = set(loa_phat_luong(trang_thai, cua_minh))
    loa |= {e for e in them if e in trang_thai and e not in cua_minh and trang_thai[e][0] in DANG_PHAT}
    if not loa:
        return []

    async def _mot(entity_id: str) -> None:
        tinh_nang = int(trang_thai[entity_id][1].get("supported_features") or 0)
        dich_vu = ("media_stop" if tinh_nang & STOP else "turn_off" if tinh_nang & TURN_OFF
                   else "media_pause" if tinh_nang & PAUSE else None)
        if dich_vu is None:
            LOGGER.warning("%s: loa %s đang phát luồng nhưng không có Stop / Turn off / Pause", ly_do, entity_id)
            return
        try:
            if not await async_dung_chac(hass, entity_id, dich_vu, ly_do):
                LOGGER.warning("%s: loa %s vẫn phát sau %d lần gửi lệnh dừng", ly_do, entity_id, DUNG_GUI_LAI + 1)
        except Exception as error:  # noqa: BLE001 — một loa hỏng không được chặn các loa khác
            LOGGER.warning("%s: dừng %s bằng %s lỗi: %s", ly_do, entity_id, dich_vu, error)

    try:
        await asyncio.wait_for(asyncio.gather(*(_mot(e) for e in sorted(loa))), HET_GIO)
    except TimeoutError:
        LOGGER.warning("%s: dừng loa quá %s s, bỏ chờ", ly_do, HET_GIO)
    LOGGER.info("%s: đã dừng %s", ly_do, ", ".join(sorted(loa)))
    return sorted(loa)
