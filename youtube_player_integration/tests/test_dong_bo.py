"""Đồng bộ vị trí nhiều loa (dong_bo.py): mô phỏng loa giả có đồng hồ ảo, độ trễ nạp luồng sau seek và vị trí lệch ban đầu.

Không mạng, không chờ thật: thời gian và hàm chờ đều là đồng hồ ảo. Kiểm: loa lệch bao nhiêu cũng được kéo về sát loa chuẩn,
độ trễ seek được HỌC theo lần đo thật (lần sau seek ít vòng hơn), đã khớp thì KHÔNG seek, loa không hỗ trợ seek / không phát /
loa chuẩn không phát đều báo đúng, ``sync_adjust`` hoạt động, một loa hỏng không chặn các loa còn lại."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

import custom_components.tritue_youtube_player.dong_bo as dong_bo
from custom_components.tritue_youtube_player import lenh_cua_minh

SEEK = 2


class DongHoAo:
    def __init__(self):
        self.t = 1_000_000.0

    def bay_gio(self):
        return self.t

    async def ngu(self, giay):
        self.t += giay


class LoaGia:
    """Loa phát 1x; sau seek: buffering ``tre`` giây rồi phát tiếp từ vị trí đích."""

    def __init__(self, dh, pos, *, tre=1.2, seek=True, phat=True, toc_do=1.0):
        self.dh, self.tre, self.seek, self.dang_phat, self.toc_do = dh, tre, seek, phat, toc_do
        self._pos0, self._t0 = pos, dh.t       # vị trí tại thời điểm _t0
        self._cho_den = 0.0                    # đang nạp luồng tới thời điểm này

    def vi_tri_that(self):
        return self._pos0 + (self.dh.t - self._t0) * self.toc_do

    def seek_toi(self, pos):
        self._pos0, self._t0 = pos, self.dh.t + self.tre
        self._cho_den = self.dh.t + self.tre

    def state(self):
        if not self.dang_phat or self.dh.t < self._cho_den:
            return SimpleNamespace(state="buffering" if self.dang_phat else "idle",
                                   attributes={"supported_features": SEEK if self.seek else 0})
        thuoc_tinh = {"media_position": self.vi_tri_that(),
                      "media_position_updated_at": datetime.fromtimestamp(self.dh.t, tz=timezone.utc),
                      "supported_features": SEEK if self.seek else 0}
        return SimpleNamespace(state="playing", attributes=thuoc_tinh)


class HassGia:
    def __init__(self, dh, loa):
        self.dh, self.loa, self.lenh = dh, loa, []
        self.states = SimpleNamespace(get=lambda e: self.loa[e].state() if e in self.loa else None)
        self.services = SimpleNamespace(async_call=self._goi)
        self.hong = set()

    async def _goi(self, dom, ten, data, blocking=False):
        assert (dom, ten) == ("media_player", "media_seek")
        e = data["entity_id"]
        self.lenh.append((e, data["seek_position"]))
        if e in self.hong:
            raise RuntimeError("loa hỏng")
        self.loa[e].seek_toi(data["seek_position"])


class TestDongBo(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        dong_bo.xoa_nho()
        lenh_cua_minh.xoa()
        self.dh = DongHoAo()

    async def chay(self, hass, master, followers, **kw):
        return await dong_bo.async_can_chinh(hass, master, followers, bay_gio=self.dh.bay_gio, ngu=self.dh.ngu, **kw)

    def troi(self, loa, chuan):
        return loa.vi_tri_that() - chuan.vi_tri_that()

    async def test_loa_tre_nhieu_giay_duoc_keo_ve_sat_loa_chuan(self):
        chuan = LoaGia(self.dh, 120.0)
        theo = LoaGia(self.dh, 100.0, tre=1.2)                 # chậm 20 giây (loa vào sau)
        hass = HassGia(self.dh, {"media_player.chuan": chuan, "media_player.theo": theo})
        kq = await self.chay(hass, "media_player.chuan", ["media_player.chuan", "media_player.theo"])
        self.assertEqual(kq["media_player.theo"]["ket_qua"], "da_chinh")
        self.assertLessEqual(abs(self.troi(theo, chuan)), dong_bo.NGUONG_MAC_DINH_S)
        self.assertGreaterEqual(len(hass.lenh), 1)
        # độ trễ seek được HỌC (≈ độ trễ nạp luồng thật của loa này)
        self.assertAlmostEqual(dong_bo.tre_seek_da_hoc("media_player.theo"), 1.2, delta=0.4)

    async def test_lan_sau_da_hoc_do_tre_thi_seek_dung_ngay_mot_lan(self):
        chuan = LoaGia(self.dh, 50.0)
        theo = LoaGia(self.dh, 10.0, tre=1.5)
        hass = HassGia(self.dh, {"c": chuan, "t": theo})
        await self.chay(hass, "c", ["t"])
        # làm loa lệch lại 30 giây rồi chỉnh lần nữa
        theo._pos0, theo._t0 = theo.vi_tri_that() - 30.0, self.dh.t
        hass.lenh.clear()
        kq = await self.chay(hass, "c", ["t"])
        self.assertEqual(kq["t"]["ket_qua"], "da_chinh")
        self.assertEqual(len(hass.lenh), 1, "đã học độ trễ seek: một lần seek là đủ")
        self.assertLessEqual(abs(self.troi(theo, chuan)), dong_bo.NGUONG_MAC_DINH_S)

    async def test_da_khop_thi_khong_seek(self):
        chuan = LoaGia(self.dh, 30.0)
        theo = LoaGia(self.dh, 30.3)                           # lệch 0,3 s < ngưỡng 0,8 s
        hass = HassGia(self.dh, {"c": chuan, "t": theo})
        kq = await self.chay(hass, "c", ["t"])
        self.assertEqual(kq["t"]["ket_qua"], "da_khop")
        self.assertEqual(hass.lenh, [])

    async def test_sync_adjust_am_cho_loa_phat_som_hon(self):
        chuan = LoaGia(self.dh, 30.0)
        theo = LoaGia(self.dh, 32.0)                           # tivi trễ 2 s: chủ máy đặt -2000 ms để nó phát sớm 2 s
        hass = HassGia(self.dh, {"c": chuan, "t": theo})
        kq = await self.chay(hass, "c", ["t"], adjust_ms={"t": -2000})
        self.assertEqual(kq["t"]["ket_qua"], "da_khop")        # đã đúng mục tiêu «đi trước 2 s»
        self.assertEqual(hass.lenh, [])

    async def test_sync_adjust_3_giay_keo_loa_ve_dung_muc_tieu(self):
        for adjust, ky_vong in ((-3000, 3.0), (3000, -3.0), (-1000, 1.0)):
            dong_bo.xoa_nho()
            chuan = LoaGia(self.dh, 60.0)
            theo = LoaGia(self.dh, 20.0, tre=1.0)
            hass = HassGia(self.dh, {"c": chuan, "t": theo})
            kq = await self.chay(hass, "c", ["t"], adjust_ms={"t": adjust})
            self.assertIn(kq["t"]["ket_qua"], ("da_chinh", "da_khop"), adjust)
            self.assertAlmostEqual(self.troi(theo, chuan), ky_vong, delta=dong_bo.NGUONG_MAC_DINH_S, msg=adjust)

    async def test_loa_khong_ho_tro_seek(self):
        chuan = LoaGia(self.dh, 5.0)
        theo = LoaGia(self.dh, 50.0, seek=False)
        hass = HassGia(self.dh, {"c": chuan, "t": theo})
        kq = await self.chay(hass, "c", ["t"])
        self.assertEqual(kq["t"]["ket_qua"], "khong_ho_tro_seek")
        self.assertEqual(hass.lenh, [])

    async def test_loa_theo_sau_khong_phat_het_gio(self):
        chuan = LoaGia(self.dh, 5.0)
        theo = LoaGia(self.dh, 0.0, phat=False)
        hass = HassGia(self.dh, {"c": chuan, "t": theo})
        kq = await self.chay(hass, "c", ["t"], cho_toi_da_s=3.0)
        self.assertEqual(kq["t"]["ket_qua"], "khong_phat")

    async def test_loa_chuan_khong_phat(self):
        chuan = LoaGia(self.dh, 5.0, phat=False)
        theo = LoaGia(self.dh, 0.0)
        hass = HassGia(self.dh, {"c": chuan, "t": theo})
        kq = await self.chay(hass, "c", ["t"], cho_toi_da_s=3.0)
        self.assertEqual(kq["t"]["ket_qua"], "loa_chuan_khong_phat")

    async def test_mot_loa_hong_khong_chan_loa_khac(self):
        chuan = LoaGia(self.dh, 60.0)
        a = LoaGia(self.dh, 10.0)
        b = LoaGia(self.dh, 15.0)
        hass = HassGia(self.dh, {"c": chuan, "a": a, "b": b})
        hass.hong.add("a")
        kq = await self.chay(hass, "c", ["a", "b"])
        self.assertEqual(kq["a"]["ket_qua"], "chua_khop")
        self.assertEqual(kq["b"]["ket_qua"], "da_chinh")
        self.assertLessEqual(abs(self.troi(b, chuan)), dong_bo.NGUONG_MAC_DINH_S)

    async def test_seek_duoc_danh_dau_la_lenh_cua_tich_hop(self):
        chuan = LoaGia(self.dh, 60.0)
        theo = LoaGia(self.dh, 10.0)
        hass = HassGia(self.dh, {"c": chuan, "t": theo})
        await self.chay(hass, "c", ["t"])
        self.assertGreater(lenh_cua_minh.con_lai_giay("t"), 0)   # idle thoáng qua sau seek không bị coi là Stop

    def test_vi_tri_noi_suy_tu_lan_cap_nhat_cuoi(self):
        t = 1_000_000.0
        st = SimpleNamespace(state="playing", attributes={
            "media_position": 10.0, "media_position_updated_at": datetime.fromtimestamp(t - 4, tz=timezone.utc)})
        self.assertAlmostEqual(dong_bo.vi_tri(st, t), 14.0, places=3)
        self.assertIsNone(dong_bo.vi_tri(SimpleNamespace(state="paused", attributes=st.attributes), t))
        self.assertIsNone(dong_bo.vi_tri(None, t))


class TestLenLich(unittest.IsolatedAsyncioTestCase):
    """Gắn vào luồng phát (services._dong_bo_nen): nhóm nhiều loa, loa mới vào phiên, tắt bằng tuỳ chọn, huỷ tác vụ cũ."""

    def setUp(self):
        dong_bo.xoa_nho()
        self.goi = []
        import asyncio

        class Entry:
            options = {}

            def async_create_background_task(inner, hass, coro, name):
                coro.close()                       # chỉ kiểm lập lịch, không chạy thật
                tac = asyncio.get_running_loop().create_future()
                self.goi.append(name)
                return tac

        self.Entry = Entry
        self.services = __import__("custom_components.tritue_youtube_player.services", fromlist=["x"])

    def test_nhieu_loa_thi_loa_dau_la_loa_chuan(self):
        with unittest_mock_patch(dong_bo, "len_lich") as lich:
            self.services._dong_bo_nen(None, self.Entry(), ["a", "b", "c"], None)
        lich.assert_called_once()
        self.assertEqual(lich.call_args.args[2:4], ("a", ["b", "c"]))

    def test_mot_loa_khong_dong_bo(self):
        with unittest_mock_patch(dong_bo, "len_lich") as lich:
            self.services._dong_bo_nen(None, self.Entry(), ["a"], None)
        lich.assert_not_called()

    def test_loa_moi_vao_phien_keo_ve_loa_dang_phat(self):
        with unittest_mock_patch(dong_bo, "len_lich") as lich:
            self.services._dong_bo_nen(None, self.Entry(), ["moi"], ["cu1", "cu2"])
        self.assertEqual(lich.call_args.args[2:4], ("cu1", ["moi"]))

    def test_tat_bang_tuy_chon(self):
        entry = self.Entry()
        entry.options = {"dong_bo": False}
        with unittest_mock_patch(dong_bo, "len_lich") as lich:
            self.services._dong_bo_nen(None, entry, ["a", "b"], None)
        lich.assert_not_called()

    def test_sync_adjust_tu_tuy_chon(self):
        entry = self.Entry()
        entry.options = {"dong_bo_adjust_ms": {"b": -300, "c": "x", "d": True}}
        with unittest_mock_patch(dong_bo, "len_lich") as lich:
            self.services._dong_bo_nen(None, entry, ["a", "b"], None)
        self.assertEqual(lich.call_args.kwargs["adjust_ms"], {"b": -300})


def unittest_mock_patch(doi_tuong, ten):
    from unittest import mock
    return mock.patch.object(doi_tuong, ten)


class TestDinhKy(unittest.IsolatedAsyncioTestCase):
    """Loa khác loại có đồng hồ chạy lệch nhau: trôi dần theo thời gian, vòng định kỳ phải kéo lại khi vượt ngưỡng."""

    def setUp(self):
        dong_bo.xoa_nho()
        lenh_cua_minh.xoa()
        self.dh = DongHoAo()

    async def test_loa_chay_nhanh_hon_bi_keo_lai_theo_chu_ky(self):
        chuan = LoaGia(self.dh, 10.0)
        theo = LoaGia(self.dh, 10.0, toc_do=1.02)            # nhanh hơn 2%: trôi 1,2 giây mỗi phút
        hass = HassGia(self.dh, {"c": chuan, "t": theo})

        async def ngu(giay):
            await self.dh.ngu(giay)
            if self.dh.t - goc > 600:                         # sau 10 phút ảo thì loa chuẩn dừng → vòng kết thúc
                chuan.dang_phat = False
        goc = self.dh.t
        await dong_bo.vong_dong_bo(hass, "c", ["t"], chu_ky_s=30.0, cho_chuan_toi_da_s=60.0,
                                  bay_gio=self.dh.bay_gio, ngu=ngu)
        self.assertGreaterEqual(len(hass.lenh), 3, "trôi nhiều phút phải được chỉnh lại nhiều lần")
        # hiệu chỉnh KHÔNG quá thường (không seek mỗi chu kỳ): ngưỡng định kỳ 1 s ⇒ cỡ một lần/phút
        self.assertLessEqual(len(hass.lenh), 20)

    async def test_chu_ky_0_chi_can_mot_lan(self):
        chuan = LoaGia(self.dh, 10.0)
        theo = LoaGia(self.dh, 40.0)
        hass = HassGia(self.dh, {"c": chuan, "t": theo})
        await dong_bo.vong_dong_bo(hass, "c", ["t"], chu_ky_s=0, bay_gio=self.dh.bay_gio, ngu=self.dh.ngu)
        self.assertGreaterEqual(len(hass.lenh), 1)
        so_lenh = len(hass.lenh)
        theo.toc_do = 2.0
        await self.dh.ngu(300)
        self.assertEqual(len(hass.lenh), so_lenh)             # không còn ai canh trôi

    async def test_loa_chuan_dung_thi_vong_ket_thuc(self):
        chuan = LoaGia(self.dh, 10.0)
        theo = LoaGia(self.dh, 10.0)
        hass = HassGia(self.dh, {"c": chuan, "t": theo})
        goc = self.dh.t

        async def ngu(giay):
            await self.dh.ngu(giay)
            if self.dh.t - goc > 100:
                chuan.dang_phat = False
        await dong_bo.vong_dong_bo(hass, "c", ["t"], chu_ky_s=30.0, cho_chuan_toi_da_s=90.0,
                                  bay_gio=self.dh.bay_gio, ngu=ngu)       # phải KẾT THÚC (không treo)
        self.assertEqual(hass.lenh, [])



class TestDichVuDatDoLech(unittest.IsolatedAsyncioTestCase):
    """Dịch vụ set_sync_adjust: ghi độ lệch từng loa vào tuỳ chọn của mục cấu hình; 0 = xoá."""

    async def _goi(self, entry, entity, ms):
        from unittest import mock
        import custom_components.tritue_youtube_player.services as sv
        dang_ky = {}
        hass = mock.MagicMock()
        hass.services.has_service.return_value = False
        hass.services.async_register = lambda dom, ten, ham, **kw: dang_ky.__setitem__(ten, ham)
        cap_nhat = []
        hass.config_entries.async_update_entry = lambda e, options=None: cap_nhat.append(options)
        sv.async_register_services(hass)
        with mock.patch.object(sv, "_loaded_entry_or_raise", return_value=entry):
            call = SimpleNamespace(data={"entry_id": "x", "entity_id": entity, "adjust_ms": ms})
            await dang_ky["set_sync_adjust"](call)
        return cap_nhat

    async def test_ghi_va_xoa_do_lech(self):
        entry = SimpleNamespace(options={"dong_bo": True, "dong_bo_adjust_ms": {"media_player.b": -300}})
        kq = await self._goi(entry, "media_player.tv", -3000)
        self.assertEqual(kq[-1], {"dong_bo": True, "dong_bo_adjust_ms": {"media_player.b": -300, "media_player.tv": -3000}})
        entry.options = kq[-1]
        kq = await self._goi(entry, "media_player.tv", 0)
        self.assertEqual(kq[-1]["dong_bo_adjust_ms"], {"media_player.b": -300})

    def test_schema_gioi_han(self):
        import voluptuous as vol
        import custom_components.tritue_youtube_player.services as sv
        sv.SET_SYNC_ADJUST_SCHEMA({"entry_id": "x", "entity_id": "media_player.a", "adjust_ms": 3000})
        with self.assertRaises(vol.Invalid):
            sv.SET_SYNC_ADJUST_SCHEMA({"entry_id": "x", "entity_id": "media_player.a", "adjust_ms": 999999})


if __name__ == "__main__":
    unittest.main()
