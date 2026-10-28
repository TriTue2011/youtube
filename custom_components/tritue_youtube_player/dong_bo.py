"""Đồng bộ vị trí phát giữa nhiều loa (Cast/DLNA…), theo ý của Music Assistant (cách B: máy chủ theo dõi tiến độ + độ trễ
rồi hiệu chỉnh): https://github.com/music-assistant/server (providers/airplay, controllers/players).

Cast và DLNA không có đồng hồ chung để lên lịch mẫu âm (khác AirPlay/PTP), nên ở đây KHÔNG hứa đồng bộ từng mẫu. Mục tiêu:
loa vào sau hoặc loa khởi động chậm được kéo về ĐÚNG VỊ TRÍ của loa chuẩn (sai lệch cỡ vài trăm mili giây, tuỳ loa báo vị
trí chính xác tới đâu). Cần khớp chặt hơn thì dùng Cast group / Snapcast (xem README, mục «Các loa không đồng bộ»).

Cách làm (mỗi loa theo sau, tối đa ``toi_da_lan`` vòng):
  1. chờ loa thực sự phát và báo vị trí (dựa trên trạng thái, không đoán thời gian cố định);
  2. đo trôi = vị trí loa theo sau - vị trí loa chuẩn - sync_adjust (cả hai nội suy tới cùng một thời điểm);
  3. trôi vượt ngưỡng thì ``media_seek`` tới vị trí loa chuẩn + sync_adjust + độ trễ seek đã học của loa đó
     (seek xong loa luôn tụt lại một chút vì phải nạp luồng; học độ trễ này theo lần đo thật, không đặt cố định);
  4. đợi loa báo vị trí mới rồi đo lại; học lại độ trễ seek.
``sync_adjust_ms`` từng loa (như ``sync_adjust`` của Music Assistant): số mili giây chỉnh tay, ÂM = loa phát SỚM hơn, dùng
cho tivi hoặc ampli có độ trễ riêng.

Mọi thời gian và hàm chờ đều truyền vào được để test không phải chờ thật.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from . import lenh_cua_minh

_LOGGER = logging.getLogger(__name__)

#: Cờ SEEK của MediaPlayerEntityFeature (giá trị cố định của Home Assistant).
SEEK = 2
#: Trôi cho phép (giây): dưới ngưỡng này coi là đã khớp (loa báo vị trí vốn chỉ chính xác cỡ nửa giây).
NGUONG_MAC_DINH_S = 0.8
TOI_DA_LAN_MAC_DINH = 3
#: Chờ tối đa để một loa bắt đầu phát và báo vị trí.
CHO_PHAT_TOI_DA_S = 20.0
#: Sau mỗi lần seek, đợi loa báo vị trí mới trước khi đo lại.
DOI_SAU_SEEK_S = 2.0
CHU_KY_HOI_S = 0.5
#: Độ trễ seek học được tối đa (giây), tránh một lần đo hỏng làm nhảy loa đi quá xa.
TRE_SEEK_TOI_DA_S = 3.0
#: Số loa tối đa nhớ độ trễ seek (bản đồ không phình theo thời gian).
TOI_DA_NHO = 128

_TRE_SEEK_S: dict[str, float] = {}


def tre_seek_da_hoc(entity_id: str) -> float:
    return _TRE_SEEK_S.get(str(entity_id), 0.0)


def xoa_nho() -> None:
    _TRE_SEEK_S.clear()


def _nho_tre_seek(entity_id: str, giay: float) -> None:
    _TRE_SEEK_S[str(entity_id)] = max(0.0, min(TRE_SEEK_TOI_DA_S, giay))
    while len(_TRE_SEEK_S) > TOI_DA_NHO:
        del _TRE_SEEK_S[next(iter(_TRE_SEEK_S))]


def vi_tri(state: Any, bay_gio: float) -> float | None:
    """Vị trí phát (giây) của một loa tại thời điểm ``bay_gio`` (epoch), nội suy từ lần cập nhật cuối; None nếu loa không
    ở trạng thái đang phát hoặc không báo vị trí."""
    if state is None or getattr(state, "state", None) != "playing":
        return None
    thuoc_tinh = getattr(state, "attributes", None) or {}
    try:
        pos = float(thuoc_tinh.get("media_position"))
    except (TypeError, ValueError):
        return None
    cap_nhat = thuoc_tinh.get("media_position_updated_at")
    if isinstance(cap_nhat, datetime):
        troi_qua = bay_gio - cap_nhat.timestamp()
        if troi_qua < 0 or troi_qua > 3600:
            troi_qua = 0.0          # đồng hồ lệch hoặc số liệu cũ vô lý: dùng vị trí báo nguyên văn
        pos += troi_qua
    return max(0.0, pos)


def ho_tro_seek(state: Any) -> bool:
    if state is None:
        return False
    try:
        return bool(int((getattr(state, "attributes", None) or {}).get("supported_features") or 0) & SEEK)
    except (TypeError, ValueError):
        return False


async def _cho_phat(hass: Any, entity_id: str, *, cho_toi_da: float, bay_gio: Callable[[], float],
                    ngu: Callable[[float], Awaitable[Any]]) -> bool:
    """Chờ tới khi loa đang phát và báo được vị trí. Trả False nếu hết giờ."""
    han = bay_gio() + cho_toi_da
    while True:
        if vi_tri(hass.states.get(entity_id), bay_gio()) is not None:
            return True
        if bay_gio() >= han:
            return False
        await ngu(CHU_KY_HOI_S)


async def async_can_chinh(
    hass: Any,
    master: str,
    followers: list[str],
    *,
    adjust_ms: dict[str, int] | None = None,
    nguong_s: float = NGUONG_MAC_DINH_S,
    toi_da_lan: int = TOI_DA_LAN_MAC_DINH,
    cho_toi_da_s: float = CHO_PHAT_TOI_DA_S,
    bay_gio: Callable[[], float] = time.time,
    ngu: Callable[[float], Awaitable[Any]] = asyncio.sleep,
) -> dict[str, dict[str, Any]]:
    """Kéo từng loa trong ``followers`` về vị trí của loa ``master``. Trả ``{entity_id: kết quả}``, mỗi kết quả có
    ``ket_qua`` ∈ {da_khop, da_chinh, chua_khop, khong_ho_tro_seek, khong_phat, loa_chuan_khong_phat} và ``troi_ms``."""
    adjust_ms = adjust_ms or {}
    ket_qua: dict[str, dict[str, Any]] = {}
    if not await _cho_phat(hass, master, cho_toi_da=cho_toi_da_s, bay_gio=bay_gio, ngu=ngu):
        return {f: {"ket_qua": "loa_chuan_khong_phat", "troi_ms": None} for f in followers if f != master}

    for entity_id in followers:
        if entity_id == master:
            continue
        if not ho_tro_seek(hass.states.get(entity_id)):
            ket_qua[entity_id] = {"ket_qua": "khong_ho_tro_seek", "troi_ms": None}
            continue
        if not await _cho_phat(hass, entity_id, cho_toi_da=cho_toi_da_s, bay_gio=bay_gio, ngu=ngu):
            ket_qua[entity_id] = {"ket_qua": "khong_phat", "troi_ms": None}
            continue
        chinh = float(adjust_ms.get(entity_id, 0)) / 1000.0
        da_chinh = False
        troi = 0.0
        for lan in range(max(1, toi_da_lan) + 1):
            t = bay_gio()
            pm = vi_tri(hass.states.get(master), t)
            pf = vi_tri(hass.states.get(entity_id), t)
            if pm is None or pf is None:
                break
            troi = pf - pm - chinh                      # > 0: loa theo sau đang ĐI TRƯỚC loa chuẩn
            if abs(troi) <= nguong_s:
                break
            if lan >= toi_da_lan:                       # hết vòng mà chưa khớp
                break
            if da_chinh:
                # lần seek trước để lại sai lệch `troi` ⇒ độ trễ seek thật của loa này lớn/nhỏ hơn đã nghĩ
                _nho_tre_seek(entity_id, tre_seek_da_hoc(entity_id) - troi)
            dich = max(0.0, pm + chinh + tre_seek_da_hoc(entity_id))
            lenh_cua_minh.danh_dau([entity_id])         # seek có thể làm loa thoáng về buffering/idle: không phải Stop
            try:
                await hass.services.async_call(
                    "media_player", "media_seek", {"entity_id": entity_id, "seek_position": round(dich, 2)},
                    blocking=True)
            except Exception as loi:   # noqa: BLE001 — một loa hỏng không được chặn các loa còn lại
                _LOGGER.warning("dong_bo: seek %s lỗi kiểu %s", entity_id, type(loi).__name__)
                break
            da_chinh = True
            await ngu(DOI_SAU_SEEK_S)
            await _cho_phat(hass, entity_id, cho_toi_da=cho_toi_da_s, bay_gio=bay_gio, ngu=ngu)
        khop = abs(troi) <= nguong_s
        ket_qua[entity_id] = {
            "ket_qua": ("da_chinh" if da_chinh else "da_khop") if khop else "chua_khop",
            "troi_ms": int(round(troi * 1000)),
        }
    return ket_qua


# ───────────── hiệu chỉnh định kỳ khi đang phát ─────────────

#: Chu kỳ kiểm trôi khi đang phát (giây). Loa khác loại có đồng hồ chạy lệch nhau nên trôi dần theo thời gian (vài trăm
#: mili giây mỗi vài phút); seek quá thường thì nghe giật, nên chỉ chỉnh khi trôi vượt ngưỡng ĐỊNH KỲ (cao hơn ngưỡng đầu).
CHU_KY_DINH_KY_MAC_DINH_S = 90.0
NGUONG_DINH_KY_MAC_DINH_S = 1.0
#: Loa chuẩn không phát liên tục quá ngần này giây (tạm dừng, dừng, đổi nguồn) thì thôi hiệu chỉnh.
CHO_CHUAN_TOI_DA_S = 120.0


async def vong_dong_bo(
    hass: Any,
    master: str,
    followers: list[str],
    *,
    adjust_ms: dict[str, int] | None = None,
    chu_ky_s: float = CHU_KY_DINH_KY_MAC_DINH_S,
    nguong_dinh_ky_s: float = NGUONG_DINH_KY_MAC_DINH_S,
    cho_chuan_toi_da_s: float = CHO_CHUAN_TOI_DA_S,
    bay_gio: Callable[[], float] = time.time,
    ngu: Callable[[float], Awaitable[Any]] = asyncio.sleep,
) -> None:
    """Căn đầu tiên (ngưỡng thường), rồi cứ ``chu_ky_s`` giây kiểm lại trôi; chỉ seek khi vượt ``nguong_dinh_ky_s``.
    ``chu_ky_s <= 0`` = chỉ căn một lần. Dừng khi loa chuẩn không còn phát quá ``cho_chuan_toi_da_s`` giây."""
    ket_qua = await async_can_chinh(hass, master, followers, adjust_ms=adjust_ms, bay_gio=bay_gio, ngu=ngu)
    _LOGGER.debug("dong_bo: lần đầu %s", {e: r["ket_qua"] for e, r in ket_qua.items()})
    if chu_ky_s <= 0:
        return
    khong_phat_tu = None
    while True:
        await ngu(chu_ky_s)
        if vi_tri(hass.states.get(master), bay_gio()) is None:
            khong_phat_tu = khong_phat_tu if khong_phat_tu is not None else bay_gio()
            if bay_gio() - khong_phat_tu >= cho_chuan_toi_da_s:
                return
            continue
        khong_phat_tu = None
        con_phat = [f for f in followers if vi_tri(hass.states.get(f), bay_gio()) is not None]
        if not con_phat:
            continue
        ket_qua = await async_can_chinh(hass, master, con_phat, adjust_ms=adjust_ms, nguong_s=nguong_dinh_ky_s,
                                        cho_toi_da_s=3.0, bay_gio=bay_gio, ngu=ngu)
        da_chinh = {e: r["troi_ms"] for e, r in ket_qua.items() if r["ket_qua"] == "da_chinh"}
        if da_chinh:
            _LOGGER.debug("dong_bo: chỉnh trôi định kỳ %s", da_chinh)


# ───────────── chạy nền, mỗi loa chỉ một tác vụ ─────────────

_TAC_VU: dict[str, "asyncio.Task[Any]"] = {}


def huy_tac_vu(entity_ids: list[str]) -> None:
    """Huỷ tác vụ đồng bộ đang chạy có dính tới các loa này (đổi bài/phát lại thì vị trí cũ hết nghĩa, seek theo nó là sai)."""
    for entity_id in entity_ids:
        tac = _TAC_VU.pop(str(entity_id), None)
        if tac is not None and not tac.done():
            tac.cancel()


def len_lich(entry: Any, hass: Any, master: str, followers: list[str], *, adjust_ms: dict[str, int] | None = None,
             chu_ky_s: float = CHU_KY_DINH_KY_MAC_DINH_S):
    """Chạy ``vong_dong_bo`` nền sau lệnh phát. Lệnh phát mới cho cùng các loa sẽ huỷ tác vụ cũ."""
    cac_loa = [master, *followers]
    huy_tac_vu(cac_loa)

    async def _chay() -> None:
        try:
            await vong_dong_bo(hass, master, followers, adjust_ms=adjust_ms, chu_ky_s=chu_ky_s)
        except asyncio.CancelledError:
            raise
        except Exception as loi:   # noqa: BLE001 — đồng bộ là phần thêm: lỗi không được làm hỏng việc phát
            _LOGGER.warning("dong_bo: lỗi kiểu %s", type(loi).__name__)

    tac = entry.async_create_background_task(hass, _chay(), "tritue_youtube_dong_bo")
    for entity_id in cac_loa:
        _TAC_VU[str(entity_id)] = tac

    def _don(xong: "asyncio.Task[Any]") -> None:
        for entity_id in cac_loa:
            if _TAC_VU.get(str(entity_id)) is xong:
                del _TAC_VU[str(entity_id)]

    tac.add_done_callback(_don)
    return tac
