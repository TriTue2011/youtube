"""`mode` của action/Assist chỉ có hai giá trị CÓ TÁC DỤNG THẬT: audio và video.

Các mức video_360…video_1080 từng được thêm nhưng không tới luồng hình nào ở đường action
(actions.py chỉ phân biệt «audio» với «ứng dụng YouTube gốc») — ô giả, nên bị gỡ. Test này giữ chỗ.
"""
import re
import unittest
from pathlib import Path

from custom_components.tritue_youtube_player.actions import async_play_on_players
from custom_components.tritue_youtube_player.playback import CHON_MODE_HOP_LE

COMP = Path(__file__).resolve().parents[2] / "custom_components" / "tritue_youtube_player"


class ModeHopLeTests(unittest.IsolatedAsyncioTestCase):
    def test_chi_audio_va_video(self):
        self.assertEqual(("audio", "video"), CHON_MODE_HOP_LE)

    def test_services_yaml_khong_co_muc_phan_giai(self):
        yaml_text = (COMP / "services.yaml").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"video_\d{3,4}", yaml_text))
        blocks = re.findall(r"    mode:\n(?:      .*\n|        .*\n|          .*\n|            .*\n)+", yaml_text)
        self.assertGreaterEqual(len(blocks), 3, "ba action phát đều phải có ô mode")
        for block in blocks:
            options = re.findall(r"- (\w+)", block)
            self.assertEqual(["audio", "video"], options)

    async def test_muc_phan_giai_bi_tu_choi_sach(self):
        for bad in ("video_360", "video_720", "video_1080", "2k", "4k", "Audio"):
            with self.subTest(mode=bad):
                with self.assertRaises(ValueError) as cm:
                    await async_play_on_players(
                        None, None, source="youtube",
                        target="dQw4w9WgXcQ",
                        entity_ids=["media_player.x"],
                        target_platforms={"media_player.x": "sonos"},
                        mode=bad,
                    )
                self.assertEqual("invalid_mode", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
