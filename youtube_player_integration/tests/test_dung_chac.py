"""Stop phải chắc chắn: «Stop youtube không được ngay, phải bấm lần 2, 2–3 lần» (chủ máy 28/10/2026). Loa (nhất là DLNA) có thể bỏ qua Stop
khi đang nạp luồng; một lệnh duy nhất không đủ. Kiểm: gửi lại khi loa còn phát, dừng ngay khi đã dừng, huỷ tác vụ đồng bộ vị trí."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import custom_components.tritue_youtube_player.dung_loa as dung_loa
from custom_components.tritue_youtube_player import dong_bo

E = "media_player.r1"


class HassGia:
    def __init__(self, bo_qua_so_lan_dau=0):
        self.bo_qua, self.lenh, self.state = bo_qua_so_lan_dau, [], "playing"
        self.states = SimpleNamespace(get=lambda e: SimpleNamespace(state=self.state, entity_id=e))
        self.services = SimpleNamespace(async_call=self._goi)

    async def _goi(self, dom, ten, data, blocking=False):
        self.lenh.append((dom, ten, data["entity_id"]))
        if len(self.lenh) > self.bo_qua:                 # loa bỏ qua các lệnh đầu rồi mới dừng
            self.state = "idle"


class TestDungChac(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p = patch.object(dung_loa, "CHO_XAC_NHAN_DUNG_S", 0.05)
        p.start()
        self.addCleanup(p.stop)

    async def test_loa_dung_ngay_thi_chi_gui_mot_lenh(self):
        h = HassGia(bo_qua_so_lan_dau=0)
        self.assertTrue(await dung_loa.async_dung_chac(h, E, "media_stop", "thử"))
        self.assertEqual(1, len(h.lenh))

    async def test_loa_bo_qua_stop_dau_thi_gui_lai_toi_khi_dung(self):
        h = HassGia(bo_qua_so_lan_dau=2)
        self.assertTrue(await dung_loa.async_dung_chac(h, E, "media_stop", "thử"))
        self.assertEqual(3, len(h.lenh), "phải tự gửi lại, không bắt người dùng bấm Stop lần 2, lần 3")

    async def test_loa_khong_chiu_dung_thi_thoi_sau_so_lan_toi_da_va_bao_that_bai(self):
        h = HassGia(bo_qua_so_lan_dau=99)
        self.assertFalse(await dung_loa.async_dung_chac(h, E, "media_stop", "thử"))
        self.assertEqual(dung_loa.DUNG_GUI_LAI + 1, len(h.lenh))

    async def test_dung_loa_huy_tac_vu_dong_bo_cua_loa_do(self):
        da_huy = []
        with patch.object(dong_bo, "huy_tac_vu", side_effect=lambda ds: da_huy.append(list(ds))):
            await dung_loa.async_dung_chac(HassGia(), E, "media_stop", "thử")
        self.assertEqual([[E]], da_huy)


if __name__ == "__main__":
    unittest.main()
