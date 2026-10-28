"""Loa về idle SỚM giữa bài (biết thời lượng bài): đó là Stop, không phải hết bài.

Lịch sử: 19/10/2026 loa d50s về idle trước hết bài, phiên bị gỡ hết loa và nhạc không phát tiếp, nên mã từng «tự cứu» (coi là luồng
bị cắt và phát tiếp đúng chỗ MỘT lần) khi sự kiện không mang `user_id`/`parent_id`. 28/10/2026 chủ máy: «Bấm Stop trực tiếp trên
loa hoặc remote thì phải dừng luôn chứ, sao lại phát tiếp». Nút Stop trên loa và luồng bị cắt trông Y HỆT nhau với tích hợp (cùng
một sự kiện idle, không ngữ cảnh), nên tự cứu làm Stop thật không dừng được. Quy tắc nay: loa idle sớm giữa bài (biết thời lượng) =
Stop → gỡ loa khỏi phiên, dù ai bấm. Luồng bị cắt nếu còn xảy ra thì sửa ở NGUỒN (máy phát/luồng), không đoán ở đây.

Giữ nguyên: loa KHÔNG báo thời lượng (xem BaiKhongRoThoiLuongTests) vẫn không phân biệt được hết bài với Stop nên sang bài kế.
"""
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import custom_components.tritue_youtube_player.advance as advance_mod
from custom_components.tritue_youtube_player.sessions import observe_track

T0 = datetime(2026, 10, 19, 16, 0, 0, tzinfo=timezone.utc)
SPEAKER = "media_player.loa_thu"
ITEM = {"id": "dQw4w9WgXcQ", "duration": 240, "source": "youtube"}


def attrs(position=10, at=T0, content_id="dQw4w9WgXcQ"):
    return {
        "media_content_id": content_id,
        "media_position": position,
        "media_position_updated_at": at.isoformat(),
        "media_duration": 240,
    }


SEEK = 2                                  # MediaPlayerEntityFeature.SEEK
CO_TUA = SEEK | 4 | 512 | 4096            # loa tua được (ví dụ loa camera)
KHONG_TUA = 4 | 512 | 4096 | 8            # loa kiểu d50s: không PAUSE, không SEEK


def ctx(user_id=None, parent_id=None):
    return types.SimpleNamespace(id="c1", user_id=user_id, parent_id=parent_id)


class ObserveTrackDungSomTests(unittest.TestCase):
    def test_dung_som_dat_co_khi_idle_giua_bai(self):
        tracker = {}
        self.assertFalse(observe_track(tracker, "playing", attrs(10), T0, ITEM))
        self.assertFalse(observe_track(tracker, "idle", {}, T0 + timedelta(seconds=60), ITEM))
        self.assertTrue(tracker.get("dung_som"))

    def test_het_bai_that_khong_phai_dung_som(self):
        tracker = {}
        observe_track(tracker, "playing", attrs(10), T0, ITEM)
        self.assertTrue(observe_track(tracker, "idle", {}, T0 + timedelta(seconds=235), ITEM))
        self.assertNotIn("dung_som", tracker)


class DungSomQuyetDinhTests(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock()
        self.hass.async_create_task = MagicMock(side_effect=lambda coro, **kw: None)
        self.adv = advance_mod.SessionAutoAdvance(self.hass, MagicMock())
        self.adv._async_resume = MagicMock(return_value="coro-resume")
        self.adv._async_remove_speaker = MagicMock(return_value="coro-remove")
        self.adv._async_advance = MagicMock(return_value="coro-advance")
        self.adv._next_from = MagicMock(return_value="queue")
        self.session = {"session_id": "s1", "item": dict(ITEM), "queue": {"index": 1}}
        self.now = T0

    def _at(self, seconds):
        self.now = T0 + timedelta(seconds=seconds)
        return patch.object(advance_mod.dt_util, "utcnow", return_value=self.now)

    def _play(self, seconds=0, position=10):
        with self._at(seconds):
            self.adv._observe(
                self.session, SPEAKER, "playing",
                attrs(position, T0 + timedelta(seconds=seconds), self.session["item"]["id"]), ctx(),
            )

    def _idle(self, seconds, context, features=CO_TUA):
        self.adv._advancing.clear()
        with self._at(seconds):
            self.adv._observe(self.session, SPEAKER, "idle", {"supported_features": features}, context)

    def test_stop_tren_loa_khong_ngu_canh_thi_dung_han(self):
        """Ca chủ máy 28/10/2026: bấm Stop trên loa/remote (sự kiện không có user_id/parent_id) phải dừng, không phát tiếp."""
        for context in (None, ctx()):
            with self.subTest(context=context):
                self.adv._async_remove_speaker.reset_mock()
                self.session = {"session_id": f"s-{context!r}", "item": dict(ITEM), "queue": {"index": 1}}
                self._play(0)
                self._idle(60, context)
                self.adv._async_remove_speaker.assert_called_once()
                self.adv._async_resume.assert_not_called()
                self.adv._async_advance.assert_not_called()

    def test_stop_cua_nguoi_dung_hay_automation_trong_ha_dung_han(self):
        for context in (ctx(user_id="u1"), ctx(parent_id="auto-ctx")):
            with self.subTest(context=context):
                self.adv._async_remove_speaker.reset_mock()
                self.session = {"session_id": f"s-{context.user_id}", "item": dict(ITEM), "queue": {"index": 1}}
                self._play(0)
                self._idle(60, context)
                self.adv._async_remove_speaker.assert_called_once()
                self.adv._async_resume.assert_not_called()

    def test_loa_khong_tua_duoc_cung_dung_han_khong_sang_bai_ke(self):
        self._play(0)
        self._idle(60, ctx(), KHONG_TUA)
        self.adv._async_remove_speaker.assert_called_once()
        self.adv._async_advance.assert_not_called()
        self.adv._async_resume.assert_not_called()

    def test_het_bai_that_van_chuyen_bai_khong_phat_lai(self):
        self._play(0)
        self._idle(235, ctx())
        self.adv._async_resume.assert_not_called()
        self.adv._async_remove_speaker.assert_not_called()
        self.adv._async_advance.assert_called_once()

    def test_stop_xong_het_tracker_khong_con_cho_phat_lai(self):
        self._play(0)
        self._idle(60, None)
        self._idle(70, None)                           # sự kiện idle lặp lại không được phát gì
        self.adv._async_resume.assert_not_called()
        self.adv._async_advance.assert_not_called()


class BaiKhongRoThoiLuongTests(unittest.TestCase):
    """Bài KHÔNG có thời lượng (duration 0/None, ví dụ bài dài «LK Bolero» 19/10/2026): trước đây loa về idle thì KHÔNG có gì xảy ra
    (`observe_track` thấy không biết thời lượng nên không coi là hết bài cũng không là dừng sớm) → phiên «playing» mà loa đã im (23:16:31),
    và tự chuyển bài không bao giờ chạy cho loại bài này.

    Không biết thời lượng thì không phân biệt được hết bài / luồng cắt / nút trên loa, nên LUÔN sang bài kế (không phát lại — phát lại bài
    đã hết là sai); Stop trong Home Assistant (user_id/parent_id) vẫn dừng hẳn; hết bài kế thì gỡ loa (dừng là dừng hẳn); đã tự chuyển trong
    CHO_XAC_NHAN_DUNG_THAT_GIAY giây thì là Stop thật.
    """

    def setUp(self):
        self.hass = MagicMock()
        self.hass.async_create_task = MagicMock(side_effect=lambda coro, **kw: None)
        self.adv = advance_mod.SessionAutoAdvance(self.hass, MagicMock())
        self.adv._async_resume = MagicMock(return_value="coro-resume")
        self.adv._async_remove_speaker = MagicMock(return_value="coro-remove")
        self.adv._async_advance = MagicMock(return_value="coro-advance")
        self.adv._next_from = MagicMock(return_value="queue")
        self.session = {"session_id": "s1", "item": {**ITEM, "duration": 0}, "queue": {"index": 0}}

    def _attrs(self, seconds, features=KHONG_TUA):
        return {
            "media_content_id": "dQw4w9WgXcQ", "supported_features": features,
            "media_position_updated_at": (T0 + timedelta(seconds=seconds)).isoformat(),
        }

    def _play(self, seconds=0, features=KHONG_TUA):
        with patch.object(advance_mod.dt_util, "utcnow", return_value=T0 + timedelta(seconds=seconds)):
            self.adv._observe(self.session, SPEAKER, "playing", self._attrs(seconds, features), ctx())

    def _idle(self, seconds, context, features=KHONG_TUA):
        self.adv._advancing.clear()
        with patch.object(advance_mod.dt_util, "utcnow", return_value=T0 + timedelta(seconds=seconds)):
            self.adv._observe(self.session, SPEAKER, "idle", {"supported_features": features}, context)

    def test_observe_track_khong_biet_thoi_luong_dat_co_khong_ro(self):
        tracker = {}
        observe_track(tracker, "playing", {"media_content_id": "dQw4w9WgXcQ"}, T0, {**ITEM, "duration": 0})
        self.assertFalse(observe_track(tracker, "idle", {}, T0 + timedelta(seconds=200), {**ITEM, "duration": 0}))
        self.assertTrue(tracker.get("het_khong_ro"))
        self.assertNotIn("dung_som", tracker)

    def test_loa_chua_tung_phat_roi_idle_thi_khong_co_gi(self):
        tracker = {}
        self.assertFalse(observe_track(tracker, "idle", {}, T0, {**ITEM, "duration": 0}))
        self.assertNotIn("het_khong_ro", tracker)

    def test_loa_tu_idle_thi_sang_bai_ke(self):
        self._play(0)
        self._idle(200, ctx())
        self.adv._async_advance.assert_called_once()
        self.adv._async_resume.assert_not_called()
        self.adv._async_remove_speaker.assert_not_called()

    def test_loa_tua_duoc_van_sang_bai_ke_khong_phat_lai(self):
        self._play(0, CO_TUA)
        self._idle(200, ctx(), CO_TUA)
        self.adv._async_advance.assert_called_once()
        self.adv._async_resume.assert_not_called()

    def test_stop_trong_ha_dung_han(self):
        for context in (ctx(user_id="u1"), ctx(parent_id="auto")):
            with self.subTest(context=context):
                self.adv._async_advance.reset_mock()
                self.adv._async_remove_speaker.reset_mock()
                self._play(0)
                self._idle(200, context)
                self.adv._async_remove_speaker.assert_called_once()
                self.adv._async_advance.assert_not_called()

    def test_het_bai_ke_thi_go_loa(self):
        self.adv._next_from = MagicMock(return_value=None)
        self._play(0)
        self._idle(200, ctx())
        self.adv._async_remove_speaker.assert_called_once()
        self.adv._async_advance.assert_not_called()

    def test_idle_lan_hai_trong_90_giay_la_stop_that(self):
        self._play(0)
        self._idle(200, ctx())
        self.assertEqual(1, self.adv._async_advance.call_count)
        self.session = {**self.session, "item": {**ITEM, "id": "vid2", "duration": 0}, "queue": {"index": 1}}
        with patch.object(advance_mod.dt_util, "utcnow", return_value=T0 + timedelta(seconds=205)):
            self.adv._observe(self.session, SPEAKER, "playing", {**self._attrs(205), "media_content_id": "vid2"}, ctx())
        self._idle(240, ctx())                                           # chỉ 40 s sau lần tự chuyển
        self.adv._async_remove_speaker.assert_called_once()
        self.assertEqual(1, self.adv._async_advance.call_count)

    def test_bai_dai_lan_hai_het_that_van_sang_bai_ke(self):
        self._play(0)
        self._idle(200, ctx())
        self.session = {**self.session, "item": {**ITEM, "id": "vid2", "duration": 0}, "queue": {"index": 1}}
        with patch.object(advance_mod.dt_util, "utcnow", return_value=T0 + timedelta(seconds=205)):
            self.adv._observe(self.session, SPEAKER, "playing", {**self._attrs(205), "media_content_id": "vid2"}, ctx())
        self._idle(205 + 200, ctx())                                     # bài thứ hai phát 200 s rồi hết
        self.assertEqual(2, self.adv._async_advance.call_count)
        self.adv._async_remove_speaker.assert_not_called()



class NextFromTests(unittest.TestCase):
    """«action queue lại ra bài chả có trong queue» (chủ máy 20/10/2026): phiên gắn hàng đợi mà hết bài thì không được lấy bài của phiên."""

    def _adv(self, has_next, bound):
        hass = MagicMock()
        adv = advance_mod.SessionAutoAdvance(hass, MagicMock())
        store = MagicMock()
        store.has_next = MagicMock(return_value=has_next)
        return adv, patch.object(advance_mod, "get_queue_store", return_value=store), patch.object(
            advance_mod, "session_queue_key", return_value=bound)

    SESSION = {"session_id": "s1", "output_entity_ids": ["media_player.loa"]}

    def test_gan_hang_doi_het_bai_thi_dung_du_phien_con_bai_rieng(self):
        adv, p1, p2 = self._adv(False, "abcdef012345")
        with p1, p2, patch.object(advance_mod, "queue_item", return_value={"id": "BaiCuCuaPlaylist"}) as qi:
            self.assertIsNone(adv._next_from(self.SESSION))
        qi.assert_not_called()

    def test_gan_hang_doi_con_bai_thi_qua_hang_doi(self):
        adv, p1, p2 = self._adv(True, "abcdef012345")
        with p1, p2:
            self.assertEqual("queue", adv._next_from(self.SESSION))

    def test_khong_gan_hang_doi_van_roi_xuong_hang_doi_cua_phien(self):
        adv, p1, p2 = self._adv(False, None)
        with p1, p2, patch.object(advance_mod, "queue_item", return_value={"id": "x"}):
            self.assertEqual("session", adv._next_from(self.SESSION))


if __name__ == "__main__":
    unittest.main()
