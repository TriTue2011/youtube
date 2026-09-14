import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"


def load_hidden_players_module():
    spec = importlib.util.spec_from_file_location(
        "tritue_youtube_player_hidden_players", COMPONENT_DIR / "hidden_players.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable_to_load_hidden_players_module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class HiddenPlayersTests(unittest.TestCase):
    def setUp(self):
        self.hidden = load_hidden_players_module()

    def test_hide_appends_without_duplicates_and_restore_removes(self):
        current = self.hidden.apply_hidden_change(
            [], ["media_player.phicomm", "media_player.fpt_box"], True
        )
        current = self.hidden.apply_hidden_change(
            current, ["media_player.fpt_box", "media_player.r1_den"], True
        )
        self.assertEqual(
            ["media_player.phicomm", "media_player.fpt_box", "media_player.r1_den"],
            current,
        )
        self.assertEqual(
            ["media_player.r1_den"],
            self.hidden.apply_hidden_change(
                current, ["media_player.phicomm", "media_player.fpt_box"], False
            ),
        )

    def test_rejects_non_player_entities_and_non_boolean_flag(self):
        for entity_ids in (["light.kitchen"], [], "media_player.phicomm", [None]):
            with self.assertRaisesRegex(ValueError, "invalid_target_entity"):
                self.hidden.apply_hidden_change([], entity_ids, True)
        with self.assertRaisesRegex(ValueError, "invalid_hidden_flag"):
            self.hidden.apply_hidden_change([], ["media_player.phicomm"], "true")

    def test_stored_data_is_cleaned_on_load(self):
        self.assertEqual([], self.hidden.normalize_hidden(None))
        self.assertEqual(
            ["media_player.phicomm"],
            self.hidden.normalize_hidden(
                {"entity_ids": ["media_player.phicomm", "light.x", "media_player.phicomm", 3]}
            ),
        )

    def test_size_is_bounded(self):
        many = [f"media_player.p{i}" for i in range(self.hidden.MAX_HIDDEN_PLAYERS)]
        current = self.hidden.apply_hidden_change([], many, True)
        with self.assertRaisesRegex(ValueError, "too_many_hidden_players"):
            self.hidden.apply_hidden_change(current, ["media_player.one_more"], True)


if __name__ == "__main__":
    unittest.main()
