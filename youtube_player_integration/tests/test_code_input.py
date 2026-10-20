"""`clean_code`: làm sạch mã dán vào ô action (hàm thuần)."""

import unittest

from custom_components.tritue_youtube_player.code_input import clean_code


class CleanCodeTests(unittest.TestCase):
    def test_bo_nhan_dung_ten_truong_va_dau_nhay(self):
        for raw, label, want in (
            ("queue_code: media_player.loa", "queue_code", "media_player.loa"),
            ("  Queue_Code:media_player.loa ", "queue_code", "media_player.loa"),
            ("'queue_code: device:b612ec534541f383'", "queue_code", "device:b612ec534541f383"),
            ('"queue_code: \'media_player.loa\'"', "queue_code", "media_player.loa"),
            ("“playlist_code: abcdef012345”", "playlist_code", "abcdef012345"),
            ("media_player.loa", "queue_code", "media_player.loa"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(want, clean_code(raw, label))

    def test_chi_go_nhan_duoc_truyen_vao(self):
        self.assertEqual("playlist_code: x", clean_code("playlist_code: x", "queue_code"))
        self.assertEqual("queue_code: x", clean_code("queue_code: x"))   # không truyền nhãn: không gỡ gì

    def test_khong_nem_voi_gia_tri_la(self):
        for raw in (None, "", 0, [], "queue_code:", "::::"):
            clean_code(raw, "queue_code")
