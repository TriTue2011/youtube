"""Danh sách chọn (thả xuống) cho `playlist_code` / `queue_code` trong giao diện action (thay cho việc chép mã từ thẻ)."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import yaml

from custom_components.tritue_youtube_player import lua_chon_action as lc
from custom_components.tritue_youtube_player.api import YouTubePlayerApiError
from custom_components.tritue_youtube_player.const import DOMAIN

from pathlib import Path

SERVICES_YAML = Path(lc.__file__).with_name("services.yaml")


def _pl(pid, name, n=1):
    return {"id": pid, "name": name, "items": [{"id": f"v{i}"} for i in range(n)]}


class DungLuaChonTests(unittest.TestCase):
    def test_nhan_ten_va_so_bai(self):
        got = lc.dung_lua_chon_playlist([_pl("aaaaaaaaaaaa", "home", 44), _pl("bbbbbbbbbbbb", "Account cafe", 1)])
        self.assertEqual(
            [{"value": "aaaaaaaaaaaa", "label": "home (44 bài)"}, {"value": "bbbbbbbbbbbb", "label": "Account cafe (1 bài)"}], got)

    def test_trung_ten_thi_them_4_ky_tu_cuoi_cua_id(self):
        got = lc.dung_lua_chon_playlist([_pl("aaaaaaaaaa11", "home", 44), _pl("bbbbbbbbbb22", "home", 44), _pl("cccccccccccc", "khac")])
        self.assertEqual(
            ["home (44 bài) · aa11", "home (44 bài) · bb22", "khac (1 bài)"], [o["label"] for o in got])

    def test_bo_phan_tu_hong_va_gioi_han_so_luong(self):
        rows = [None, {"id": ""}, "x", _pl("cccccccccccc", "ok")] + [_pl(f"{i:012d}", f"p{i}") for i in range(lc.TOI_DA_LUA_CHON + 20)]
        got = lc.dung_lua_chon_playlist(rows)
        self.assertEqual(lc.TOI_DA_LUA_CHON, len(got))
        self.assertEqual("cccccccccccc", got[0]["value"])

    def test_queue_chi_liet_ke_hang_doi_co_bai_va_dung_ten_loa(self):
        queues = {
            "media_player.googlehome5802": {"items": [{}, {}]},
            "media_player.rong": {"items": []},
            "device:b612ec534541f383": {"items": [{}]},
        }
        got = lc.dung_lua_chon_queue(queues, {"media_player.googlehome5802": "Phòng khách"})
        self.assertEqual(
            [{"value": "media_player.googlehome5802", "label": "Hàng đợi «Phòng khách» (2 bài)"},
             {"value": "device:b612ec534541f383", "label": "Hàng đợi «Máy b612ec» (1 bài)"}], got)


class ApLuaChonTests(unittest.TestCase):
    def _base(self):
        return yaml.safe_load(SERVICES_YAML.read_text(encoding="utf-8"))

    def test_chi_thay_bo_chon_hai_o_va_giu_cho_dan_ma(self):
        base = self._base()
        out = lc.ap_lua_chon(base, [{"value": "aaaaaaaaaaaa", "label": "home (1 bài)"}], [{"value": "media_player.x", "label": "Hàng đợi «x» (1 bài)"}])
        sel = out["play_playlist"]["fields"]["playlist_code"]["selector"]["select"]
        self.assertTrue(sel["custom_value"])           # vẫn dán được mã TTPL1 / mã 12 ký tự / tên
        self.assertEqual("aaaaaaaaaaaa", sel["options"][0]["value"])
        self.assertEqual("media_player.x", out["play_queue"]["fields"]["queue_code"]["selector"]["select"]["options"][0]["value"])
        # các ô khác và bản gốc không bị đổi
        self.assertEqual(base["play_playlist"]["fields"]["entry_id"], out["play_playlist"]["fields"]["entry_id"])
        self.assertEqual({"text": None}, base["play_playlist"]["fields"]["playlist_code"]["selector"])

    def test_danh_sach_rong_giu_o_go_chu_goc(self):
        base = self._base()
        out = lc.ap_lua_chon(base, [], [])
        self.assertEqual(base["play_playlist"]["fields"]["playlist_code"], out["play_playlist"]["fields"]["playlist_code"])
        self.assertEqual(base["play_queue"]["fields"]["queue_code"], out["play_queue"]["fields"]["queue_code"])


class CapNhatTests(unittest.IsolatedAsyncioTestCase):
    def _hass(self, playlists=None, error=None, queues=None):
        hass = MagicMock()
        hass.data = {}
        hass.async_add_executor_job = AsyncMock(side_effect=lambda f, *a: f(*a))
        entry = MagicMock()
        entry.state = lc.ConfigEntryState.LOADED
        if error:
            entry.runtime_data.client.async_playlists = AsyncMock(side_effect=error)
        else:
            entry.runtime_data.client.async_playlists = AsyncMock(return_value={"playlists": playlists or []})
        hass.config_entries.async_entries.return_value = [entry]
        hass.states.get.return_value = None
        store = MagicMock()
        store.async_load = AsyncMock()
        store.async_list = AsyncMock(return_value=queues or {})
        return hass, store

    async def test_dat_lai_mo_ta_hai_action(self):
        hass, store = self._hass([_pl("aaaaaaaaaaaa", "home", 3)], queues={"media_player.x": {"items": [{}]}})
        with patch.object(lc, "get_queue_store", return_value=store), patch.object(lc, "async_set_service_schema") as dat:
            await lc.async_cap_nhat_lua_chon(hass)
        dat_theo = {c.args[2]: c.args[3] for c in dat.call_args_list}
        self.assertEqual({"play_playlist", "play_queue"}, set(dat_theo))
        self.assertEqual("aaaaaaaaaaaa", dat_theo["play_playlist"]["fields"]["playlist_code"]["selector"]["select"]["options"][0]["value"])
        self.assertEqual("media_player.x", dat_theo["play_queue"]["fields"]["queue_code"]["selector"]["select"]["options"][0]["value"])
        self.assertTrue(all(c.args[1] == DOMAIN for c in dat.call_args_list))

    async def test_entry_dang_nap_chua_la_loaded_van_co_danh_sach_playlist(self):
        """Báo cáo chủ máy 20/10/2026: «mã playlist chưa có list để chọn». Lúc async_setup_entry chạy, entry đang SETUP_IN_PROGRESS."""
        hass, store = self._hass([_pl("aaaaaaaaaaaa", "home", 3)])
        entry = MagicMock()
        entry.state = "setup_in_progress"
        entry.runtime_data.client.async_playlists = AsyncMock(return_value={"playlists": [_pl("aaaaaaaaaaaa", "home", 3)]})
        hass.config_entries.async_entries.return_value = [entry]   # lọc theo LOADED sẽ trả rỗng
        with patch.object(lc, "get_queue_store", return_value=store), patch.object(lc, "async_set_service_schema") as dat:
            await lc.async_cap_nhat_lua_chon(hass, entry=entry)
        dat_theo = {c.args[2]: c.args[3] for c in dat.call_args_list}
        self.assertEqual("aaaaaaaaaaaa", dat_theo["play_playlist"]["fields"]["playlist_code"]["selector"]["select"]["options"][0]["value"])

    async def test_may_phat_khong_tra_loi_thi_giu_nguyen_khong_dat_gi(self):
        hass, store = self._hass(error=YouTubePlayerApiError("cannot_connect"))
        with patch.object(lc, "get_queue_store", return_value=store), patch.object(lc, "async_set_service_schema") as dat:
            await lc.async_cap_nhat_lua_chon(hass)
        dat.assert_not_called()

    async def test_reset_tra_ve_o_go_chu_goc_va_khong_goi_may_phat(self):
        hass, store = self._hass([_pl("aaaaaaaaaaaa", "home")])
        with patch.object(lc, "get_queue_store", return_value=store), patch.object(lc, "async_set_service_schema") as dat:
            await lc.async_cap_nhat_lua_chon(hass, reset=True)
        for call in dat.call_args_list:
            for f in ("playlist_code", "queue_code"):
                sel = call.args[3]["fields"].get(f, {}).get("selector", {})
                self.assertNotIn("select", sel)
        hass.config_entries.async_entries.assert_not_called()

    async def test_loi_la_chi_ghi_log_khong_nem(self):
        hass, store = self._hass([_pl("aaaaaaaaaaaa", "home")])
        with patch.object(lc, "get_queue_store", return_value=store), \
             patch.object(lc, "async_set_service_schema", side_effect=RuntimeError("boom")):
            await lc.async_cap_nhat_lua_chon(hass)          # không ném


class HenGioTests(unittest.TestCase):
    """Hẹn giờ làm mới không được thành «hẹn giờ mồ côi» (pytest-homeassistant báo `Lingering timer`)."""

    def test_khong_co_tich_hop_nao_nap_thi_khong_hen(self):
        hass = MagicMock()
        hass.data = {}
        hass.config_entries.async_entries.return_value = []
        with patch.object(lc, "async_call_later") as hen:
            lc.lam_moi_lua_chon_sau(hass)
        hen.assert_not_called()

    def test_hen_lai_thi_huy_hen_cu_va_huy_hen_duoc(self):
        hass = MagicMock()
        hass.data = {}
        entry = MagicMock()
        entry.state = lc.ConfigEntryState.LOADED
        hass.config_entries.async_entries.return_value = [entry]
        huy1, huy2 = MagicMock(), MagicMock()
        with patch.object(lc, "async_call_later", side_effect=[huy1, huy2]):
            lc.lam_moi_lua_chon_sau(hass)
            lc.lam_moi_lua_chon_sau(hass)
        huy1.assert_called_once()                 # lần hẹn thứ hai thay lần đầu (gộp nhiều lần đổi liên tiếp)
        lc.huy_hen_lua_chon(hass)
        huy2.assert_called_once()
        lc.huy_hen_lua_chon(hass)                 # gọi lần nữa không lỗi


if __name__ == "__main__":
    unittest.main()
