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


class LoaDoiBai(Loa):
    """Loa phát bài A; tới ``luc_doi`` (giây ảo) chuyển sang bài B và bắt đầu từ 0 sau ``tre_bat_dau`` giây (nạp luồng). Trước đó nó VẪN báo
    «đang phát» bài A với vị trí cũ — đúng cái bẫy lúc chuyển bài."""

    def __init__(self, dh, pos_a, luc_doi, tre_bat_dau, **kw):
        super().__init__(dh, pos_a, **kw)
        self.luc_doi, self.tre_bat_dau, self.da_doi = luc_doi, tre_bat_dau, False

    def state(self):
        if not self.da_doi and self.dh.t >= self.luc_doi:
            self.da_doi = True
            self.pos0, self.t0 = 0.0, self.dh.t + self.tre_bat_dau
            self.cho_den = self.dh.t + self.tre_bat_dau
        st = super().state()
        if st.state == "playing":
            st.attributes["media_content_id"] = "B" if self.da_doi else "A"
        return st


class TestChuyenBaiKhongDoTrenSoLieuCu(unittest.IsolatedAsyncioTestCase):
    """«Khi chuyển sang bài thứ 2 lại mất đồng bộ» (R1 + loa Google, 28/10/2026): lúc lệnh phát bài B vừa gửi, hai loa còn báo đang phát bài A
    với vị trí cũ. Đo trôi trên số liệu đó rồi tua thì loa bị đẩy tới vị trí vô nghĩa."""

    def setUp(self):
        dong_bo.xoa_nho()

    async def test_khong_tua_theo_vi_tri_bai_cu_va_can_dung_khi_bai_moi_len(self):
        dh = DongHo(600.0)
        chuan = LoaDoiBai(dh, 200.0, dh.t + 2.0, 1.0)                 # Google: sang bài B sau 2 s, nạp 1 s
        theo = LoaDoiBai(dh, 203.0, dh.t + 2.0, 3.5, tre=1.0)          # R1: nạp luồng chậm hơn 2,5 s
        hass = Hass({"c": chuan, "f": theo})
        seeks = []
        goc = hass._goi

        async def goi(dom, ten, data, blocking=False):
            seeks.append((round(dh.t - 1_000_000, 1), data["seek_position"], theo.da_doi))
            await goc(dom, ten, data, blocking)

        hass.services.async_call = goi
        item_b = {"id": "B", "url": "u"}
        try:
            await dong_bo.vong_dong_bo(hass, "c", ["f"], bay_gio=dh.bay_gio, ngu=dh.ngu, item=item_b, chu_ky_s=0)
        except Het:
            pass
        # mọi lần tua phải nhắm vị trí BÀI B (nhỏ, vài giây), không bao giờ ~200 giây của bài A
        self.assertTrue(seeks, "loa R1 nạp chậm 2,5 giây phải được căn lại")
        for luc, dich, _ in seeks:
            self.assertLess(dich, 30.0, f"tua tới {dich} giây lúc {luc}: đang đo theo số liệu của bài cũ")
        self.assertLess(abs(theo.that() - chuan.that()), 0.5)

    async def test_khong_co_item_thi_van_dung_hanh_vi_cu_nhung_co_item_thi_cho_dung_bai(self):
        dh = DongHo(60.0)
        chuan = LoaDoiBai(dh, 200.0, dh.t + 5.0, 1.0)
        hass = Hass({"c": chuan})
        # ngay lúc đầu loa báo bài A: với item B thì CHƯA tính là đang phát
        self.assertIsNone(dong_bo.vi_tri(hass.states.get("c"), dh.bay_gio(), {"id": "B", "url": "u"}))
        self.assertIsNotNone(dong_bo.vi_tri(hass.states.get("c"), dh.bay_gio()))
