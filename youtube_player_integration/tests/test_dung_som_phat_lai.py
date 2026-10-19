"""Loa về idle SỚM giữa bài: luồng bị cắt hay người dùng bấm Stop?

Chủ máy 19/10/2026 23:00:34: loa d50s tự về idle ~35–70 s trước hết bài thứ 2 của playlist, phiên bị gỡ hết loa
(`output_entity_ids=[]`) và nhạc KHÔNG phát tiếp. Nguyên nhân trong mã: `observe_track` đặt cờ `dung_som` khi loa idle sớm
hơn cuối bài quá END_TOLERANCE_SECONDS, `_observe` coi đó là Stop → gỡ loa → phiên một loa chết. Luồng bị cắt giữa bài
(máy phát/Google ngắt kết nối) trông Y HỆT.

Quy tắc mới (phân biệt bằng CẤU TRÚC — ngữ cảnh của sự kiện đổi trạng thái, không dò chữ):
- Stop do người dùng hoặc automation trong Home Assistant (`context.user_id` hoặc `context.parent_id`) → tôn trọng ngay.
- Loa tự đổi trạng thái (không ai ra lệnh qua Home Assistant) → coi là luồng cắt: phát tiếp đúng chỗ MỘT lần.
- Loa lại dừng sớm ở cùng bài trong CHO_XAC_NHAN_DUNG_THAT_GIAY giây sau lần phát tiếp → Stop thật (nút trên loa/remote).
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


class ObserveTrackViTriTests(unittest.TestCase):
    def test_dung_som_ghi_vi_tri_luc_dung(self):
        tracker = {}
        self.assertFalse(observe_track(tracker, "playing", attrs(10), T0, ITEM))
        self.assertFalse(observe_track(tracker, "idle", {}, T0 + timedelta(seconds=60), ITEM))
        self.assertTrue(tracker.get("dung_som"))
        self.assertAlmostEqual(70.0, tracker["dung_som_vi_tri"], delta=1)

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

    def _sang_bai_khac(self, index):
        """Phiên chuyển sang bài kế: khoá theo dõi (phiên, bài, vị trí hàng đợi, loa) đổi → tracker mới."""
        self.session = {**self.session, "item": {**ITEM, "id": f"vid{index}"}, "queue": {"index": index}}

    def test_loa_tu_idle_som_thi_phat_tiep_dung_cho_mot_lan(self):
        self._play(0)
        self._idle(60, ctx())
        self.adv._async_resume.assert_called_once()
        _, entity_id, position = self.adv._async_resume.call_args.args
        self.assertEqual(SPEAKER, entity_id)
        self.assertAlmostEqual(70.0, position, delta=1)
        self.adv._async_remove_speaker.assert_not_called()

    def test_khong_co_context_van_phat_tiep(self):
        self._play(0)
        self._idle(60, None)
        self.adv._async_resume.assert_called_once()
        self.adv._async_remove_speaker.assert_not_called()

    def test_stop_cua_nguoi_dung_trong_ha_duoc_ton_trong_ngay(self):
        self._play(0)
        self._idle(60, ctx(user_id="u1"))
        self.adv._async_remove_speaker.assert_called_once()
        self.adv._async_resume.assert_not_called()

    def test_stop_tu_automation_duoc_ton_trong_ngay(self):
        self._play(0)
        self._idle(60, ctx(parent_id="auto-ctx"))
        self.adv._async_remove_speaker.assert_called_once()
        self.adv._async_resume.assert_not_called()

    def test_dung_som_lan_hai_ngay_sau_khi_phat_tiep_la_stop_that(self):
        self._play(0)
        self._idle(60, ctx())
        self.assertEqual(1, self.adv._async_resume.call_count)
        self._play(65, position=70)                       # đã phát tiếp
        self._idle(80, ctx())                             # lại dừng sớm trong vòng 90 s
        self.adv._async_remove_speaker.assert_called_once()
        self.assertEqual(1, self.adv._async_resume.call_count)

    def test_dung_som_lan_hai_sau_khoang_cho_lai_duoc_phat_tiep(self):
        self._play(0)
        self._idle(60, ctx())
        self._play(65, position=70)
        self._idle(65 + advance_mod.CHO_XAC_NHAN_DUNG_THAT_GIAY + 5, ctx())
        self.assertEqual(2, self.adv._async_resume.call_count)
        self.adv._async_remove_speaker.assert_not_called()

    def test_het_bai_that_van_chuyen_bai_khong_phat_lai(self):
        self._play(0)
        self._idle(235, ctx())
        self.adv._async_resume.assert_not_called()
        self.adv._async_remove_speaker.assert_not_called()
        self.adv._async_advance.assert_called_once()

    def test_phien_dang_chuyen_bai_thi_khong_xep_hai_viec(self):
        self._play(0)
        self.adv._advancing.add("s1")
        with self._at(60):
            self.adv._observe(self.session, SPEAKER, "idle", {}, ctx())
        self.adv._async_resume.assert_not_called()

    def test_loa_khong_tua_duoc_thi_sang_bai_ke_khong_phat_lai_tu_dau(self):
        self._play(0)
        self._idle(60, ctx(), KHONG_TUA)
        self.adv._async_advance.assert_called_once()
        self.adv._async_resume.assert_not_called()
        self.adv._async_remove_speaker.assert_not_called()

    def test_loa_khong_tua_duoc_va_het_bai_ke_thi_nhu_cu_go_loa(self):
        self.adv._next_from = MagicMock(return_value=None)
        self._play(0)
        self._idle(60, ctx(), KHONG_TUA)
        self.adv._async_remove_speaker.assert_called_once()
        self.adv._async_advance.assert_not_called()
        self.adv._async_resume.assert_not_called()

    def test_bam_stop_tren_loa_khong_tua_duoc_van_dung_duoc_khi_da_sang_bai_moi(self):
        # Nhớ «đã tự cứu một lần» theo PHIÊN + LOA, không theo bài: sang bài mới tracker đổi nhưng Stop thật vẫn được tôn trọng.
        self._play(0)
        self._idle(60, ctx(), KHONG_TUA)
        self.assertEqual(1, self.adv._async_advance.call_count)
        self._sang_bai_khac(2)
        self._play(65, position=0)
        self._idle(80, ctx(), KHONG_TUA)
        self.adv._async_remove_speaker.assert_called_once()
        self.assertEqual(1, self.adv._async_advance.call_count)

    def test_bo_nho_da_cuu_het_han_thi_duoc_cuu_lai(self):
        self._play(0)
        self._idle(60, ctx(), KHONG_TUA)
        self._sang_bai_khac(2)
        self._play(65, position=0)
        self._idle(65 + advance_mod.CHO_XAC_NHAN_DUNG_THAT_GIAY + 5, ctx(), KHONG_TUA)
        self.assertEqual(2, self.adv._async_advance.call_count)
        self.adv._async_remove_speaker.assert_not_called()

    def test_hai_phien_khac_nhau_khong_dung_chung_bo_nho(self):
        self._play(0)
        self._idle(60, ctx())
        khac = {**self.session, "session_id": "s2"}
        with self._at(70):
            self.adv._observe(khac, SPEAKER, "playing", attrs(10, self.now), ctx())
        self.adv._advancing.clear()
        with self._at(100):
            self.adv._observe(khac, SPEAKER, "idle", {"supported_features": CO_TUA}, ctx())
        self.assertEqual(2, self.adv._async_resume.call_count)
        self.adv._async_remove_speaker.assert_not_called()


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


if __name__ == "__main__":
    unittest.main()
