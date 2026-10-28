"""Lý do loa về idle (hết bài / dừng / lỗi / bị đè): tín hiệu thật của loa thắng việc đoán bằng thời lượng bài.

Chủ máy 28/10/2026: «Stop hay không thì lấy event hoặc trigger gì đó là được mà nhỉ» — cả loa (R1), cam và Cast. DLNA và AirPlay
không có mã lý do tin cậy nên vẫn dùng thời lượng bài (xem docstring của ly_do_idle.py)."""
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import custom_components.tritue_youtube_player.advance as advance_mod
from custom_components.tritue_youtube_player import ly_do_idle
from custom_components.tritue_youtube_player.ly_do_idle import BI_DE, DUNG, HET_BAI, LOI, doc_ly_do_idle
from homeassistant.components.media_player import DATA_COMPONENT

T0 = datetime(2026, 10, 28, 6, 0, 0, tzinfo=timezone.utc)
SPEAKER = "media_player.loa_thu"
ITEM = {"id": "dQw4w9WgXcQ", "duration": 240, "source": "youtube"}
SEEK = 2


def cast_hass(entity):
    component = MagicMock()
    component.get_entity.return_value = entity
    return types.SimpleNamespace(data={DATA_COMPONENT: component})


def cast_entity(reason, idle=True, domain="cast"):
    status = types.SimpleNamespace(player_is_idle=idle, idle_reason=reason)
    return types.SimpleNamespace(platform=types.SimpleNamespace(domain=domain), media_status=status)


class DocLyDoIdleTests(unittest.TestCase):
    def test_thuoc_tinh_idle_reason_cua_loa_tu_viet(self):
        hass = types.SimpleNamespace(data={})
        for gia_tri, mong_doi in (("finished", HET_BAI), ("Stopped", DUNG), ("error", LOI), ("interrupted", BI_DE), ("la", None)):
            self.assertEqual(mong_doi, doc_ly_do_idle(hass, SPEAKER, {"idle_reason": gia_tri}), gia_tri)

    def test_cast_doc_tu_media_status(self):
        for ma, mong_doi in (("FINISHED", HET_BAI), ("CANCELLED", DUNG), ("ERROR", LOI), ("INTERRUPTED", BI_DE), (None, None)):
            self.assertEqual(mong_doi, doc_ly_do_idle(cast_hass(cast_entity(ma)), SPEAKER, {}), ma)

    def test_cast_chua_idle_hoac_khong_phai_cast_thi_khong_doc(self):
        self.assertIsNone(doc_ly_do_idle(cast_hass(cast_entity("FINISHED", idle=False)), SPEAKER, {}))
        self.assertIsNone(doc_ly_do_idle(cast_hass(cast_entity("FINISHED", domain="dlna_dmr")), SPEAKER, {}))
        self.assertIsNone(doc_ly_do_idle(cast_hass(None), SPEAKER, {}))

    def test_thieu_thanh_phan_ben_trong_ha_thi_khong_vo(self):
        self.assertIsNone(doc_ly_do_idle(types.SimpleNamespace(data={}), SPEAKER, {}))
        component = MagicMock()
        component.get_entity.side_effect = RuntimeError("đổi cấu trúc")
        self.assertIsNone(doc_ly_do_idle(types.SimpleNamespace(data={DATA_COMPONENT: component}), SPEAKER, {}))


class AdvanceTheoLyDoTests(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock()
        self.hass.async_create_task = MagicMock(side_effect=lambda coro, **kw: None)
        self.adv = advance_mod.SessionAutoAdvance(self.hass, MagicMock())
        self.adv._async_resume = MagicMock(return_value="resume")
        self.adv._async_remove_speaker = MagicMock(return_value="remove")
        self.adv._async_advance = MagicMock(return_value="advance")
        self.adv._next_from = MagicMock(return_value="queue")
        self.session = {"session_id": "s1", "item": dict(ITEM), "queue": {"index": 0}}

    def _attrs(self, seconds, **them):
        return {"media_content_id": ITEM["id"], "media_position": 10, "supported_features": SEEK,
                "media_position_updated_at": (T0 + timedelta(seconds=seconds)).isoformat(), **them}

    def _play(self, seconds=0):
        with patch.object(advance_mod.dt_util, "utcnow", return_value=T0 + timedelta(seconds=seconds)):
            self.adv._observe(self.session, SPEAKER, "playing", self._attrs(seconds), None)

    def _idle(self, seconds, ly_do, features=SEEK):
        self.adv._advancing.clear()
        attrs = {"supported_features": features, "idle_reason": ly_do} if ly_do else {"supported_features": features}
        with patch.object(advance_mod.dt_util, "utcnow", return_value=T0 + timedelta(seconds=seconds)):
            self.adv._observe(self.session, SPEAKER, "idle", attrs, None)

    def _chi(self, **mong_doi):
        for ten, so_lan in mong_doi.items():
            self.assertEqual(so_lan, getattr(self.adv, f"_async_{ten}").call_count, ten)

    def test_loa_khai_het_bai_giua_bai_van_sang_bai_ke(self):
        """Loa nói «hết bài» thì tin loa, dù vị trí chưa tới cuối (thời lượng đo sai)."""
        self._play(0)
        self._idle(60, "finished")
        self._chi(advance=1, remove_speaker=0, resume=0)

    def test_loa_khai_dung_sat_cuoi_bai_van_la_stop(self):
        self._play(0)
        self._idle(235, "stopped")                       # theo thời lượng thì là hết bài; loa nói là Stop
        self._chi(advance=0, remove_speaker=1, resume=0)

    def test_bai_khong_biet_thoi_luong_nhung_loa_khai_het_bai(self):
        self.session = {**self.session, "item": {**ITEM, "duration": 0}}
        self._play(0)
        self._idle(200, "finished")
        self._chi(advance=1, remove_speaker=0)

    def test_bai_khong_biet_thoi_luong_nhung_loa_khai_dung(self):
        self.session = {**self.session, "item": {**ITEM, "duration": 0}}
        self._play(0)
        self._idle(200, "stopped")
        self._chi(advance=0, remove_speaker=1)

    def test_loa_bi_noi_dung_khac_de_thi_go_loa(self):
        self._play(0)
        self._idle(60, "interrupted")
        self._chi(remove_speaker=1, resume=0, advance=0)

    def test_loi_luong_phat_tiep_dung_cho_mot_lan(self):
        self._play(0)
        self._idle(60, "error")
        self._chi(resume=1, remove_speaker=0)
        vi_tri = self.adv._async_resume.call_args.args[2]
        self.assertAlmostEqual(70.0, vi_tri, delta=1)

    def test_loi_lan_hai_ngay_sau_do_thi_go_loa(self):
        self._play(0)
        self._idle(60, "error")
        self._play(65)
        self._idle(80, "error")
        self._chi(resume=1, remove_speaker=1)

    def test_loi_loa_khong_tua_duoc_thi_sang_bai_ke(self):
        self._play(0)
        self._idle(60, "error", features=4)
        self._chi(advance=1, resume=0, remove_speaker=0)

    def test_loa_khong_khai_thi_dung_thoi_luong_nhu_cu(self):
        self._play(0)
        self._idle(60, None)                             # giữa bài, biết thời lượng → Stop
        self._chi(remove_speaker=1, advance=0)
        self.adv._async_remove_speaker.reset_mock()
        self.session = {"session_id": "s2", "item": dict(ITEM), "queue": {"index": 0}}
        self._play(100)
        self._idle(335, None)                            # sát cuối bài → hết bài
        self._chi(advance=1)

    def test_loa_dang_phat_roi_moi_doc_ly_do(self):
        """Loa chưa từng phát bài này mà idle thì không có gì để đọc, kể cả khi thuộc tính còn sót lý do cũ."""
        self._idle(5, "stopped")
        self._chi(advance=0, remove_speaker=0, resume=0)


if __name__ == "__main__":
    unittest.main()
