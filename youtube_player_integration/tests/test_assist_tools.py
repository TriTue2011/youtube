import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"


def load_module():
    from custom_components.tritue_youtube_player import assist_tools
    return assist_tools


SPEAKERS = [
    {"entity_id": "media_player.bep", "name": "Bếp"},
    {"entity_id": "media_player.phong_khach", "name": "Phòng khách"},
    {"entity_id": "media_player.lg_tv", "name": "Ti vi phòng ngủ"},
]


class AssistToolTests(unittest.TestCase):
    def setUp(self):
        self.tools = load_module()

    def test_speakers_are_matched_loosely(self):
        match = self.tools.match_speakers
        every = [s["entity_id"] for s in SPEAKERS]
        for words in ("tất cả", "Tat ca loa", "all", ""):
            self.assertEqual((every, []), match(words, SPEAKERS), words)
        self.assertEqual((["media_player.phong_khach", "media_player.bep"], []), match("phong khach và bếp", SPEAKERS))
        self.assertEqual((["media_player.bep", "media_player.lg_tv"], []), match("loa 1, 3", SPEAKERS))
        self.assertEqual((["media_player.lg_tv"], []), match("tivi phòng ngủ", SPEAKERS))
        self.assertEqual((["media_player.bep"], ["gac xep"]), match("bếp, gác xép", SPEAKERS))
        # A name that itself starts with a device word ("Tivi LG") still matches.
        lg = [{"entity_id": "media_player.lg", "name": "Tivi LG"}, *SPEAKERS]
        self.assertEqual((["media_player.lg", "media_player.phong_khach"], []), match("tivi lg và loa phòng khách", lg))

    def test_results_are_numbered_and_bounded(self):
        items = [{"title": f"Bai {n}", "channel": "K", "duration": 3725 if n == 1 else 216} for n in range(1, 15)]
        numbered = self.tools.numbered_results(items)
        self.assertEqual(10, len(numbered))
        self.assertEqual({"so": 1, "ten": "Bai 1", "kenh": "K", "thoi_luong": "1:02:05"}, numbered[0])
        self.assertEqual("3:36", numbered[1]["thoi_luong"])

    def test_playlist_matching_and_formatting(self):
        playlists = [
            {"id": "pl-1", "name": "Nhạc Trẻ Hay", "items": [{"id": "v1"}, {"id": "v2"}]},
            {"id": "pl-2", "name": "Bolero Chọn Lọc", "items": [{"id": "v3"}]},
        ]
        # Match by number
        self.assertEqual(playlists[0], self.tools.match_playlist("1", playlists))
        self.assertEqual(playlists[1], self.tools.match_playlist("2", playlists))
        # Match by id
        self.assertEqual(playlists[1], self.tools.match_playlist("pl-2", playlists))
        # Match by loose name
        self.assertEqual(playlists[0], self.tools.match_playlist("nhac tre", playlists))
        self.assertEqual(playlists[1], self.tools.match_playlist("bolero", playlists))
        # Bad input / not found
        self.assertIsNone(self.tools.match_playlist("khong co", playlists))
        self.assertIsNone(self.tools.match_playlist("99", playlists))
        self.assertIsNone(self.tools.match_playlist("-1", playlists))
        self.assertIsNone(self.tools.match_playlist("", playlists))
        self.assertIsNone(self.tools.match_playlist(None, playlists))

        # Formatting
        formatted = self.tools.format_playlists(playlists)
        self.assertEqual(2, len(formatted))
        self.assertEqual({"so": 1, "id": "pl-1", "ten": "Nhạc Trẻ Hay", "so_bai": 2}, formatted[0])

    def test_queue_formatting_and_item_matching(self):
        queue = {
            "items": [
                {"uid": "u1", "id": "dQw4w9WgXcQ", "title": "Bài 1", "artist": "Ca sĩ A", "duration_seconds": 210},
                {"uid": "u2", "id": "kJQP7kiw5Fk", "title": "Bài 2", "artist": "Ca sĩ B", "duration_seconds": 180},
            ],
            "current": "u2",
            "mode": "video",
            "order": "shuffle",
        }
        res = self.tools.format_queue(queue)
        self.assertEqual(2, res["tong_so"])
        self.assertEqual("video", res["che_do"])
        self.assertEqual("tron_bai", res["thu_tu"])
        self.assertFalse(res["bai_hat"][0]["dang_phat"])
        self.assertTrue(res["bai_hat"][1]["dang_phat"])
        self.assertEqual("3:30", res["bai_hat"][0]["thoi_luong"])

        # Match queue item by number 1..N
        self.assertEqual(queue["items"][0], self.tools.match_queue_item("1", queue))
        self.assertEqual(queue["items"][1], self.tools.match_queue_item("2", queue))
        # Match by uid
        self.assertEqual(queue["items"][0], self.tools.match_queue_item("u1", queue))
        # Match by loose title
        self.assertEqual(queue["items"][1], self.tools.match_queue_item("bai 2", queue))
        # Bad input
        self.assertIsNone(self.tools.match_queue_item("0", queue))
        self.assertIsNone(self.tools.match_queue_item("5", queue))
        self.assertIsNone(self.tools.match_queue_item("khong_co", queue))

    def test_parse_safe_integer(self):
        parse = self.tools.parse_safe_integer
        self.assertEqual(1, parse(1))
        self.assertEqual(1, parse("1"))
        self.assertEqual(10, parse("10"))
        # Unicode superscript digit
        self.assertIsNone(parse("²"))
        # Huge digit string
        self.assertIsNone(parse("9" * 5000))
        # Invalid inputs
        self.assertIsNone(parse(True))
        self.assertIsNone(parse(False))
        self.assertIsNone(parse("0"))
        self.assertIsNone(parse("-1"))
        self.assertIsNone(parse("abc"))
        self.assertIsNone(parse(None))

    def test_playlist_matching_multiple_returns_candidates(self):
        playlists = [
            {"id": "pl-1", "name": "Nhạc Trịnh 1", "items": [{"id": "v1"}]},
            {"id": "pl-2", "name": "Nhạc Trịnh 2", "items": [{"id": "v2"}]},
            {"id": "pl-3", "name": "Bolero", "items": [{"id": "v3"}]},
        ]
        # Single clear match
        self.assertEqual(playlists[2], self.tools.match_playlist("bolero", playlists))
        # Multiple matches must return candidates list, NOT picking the first one
        matched = self.tools.match_playlist("Nhạc Trịnh", playlists)
        self.assertIsInstance(matched, list, "Multiple matches should return candidate list")
        self.assertEqual(2, len(matched))

    def test_queue_matching_multiple_and_safe_integer(self):
        queue = {
            "items": [
                {"uid": "u1", "id": "dQw4w9WgXcQ", "title": "Bài Nhạc 1", "duration_seconds": 120},
                {"uid": "u2", "id": "kJQP7kiw5Fk", "title": "Bài Nhạc 2", "duration_seconds": 180},
            ]
        }
        # Safe integer inputs
        self.assertEqual(queue["items"][0], self.tools.match_queue_item("1", queue))
        self.assertIsNone(self.tools.match_queue_item("²", queue))
        self.assertIsNone(self.tools.match_queue_item("9" * 5000, queue))
        # Multiple matches
        matched = self.tools.match_queue_item("Bài Nhạc", queue)
        self.assertIsInstance(matched, list, "Multiple matches in queue should return list")
        self.assertEqual(2, len(matched))

    def test_extract_item_id_invalid_host(self):
        """M3: extract_item_id must reject invalid or malicious hosts."""
        extract = self.tools.extract_item_id
        # Host lạ
        self.assertIsNone(extract("http://evil.example/?v=dQw4w9WgXcQ"))
        self.assertIsNone(extract("https://evil.example/watch?v=dQw4w9WgXcQ"))
        self.assertIsNone(extract("https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ"))
        self.assertIsNone(extract("http://notyoutube.com/watch?v=dQw4w9WgXcQ"))

    def test_extract_item_id_security_and_valid_cases(self):
        """Security and edge case validation for extract_item_id."""
        extract = self.tools.extract_item_id
        # javascript:
        self.assertIsNone(extract("javascript:alert(1)"))
        self.assertIsNone(extract("javascript:void(0)"))
        # //host/...
        self.assertIsNone(extract("//youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertIsNone(extract("//evil.example/watch?v=dQw4w9WgXcQ"))
        # userinfo user@host
        self.assertIsNone(extract("http://user@youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertIsNone(extract("https://user:pass@youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertIsNone(extract("https://youtube.com@evil.example/watch?v=dQw4w9WgXcQ"))
        # chuỗi dài 10k
        self.assertIsNone(extract("https://www.youtube.com/watch?v=dQw4w9WgXcQ&x=" + "a" * 10000))
        self.assertIsNone(extract("a" * 10000))
        # có \n
        self.assertIsNone(extract("https://www.youtube.com/watch?v=dQw4w9WgXcQ\n&x=1"))
        self.assertIsNone(extract("dQw4w9W\ngXc"))
        # có ..
        self.assertIsNone(extract("https://www.youtube.com/watch/../watch?v=dQw4w9WgXcQ"))
        self.assertIsNone(extract("../dQw4w9WgXcQ"))
        # id đúng khuôn
        self.assertEqual("dQw4w9WgXcQ", extract("dQw4w9WgXcQ"))
        self.assertEqual("kJQP7kiw5Fk", extract("kJQP7kiw5Fk"))
        # URL watch?v= đúng
        self.assertEqual("dQw4w9WgXcQ", extract("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertEqual("dQw4w9WgXcQ", extract("http://m.youtube.com/watch?v=dQw4w9WgXcQ&feature=share"))
        self.assertEqual("dQw4w9WgXcQ", extract("https://music.youtube.com/watch?v=dQw4w9WgXcQ"))
        # URL youtu.be/ đúng
        self.assertEqual("dQw4w9WgXcQ", extract("https://youtu.be/dQw4w9WgXcQ"))
        self.assertEqual("dQw4w9WgXcQ", extract("http://youtu.be/dQw4w9WgXcQ?t=10"))
        # shorts/embed
        self.assertEqual("dQw4w9WgXcQ", extract("https://www.youtube.com/shorts/dQw4w9WgXcQ"))
        self.assertEqual("dQw4w9WgXcQ", extract("https://www.youtube.com/embed/dQw4w9WgXcQ"))
        # nguồn khác youtube
        self.assertIsNone(extract("dQw4w9WgXcQ", source="zing"))
        self.assertIsNone(extract("https://www.youtube.com/watch?v=dQw4w9WgXcQ", source="zing"))
        # None / rỗng
        self.assertIsNone(extract(None))
        self.assertIsNone(extract(""))


if __name__ == "__main__":
    unittest.main()
