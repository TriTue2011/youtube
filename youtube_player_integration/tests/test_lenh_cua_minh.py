"""Next (thủ công và tự động) không được làm phiên chết.

Chủ máy 19/10/2026 23:37: bấm Next ở giây thứ 9 của bài đầu playlist → loa d50s thoáng về `idle` rồi mới phát bài mới; tích hợp thấy
`idle` sớm và gỡ loa → phiên chết sau 11 giây. Yêu cầu: «tự next không lỗi kể cả sau 3, 4 bài; next thủ công không lỗi kể cả next 3, 4
lần liên tiếp hoặc cách nhau».

Sửa theo CẤU TRÚC: (1) mọi lệnh phát do chính tích hợp gửi cho một loa được ghi lại (`lenh_cua_minh`); `idle` của loa đó trong
KHOANG_GIAY giây sau lệnh là chuyển bài, không phải Stop/luồng cắt → bỏ qua và kiểm lại sau khi hết khoảng; (2) các lần
Next/tự chuyển bài của một tích hợp chạy TUẦN TỰ, mỗi lần đọc trạng thái mới nhất của phiên (không tính bài kế từ ảnh chụp cũ).
"""
import asyncio
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import custom_components.tritue_youtube_player.advance as advance_mod
import custom_components.tritue_youtube_player.services as services_mod
from custom_components.tritue_youtube_player import lenh_cua_minh

T0 = datetime(2026, 10, 19, 17, 0, 0, tzinfo=timezone.utc)
SPEAKER = "media_player.loa_thu"
ITEM = {"id": "dQw4w9WgXcQ", "duration": 240, "source": "youtube"}
CO_TUA = 2 | 4 | 512 | 4096
KHONG_TUA = 4 | 512 | 4096 | 8


def at(seconds):
    return patch.object(advance_mod.dt_util, "utcnow", return_value=T0 + timedelta(seconds=seconds))


def ctx():
    return types.SimpleNamespace(id="c", user_id=None, parent_id=None)


class KhoangLenhCuaMinhTests(unittest.TestCase):
    def setUp(self):
        lenh_cua_minh.xoa()
        self.addCleanup(lenh_cua_minh.xoa)

    def test_trong_khoang_sau_lenh_roi_het_han(self):
        lenh_cua_minh.danh_dau([SPEAKER], now=T0)
        self.assertGreater(lenh_cua_minh.con_lai_giay(SPEAKER, T0 + timedelta(seconds=5)), 0)
        self.assertEqual(0, lenh_cua_minh.con_lai_giay(SPEAKER, T0 + timedelta(seconds=lenh_cua_minh.KHOANG_GIAY + 1)))

    def test_moi_loa_mot_dong_ho_rieng(self):
        lenh_cua_minh.danh_dau(["media_player.a"], now=T0)
        self.assertEqual(0, lenh_cua_minh.con_lai_giay("media_player.b", T0))

    def test_danh_dau_lai_keo_dai_khoang(self):
        lenh_cua_minh.danh_dau([SPEAKER], now=T0)
        lenh_cua_minh.danh_dau([SPEAKER], now=T0 + timedelta(seconds=15))
        self.assertGreater(lenh_cua_minh.con_lai_giay(SPEAKER, T0 + timedelta(seconds=30)), 0)

    def test_ban_do_khong_phinh_vo_han(self):
        for i in range(2000):
            lenh_cua_minh.danh_dau([f"media_player.x{i}"], now=T0)
        lenh_cua_minh.danh_dau([SPEAKER], now=T0 + timedelta(seconds=600))
        self.assertLessEqual(lenh_cua_minh.so_muc(), 300)


class IdleThoangQuaSauLenhCuaMinhTests(unittest.TestCase):
    def setUp(self):
        lenh_cua_minh.xoa()
        self.addCleanup(lenh_cua_minh.xoa)
        self.hass = MagicMock()
        self.hass.async_create_task = MagicMock(side_effect=lambda coro, **kw: None)
        self.adv = advance_mod.SessionAutoAdvance(self.hass, MagicMock())
        self.adv._async_resume = MagicMock(return_value="resume")
        self.adv._async_remove_speaker = MagicMock(return_value="remove")
        self.adv._async_advance = MagicMock(return_value="advance")
        self.adv._next_from = MagicMock(return_value="queue")
        self.session = {"session_id": "s1", "item": dict(ITEM), "queue": {"index": 0}}
        self.hen = []                      # (giây hẹn, hàm gọi lại)

        def _call_later(hass, delay, action):
            self.hen.append((delay, action))
            return lambda: None

        p = patch.object(advance_mod, "async_call_later", side_effect=_call_later)
        p.start()
        self.addCleanup(p.stop)

    def _play(self, seconds, features=KHONG_TUA):
        with at(seconds):
            self.adv._observe(self.session, SPEAKER, "playing",
                              {"media_content_id": self.session["item"]["id"], "supported_features": features,
                               "media_position_updated_at": (T0 + timedelta(seconds=seconds)).isoformat()}, ctx())

    def _idle(self, seconds, features=KHONG_TUA):
        self.adv._advancing.clear()
        with at(seconds):
            self.adv._observe(self.session, SPEAKER, "idle", {"supported_features": features}, ctx())

    def test_idle_ngay_sau_lenh_phat_cua_minh_bi_bo_qua_khong_go_loa(self):
        self._play(0)
        lenh_cua_minh.danh_dau([SPEAKER], now=T0 + timedelta(seconds=9))     # Next lúc giây 9
        self._idle(9.5)
        self.adv._async_remove_speaker.assert_not_called()
        self.adv._async_advance.assert_not_called()
        self.adv._async_resume.assert_not_called()

    def test_chuoi_idle_dồn_dập_trong_khoang_khong_phat_sinh_gi(self):
        self._play(0)
        lenh_cua_minh.danh_dau([SPEAKER], now=T0 + timedelta(seconds=9))
        for t in (9.4, 9.45, 9.46, 12):
            self._idle(t)
        self.adv._async_remove_speaker.assert_not_called()
        self.adv._async_advance.assert_not_called()

    def test_bi_bo_qua_thi_hen_kiem_lai_dung_mot_lan_cho_moi_loa_phien(self):
        self._play(0)
        lenh_cua_minh.danh_dau([SPEAKER], now=T0 + timedelta(seconds=9))
        for t in (9.4, 9.45, 9.46):
            self._idle(t)
        self.assertEqual(1, len(self.hen))

    def test_het_khoang_van_idle_som_thi_xu_ly_nhu_binh_thuong(self):
        self._play(0)
        lenh_cua_minh.danh_dau([SPEAKER], now=T0 + timedelta(seconds=9))
        self._idle(9.5 + lenh_cua_minh.KHOANG_GIAY)                           # hết khoảng, loa vẫn idle sớm
        self.adv._async_remove_speaker.assert_called_once()                   # idle giữa bài sau khoảng = Stop thật → gỡ loa
        self.adv._async_advance.assert_not_called()

    def test_playing_trong_khoang_van_duoc_ghi_nhan(self):
        self._play(0)
        lenh_cua_minh.danh_dau([SPEAKER], now=T0 + timedelta(seconds=9))
        self.session = {**self.session, "item": {**ITEM, "id": "vid2"}, "queue": {"index": 1}}
        self._play(10)                                                         # bài mới lên sóng
        self._idle(10 + 235)                                                   # bài mới hết thật (240 s), ngoài khoảng
        self.adv._async_advance.assert_called_once()                          # đã ghi nhận playing trong khoảng → hết bài → bài kế
        self.adv._async_remove_speaker.assert_not_called()

    def test_kiem_lai_loa_da_phat_bai_moi_thi_khong_lam_gi(self):
        self._play(0)
        lenh_cua_minh.danh_dau([SPEAKER], now=T0 + timedelta(seconds=9))
        self._idle(9.5)
        delay, goi_lai = self.hen[0]
        self.assertGreater(delay, 0)
        self.session = {**self.session, "item": {**ITEM, "id": "vid2"}, "queue": {"index": 1}}
        self.hass.states.get = MagicMock(return_value=types.SimpleNamespace(
            state="playing", attributes={"media_content_id": "vid2", "supported_features": KHONG_TUA}))
        self.adv._sessions = MagicMock(return_value=[self.session])
        self.adv._lead_speaker = MagicMock(return_value=SPEAKER)
        with at(9.5 + delay):
            goi_lai(None)
        self.adv._async_remove_speaker.assert_not_called()

    def test_kiem_lai_loa_van_im_va_chua_tung_phat_bai_moi_thi_dung_han(self):
        self._play(0)
        lenh_cua_minh.danh_dau([SPEAKER], now=T0 + timedelta(seconds=9))
        self._idle(9.5)
        delay, goi_lai = self.hen[0]
        self.session = {**self.session, "item": {**ITEM, "id": "vid2"}, "queue": {"index": 1}}
        self.hass.states.get = MagicMock(return_value=types.SimpleNamespace(
            state="idle", attributes={"supported_features": KHONG_TUA}))
        self.adv._sessions = MagicMock(return_value=[self.session])
        self.adv._lead_speaker = MagicMock(return_value=SPEAKER)
        with at(9.5 + delay):
            goi_lai(None)
        self.adv._async_remove_speaker.assert_called_once()


class ChuyenBaiTuanTuTests(unittest.IsolatedAsyncioTestCase):
    """Bấm Next 3–4 lần liên tiếp: mỗi lần PHẢI tiến đúng một bài (không tính từ ảnh chụp cũ, không chạy chồng nhau)."""

    def setUp(self):
        self.queue = {"index": 0, "items": [{"id": f"vid{i}", "source": "youtube", "url": f"vid{i}"} for i in range(10)]}
        self.session = {"session_id": "s1", "state": "playing", "queue": self.queue, "output_entity_ids": [SPEAKER]}
        self.entry = types.SimpleNamespace(
            entry_id="e1", runtime_data=types.SimpleNamespace(data={"sessions": [self.session]}))
        self.hass = MagicMock()
        self.hass.data = {}                      # khoá tuần tự nằm trong hass.data: phải là dict thật
        self.da_phat = []

        async def phat(hass, entry, session, item, **kwargs):
            await asyncio.sleep(0.02)                 # lệnh phát mất thời gian, các cuộc gọi dễ chồng lên nhau
            self.queue["index"] = int(item["id"][3:])  # máy phát cập nhật chỉ số bài; coordinator làm mới sau khi phát
            self.da_phat.append(item["id"])
            return {}

        p = patch.object(services_mod, "_async_play_session_item", side_effect=phat)
        p.start()
        self.addCleanup(p.stop)

    async def test_bon_lan_next_dong_thoi_tien_dung_bon_bai(self):
        await asyncio.gather(*(services_mod.async_skip(self.hass, self.entry, "s1", 1) for _ in range(4)))
        self.assertEqual(4, self.queue["index"])
        self.assertEqual(["vid1", "vid2", "vid3", "vid4"], self.da_phat)

    async def test_next_roi_previous_khong_lech(self):
        await asyncio.gather(
            services_mod.async_skip(self.hass, self.entry, "s1", 1),
            services_mod.async_skip(self.hass, self.entry, "s1", 1),
            services_mod.async_skip(self.hass, self.entry, "s1", -1),
        )
        self.assertEqual(1, self.queue["index"])

    async def test_loi_o_mot_lan_khong_giu_khoa_cho_lan_sau(self):
        thanh_cong = services_mod._async_play_session_item.side_effect
        lan = {"n": 0}

        async def phat(hass, entry, session, item, **kwargs):
            lan["n"] += 1
            if lan["n"] == 1:
                raise services_mod.ServiceValidationError(translation_domain="x", translation_key="playback_error")
            return await thanh_cua_lan_sau(hass, entry, session, item, **kwargs)

        thanh_cua_lan_sau = thanh_cong
        with patch.object(services_mod, "_async_play_session_item", side_effect=phat):
            with self.assertRaises(services_mod.ServiceValidationError):
                await services_mod.async_skip(self.hass, self.entry, "s1", 1)
            await services_mod.async_skip(self.hass, self.entry, "s1", 1)
        self.assertEqual(1, self.queue["index"])


class DispatchGhiLenhCuaMinhTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_dispatch_danh_dau_loa_truoc_va_sau_khi_phat(self):
        lenh_cua_minh.xoa()
        self.addCleanup(lenh_cua_minh.xoa)
        hass = MagicMock()
        hass.states.get = MagicMock(return_value=types.SimpleNamespace(state="idle", attributes={}))
        entry = types.SimpleNamespace(
            entry_id="e1",
            runtime_data=types.SimpleNamespace(client=MagicMock(), async_refresh=AsyncMock()),
        )
        thu_tu = []

        async def phat(*a, **k):
            thu_tu.append(("phat", lenh_cua_minh.con_lai_giay(SPEAKER) > 0))   # đã đánh dấu TRƯỚC khi gửi lệnh
            return {}

        with patch.object(services_mod, "_virtual_players", return_value=set()), \
             patch.object(services_mod.er, "async_get", return_value=MagicMock(async_get=lambda e: None)), \
             patch.object(services_mod, "async_play_on_players", side_effect=phat):
            await services_mod.async_dispatch(hass, entry, source="youtube", target="dQw4w9WgXcQ", entity_ids=[SPEAKER])
        self.assertEqual([("phat", True)], thu_tu)
        self.assertGreater(lenh_cua_minh.con_lai_giay(SPEAKER), 0)


if __name__ == "__main__":
    unittest.main()
