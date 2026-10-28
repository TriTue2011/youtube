"""N5: schema (voluptuous THẬT) === services.yaml === strings.json cho MỌI action.

- Khoá trường và cờ bắt buộc/tuỳ chọn phải trùng nhau ở 3 nơi.
- Selector options của các trường select phải bao gồm mọi giá trị mà schema chấp nhận.
"""

import json
import unittest
from pathlib import Path

import voluptuous as vol
import yaml

import custom_components.tritue_youtube_player.services as services_mod

COMPONENT_DIR = Path(__file__).resolve().parents[2] / "custom_components" / "tritue_youtube_player"

SCHEMA_BY_ACTION = {
    "play_on_players": services_mod.PLAY_ON_PLAYERS_SCHEMA,
    "play_playlist": services_mod.PLAY_PLAYLIST_SCHEMA,
    "play_queue": services_mod.PLAY_QUEUE_SCHEMA,
    "skip": services_mod.SKIP_SCHEMA,
    "stop_session": services_mod.STOP_SESSION_SCHEMA,
    "remove_players": services_mod.REMOVE_PLAYERS_SCHEMA,
    "set_sync_adjust": services_mod.SET_SYNC_ADJUST_SCHEMA,
}


def _schema_fields(schema):
    """{tên trường: bắt buộc?} trích bằng voluptuous THẬT."""
    out = {}
    for marker in schema.schema:
        name = marker.key if hasattr(marker, "key") else str(marker)
        out[name] = isinstance(marker, vol.Required)
    return out


class ServiceConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.services_yaml = yaml.safe_load(
            (COMPONENT_DIR / "services.yaml").read_text(encoding="utf-8")
        )
        cls.strings = json.loads(
            (COMPONENT_DIR / "strings.json").read_text(encoding="utf-8")
        )

    def test_n5_schema_bang_yaml_khoa_truong_va_bat_buoc(self):
        """N5: khoá trường + bắt buộc/tuỳ chọn schema phải trùng services.yaml."""
        for action, schema in SCHEMA_BY_ACTION.items():
            with self.subTest(action=action):
                expected = _schema_fields(schema)
                yaml_fields = self.services_yaml[action]["fields"]
                self.assertEqual(
                    set(expected), set(yaml_fields),
                    f"{action}: khoá trường schema != services.yaml",
                )
                for name, required in expected.items():
                    self.assertEqual(
                        required,
                        bool(yaml_fields[name].get("required", False)),
                        f"{action}.{name}: bắt buộc/tuỳ chọn lệch schema/services.yaml",
                    )

    def test_n5_schema_bang_strings_khoa_truong(self):
        """N5: khoá trường schema phải trùng strings.json (required do services.yaml quyết)."""
        for action, schema in SCHEMA_BY_ACTION.items():
            with self.subTest(action=action):
                expected = _schema_fields(schema)
                string_fields = self.strings["services"][action]["fields"]
                self.assertEqual(
                    set(expected), set(string_fields),
                    f"{action}: khoá trường schema != strings.json",
                )

    def test_n1_mode_khong_default(self):
        """N1: schema/yaml `mode` KHÔNG có default (HA tự điền «audio» làm TV Cast nhận audio/mpeg)."""
        for action, schema in SCHEMA_BY_ACTION.items():
            with self.subTest(action=action):
                yaml_fields = self.services_yaml[action]["fields"]
                for marker in schema.schema:
                    name = marker.key if hasattr(marker, "key") else str(marker)
                    if name == "mode":
                        self.assertIs(
                            vol.UNDEFINED,
                            marker.default,
                            f"{action}: schema mode có default (hồi quy N1)",
                        )
                        self.assertNotIn(
                            "default", yaml_fields["mode"],
                            f"{action}: services.yaml mode có default",
                        )
        # Schema không tự điền mode khi gọi thiếu
        data = services_mod.PLAY_ON_PLAYERS_SCHEMA(
            {
                "entry_id": "e1",
                "source": "youtube",
                "target": "dQw4w9WgXcQ",
                "entity_id": ["media_player.a"],
            }
        )
        self.assertNotIn("mode", data)

    def test_n5_source_selector_bao_gom_moi_gia_tri_schema(self):
        """N5: selector options của source phải bao gồm mọi giá trị schema chấp nhận."""
        schema = services_mod.PLAY_ON_PLAYERS_SCHEMA
        schema_vals = None
        for marker, validator in schema.schema.items():
            name = marker.key if hasattr(marker, "key") else str(marker)
            if name == "source" and isinstance(validator, vol.In):
                schema_vals = set(validator.container)
        self.assertIsNotNone(schema_vals)
        options = self.services_yaml["play_on_players"]["fields"]["source"][
            "selector"
        ]["select"]["options"]
        self.assertTrue(
            schema_vals <= set(options),
            f"source: schema chấp nhận {sorted(schema_vals)} nhưng selector thiếu {sorted(schema_vals - set(options))}",
        )


if __name__ == "__main__":
    unittest.main()
