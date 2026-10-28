"""Đồng bộ nhiều loa KHÁC LOẠI (Cast + DLNA/R1) trong một giờ: đồng hồ hai loa chạy lệch nhịp, vị trí loa báo có nhiễu, tua của DLNA có thể
bị lượng tử hoá nguyên giây. Chủ máy 28/10/2026: «lúc đầu đồng bộ tốt, dần dần mất đồng bộ» (R1 + loa Google).

Mô phỏng bằng đồng hồ ảo (không chờ thật). Đo ĐỘ LỆCH THẬT giữa hai loa (không phải số loa báo) sau lượt căn đầu tiên; bỏ các mốc loa đang nạp
lại luồng sau seek (lúc đó loa im, không phải «lệch»)."""
import asyncio
import random
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

import custom_components.tritue_youtube_player.dong_bo as dong_bo

SEEK = 2


class Het(Exception):
    pass


class DongHo:
    def __init__(self, t_het):
        self.t, self.t_het = 1_000_000.0, 1_000_000.0 + t_het

    def bay_gio(self):
        return self.t

    async def ngu(self, giay):
        self.t += giay
        if self.t > self.t_het:
            raise Het


class Loa:
    """Loa phát với đồng hồ riêng ``toc_do``; báo vị trí có nhiễu ±``nhieu`` giây; tua có thể bị lượng tử hoá nguyên giây."""

    def __init__(self, dh, pos, *, toc_do=1.0, nhieu=0.0, tua_nguyen=False, tre=1.0, rng=None):
        self.dh, self.toc_do, self.nhieu, self.tua_nguyen, self.tre = dh, toc_do, nhieu, tua_nguyen, tre
        self.pos0, self.t0, self.cho_den = pos, dh.t, 0.0
        self.rng, self.so_seek = rng or random.Random(1), 0

    def that(self):
        return self.pos0 + (self.dh.t - self.t0) * self.toc_do

    def dang_nap(self):
        return self.dh.t < self.cho_den

    def seek(self, pos):
        self.so_seek += 1
        pos = float(round(pos)) if self.tua_nguyen else pos
        self.pos0, self.t0, self.cho_den = pos, self.dh.t + self.tre, self.dh.t + self.tre

    def state(self):
        if self.dang_nap():
            return SimpleNamespace(state="buffering", attributes={"supported_features": SEEK})
        pos = self.that() + self.rng.uniform(-self.nhieu, self.nhieu)
        return SimpleNamespace(state="playing", attributes={
            "media_position": pos, "supported_features": SEEK,
            "media_position_updated_at": datetime.fromtimestamp(self.dh.t, tz=timezone.utc)})


class Hass:
    def __init__(self, loa):
        self.loa = loa
        self.states = SimpleNamespace(get=lambda e: self.loa[e].state() if e in self.loa else None)
        self.services = SimpleNamespace(async_call=self._goi)

    async def _goi(self, dom, ten, data, blocking=False):
        self.loa[data["entity_id"]].seek(float(data["seek_position"]))


async def chay(chuan, theo, *, gio=3600.0, on_dinh_s=180.0, **tham_so):
    """Chạy vòng đồng bộ ``gio`` giây ảo; trả (lệch lớn nhất, số seek) giữa hai loa SAU khi đã ổn định ``on_dinh_s`` giây kể từ lần seek đầu."""
    dh = chuan.dh
    hass = Hass({"c": chuan, "f": theo})
    lech, moc = [], {"t1": None}
    goc_ngu = dh.ngu

    async def ngu(giay):
        await goc_ngu(giay)
        if theo.so_seek >= 1 and moc["t1"] is None:
            moc["t1"] = dh.t
        if moc["t1"] is not None and dh.t - moc["t1"] >= on_dinh_s and not theo.dang_nap() and not chuan.dang_nap():
            lech.append(abs(theo.that() - chuan.that()))

    try:
        await dong_bo.vong_dong_bo(hass, "c", ["f"], bay_gio=dh.bay_gio, ngu=ngu, **tham_so)
    except Het:
        pass
    return (max(lech) if lech else None), theo.so_seek


class TestTroiNhieuLoa(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        dong_bo.xoa_nho()

    async def test_loa_chay_lech_nhip_va_bao_vi_tri_co_nhieu_van_giu_lech_duoi_nua_giay(self):
        dh = DongHo(3600.0)
        chuan = Loa(dh, 100.0)                                                   # loa Google: chính xác
        theo = Loa(dh, 103.7, toc_do=1.0004, nhieu=0.12, tre=1.1)                # R1: lệch 3,7 giây, chạy nhanh 0,04%
        lech, so_seek = await chay(chuan, theo)
        self.assertIsNotNone(lech)
        self.assertLess(lech, 0.5, f"lệch lớn nhất {lech:.2f} giây (số seek {so_seek})")
        self.assertLess(so_seek, 12, "không được seek liên tục (nghe giật)")

    async def test_loa_chi_tua_duoc_nguyen_giay_khong_bi_seek_lien_tuc_duoi_theo_nhieu(self):
        """DLNA từ chối đích thập phân: tua bị làm tròn → không hội tụ dưới ~0,5 giây; ngưỡng phải tự nới cho loa đó, KHÔNG dập dình."""
        dh = DongHo(3600.0)
        chuan = Loa(dh, 100.0)
        theo = Loa(dh, 102.4, toc_do=1.0003, nhieu=0.1, tua_nguyen=True, tre=1.1)
        lech, so_seek = await chay(chuan, theo)
        self.assertIsNotNone(lech)
        self.assertLess(lech, 1.0, f"lệch lớn nhất {lech:.2f}")
        self.assertLess(so_seek, 15, f"seek {so_seek} lần trong một giờ: đang đuổi theo nhiễu lượng tử")


if __name__ == "__main__":
    unittest.main()
