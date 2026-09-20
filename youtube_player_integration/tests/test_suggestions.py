"""Test kho gợi ý của nhà — từ khoá và bài ghim.

`suggestions.py` khai ngay ở đầu tệp rằng nó chỉ gồm hàm thuần, không nhập gì của
Home Assistant, "so they run in the unit tests". Nhưng tới 20/09/2026 nó KHÔNG có
test chức năng nào: chỉ được soi gián tiếp qua khớp chuỗi trong `test_frontend`.
Đó đúng là lý do lỗ hổng Facebook sống được — `normalize_song` lặng lẽ từ chối mọi
mã không phải 11 ký tự kiểu YouTube, và không ai thấy.
"""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"

#: Mã thật, lấy từ đúng hai nguồn đang chạy — không bịa chuỗi cho vừa khuôn.
MA_YOUTUBE = "kJQP7kiw5Fk"
MA_FACEBOOK = "1964113577722801"


def load_suggestions_module():
    spec = importlib.util.spec_from_file_location(
        "tritue_youtube_player_suggestions", COMPONENT_DIR / "suggestions.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable_to_load_suggestions_module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PinnedSongSourceTests(unittest.TestCase):
    """Bài ghim mang theo NGUỒN, và mỗi nguồn có khuôn mã riêng."""

    def setUp(self):
        self.s = load_suggestions_module()

    def test_ghim_duoc_bai_facebook(self):
        song = self.s.normalize_song(
            {"video_id": MA_FACEBOOK, "source": "facebook", "title": "Nhạc Facebook"}
        )
        self.assertIsNotNone(song)
        self.assertEqual(song["source"], "facebook")
        self.assertEqual(song["id"], MA_FACEBOOK)

    def test_ban_ghi_cu_khong_khai_nguon_van_la_youtube(self):
        """Tương thích ngược: thứ đã lưu trước khi có Facebook không được mất."""
        song = self.s.normalize_song({"video_id": MA_YOUTUBE, "title": "Despacito"})
        self.assertIsNotNone(song)
        self.assertEqual(song["source"], "youtube")

    def test_moi_nguon_mot_khuon_ma_rieng(self):
        """Khuôn lỏng dùng chung là mở cửa cho mã rác của nguồn kia lọt vào."""
        # Mã Facebook mà không khai nguồn -> hiểu là YouTube -> sai khuôn -> từ chối.
        self.assertIsNone(self.s.normalize_song({"video_id": MA_FACEBOOK, "title": "X"}))
        # Mã YouTube mà khai là Facebook -> cũng từ chối.
        self.assertIsNone(
            self.s.normalize_song(
                {"video_id": MA_YOUTUBE, "source": "facebook", "title": "X"}
            )
        )

    def test_nguon_ngoai_danh_sach_bi_tu_choi(self):
        self.assertIsNone(
            self.s.normalize_song(
                {"video_id": MA_FACEBOOK, "source": "zing", "title": "X"}
            )
        )

    def test_ghim_facebook_di_tron_duong_qua_apply_suggestion_change(self):
        """Đo cả đường: bản ghi đi qua bộ chuẩn hoá của kho rồi vẫn còn nguồn."""
        hien_tai = self.s.normalize_suggestions(
            {"groups": [{"id": "nhac-nha", "name": "Nhạc nhà", "songs": []}]}
        )
        sau = self.s.apply_suggestion_change(
            hien_tai,
            {
                "action": "pin_song",
                "id": "nhac-nha",
                "item": {
                    "video_id": MA_FACEBOOK,
                    "source": "facebook",
                    "title": "Bài Facebook",
                },
            },
        )
        nhom = next(g for g in sau["groups"] if g["id"] == "nhac-nha")
        self.assertEqual([b["id"] for b in nhom["songs"]], [MA_FACEBOOK])
        self.assertEqual(nhom["songs"][0]["source"], "facebook")


if __name__ == "__main__":
    unittest.main()
