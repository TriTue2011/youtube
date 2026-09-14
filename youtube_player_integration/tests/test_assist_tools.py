import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"


def load_module():
    spec = importlib.util.spec_from_file_location("tritue_assist_tools", COMPONENT_DIR / "assist_tools.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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

    def test_results_are_numbered_and_bounded(self):
        items = [{"title": f"Bai {n}", "channel": "K", "duration": 3725 if n == 1 else 216} for n in range(1, 15)]
        numbered = self.tools.numbered_results(items)
        self.assertEqual(10, len(numbered))
        self.assertEqual({"so": 1, "ten": "Bai 1", "kenh": "K", "thoi_luong": "1:02:05"}, numbered[0])
        self.assertEqual("3:36", numbered[1]["thoi_luong"])


if __name__ == "__main__":
    unittest.main()
