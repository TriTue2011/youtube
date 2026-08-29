import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"


def load_actions_module():
    component_package = types.ModuleType("custom_components.tritue_youtube_player")
    component_package.__path__ = [str(COMPONENT_DIR)]
    modules = {"custom_components.tritue_youtube_player": component_package}
    module_name = "custom_components.tritue_youtube_player.actions"
    spec = importlib.util.spec_from_file_location(
        module_name, COMPONENT_DIR / "actions.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable_to_load_actions_module")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


class FakeServices:
    def __init__(self):
        self.calls = []

    async def async_call(
        self, domain, service, service_data=None, *, blocking=False, target=None
    ):
        self.calls.append(
            {
                "domain": domain,
                "service": service,
                "service_data": service_data or {},
                "blocking": blocking,
                "target": target,
            }
        )


class MultiPlayerActionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.actions = load_actions_module()
        self.hass = types.SimpleNamespace(services=FakeServices())
        self.client = types.SimpleNamespace(
            async_play=AsyncMock(
                return_value={
                    "item": {
                        "source": "youtube",
                        "kind": "video",
                        "id": "dQw4w9WgXcQ",
                    },
                    "session_revision": 1,
                }
            ),
            async_create_stream=AsyncMock(
                return_value={
                    "stream_url": "http://192.0.2.10:8099/api/stream/signed",
                    "media_content_type": "audio/mpeg",
                }
            ),
            async_update_session=AsyncMock(
                return_value={"success": True, "session": {"state": "playing"}}
            ),
            async_stop=AsyncMock(return_value={"success": True, "state": "idle"}),
        )

    async def test_youtube_dispatches_for_each_platform_and_sets_group_volume(self):
        result = await self.actions.async_play_on_players(
            self.hass,
            self.client,
            source="youtube",
            target="dQw4w9WgXcQ",
            entity_ids=["media_player.cast", "media_player.other"],
            target_platforms={
                "media_player.cast": "cast",
                "media_player.other": "dlna_dmr",
            },
            target_device_classes={
                "media_player.cast": "tv",
                "media_player.other": None,
            },
            target_supported_features={
                "media_player.cast": 516,
                "media_player.other": 516,
            },
            volume_level=0.35,
        )

        self.assertEqual(1, result["target_count"])
        self.assertEqual(["media_player.other"], result["skipped_targets"])
        self.assertEqual("volume_set", self.hass.services.calls[0]["service"])
        self.assertEqual(
            {"entity_id": ["media_player.cast"]},
            self.hass.services.calls[0]["target"],
        )
        cast_call = self.hass.services.calls[1]
        self.assertEqual("cast", cast_call["service_data"]["media_content_type"])
        self.assertEqual(2, len(self.hass.services.calls))
        self.client.async_update_session.assert_awaited_once_with(
            "youtube",
            "dQw4w9WgXcQ",
            ["media_player.cast"],
            media_content_type=None,
            volume_level=0.35,
        )

    async def test_zing_creates_one_signed_stream_for_all_selected_speakers(self):
        target = "https://zingmp3.vn/bai-hat/Thuc-Giac/ZZ90FD0B.html"
        result = await self.actions.async_play_on_players(
            self.hass,
            self.client,
            source="zing",
            target=target,
            entity_ids=["media_player.living_room", "media_player.kitchen"],
            target_platforms={},
        )

        self.client.async_create_stream.assert_awaited_once_with("zing", target)
        self.assertEqual(
            "audio/mpeg",
            self.hass.services.calls[0]["service_data"]["media_content_type"],
        )
        self.assertEqual(
            {"entity_id": ["media_player.living_room", "media_player.kitchen"]},
            self.hass.services.calls[0]["target"],
        )
        self.assertEqual("zing", result["source"])
        self.client.async_update_session.assert_awaited_once_with(
            "zing",
            target,
            ["media_player.living_room", "media_player.kitchen"],
            media_content_type="audio/mpeg",
            volume_level=None,
        )

    async def test_http_audio_dispatches_and_records_session(self):
        target = "https://audio.example/music/song.flac"

        result = await self.actions.async_play_on_players(
            self.hass,
            self.client,
            source="http",
            target=target,
            entity_ids=["media_player.esp32"],
            target_platforms={"media_player.esp32": "esphome"},
            media_content_type="audio/flac",
        )

        self.assertEqual(
            "audio/flac",
            self.hass.services.calls[0]["service_data"]["media_content_type"],
        )
        self.assertEqual(
            target,
            self.hass.services.calls[0]["service_data"]["media_content_id"],
        )
        self.client.async_create_stream.assert_not_awaited()
        self.client.async_update_session.assert_awaited_once_with(
            "http",
            target,
            ["media_player.esp32"],
            media_content_type="audio/flac",
            volume_level=None,
        )
        self.assertEqual("http", result["source"])

    async def test_http_audio_is_validated_before_volume_or_playback(self):
        with self.assertRaises(ValueError):
            await self.actions.async_play_on_players(
                self.hass,
                self.client,
                source="http",
                target="https://music.youtube.com/watch?v=dQw4w9WgXcQ",
                entity_ids=["media_player.speaker"],
                target_platforms={"media_player.speaker": "cast"},
                target_device_classes={"media_player.speaker": "speaker"},
                target_supported_features={"media_player.speaker": 516},
                volume_level=0.4,
                media_content_type="audio/webm",
            )

        self.assertEqual([], self.hass.services.calls)
        self.client.async_update_session.assert_not_awaited()

    async def test_incompatible_youtube_targets_fail_before_mutating_server(self):
        with self.assertRaises(self.actions.UnsupportedTargetMediaError):
            await self.actions.async_play_on_players(
                self.hass,
                self.client,
                source="youtube",
                target="dQw4w9WgXcQ",
                entity_ids=["media_player.speaker"],
                target_platforms={"media_player.speaker": "cast"},
                target_device_classes={"media_player.speaker": "speaker"},
                target_supported_features={"media_player.speaker": 516},
            )

        self.client.async_play.assert_not_awaited()
        self.assertEqual([], self.hass.services.calls)

    async def test_failed_youtube_dispatch_rolls_back_the_addon_session(self):
        self.hass.services.async_call = AsyncMock(
            side_effect=RuntimeError("cast failed")
        )

        with self.assertRaises(RuntimeError):
            await self.actions.async_play_on_players(
                self.hass,
                self.client,
                source="youtube",
                target="dQw4w9WgXcQ",
                entity_ids=["media_player.cast"],
                target_platforms={"media_player.cast": "cast"},
                target_device_classes={"media_player.cast": "tv"},
                target_supported_features={"media_player.cast": 512},
            )

        self.client.async_stop.assert_awaited_once_with(expected_revision=1)
        self.client.async_update_session.assert_not_awaited()

    async def test_partial_youtube_dispatch_keeps_successful_output_session(self):
        self.hass.services.async_call = AsyncMock(
            side_effect=[None, RuntimeError("second cast failed")]
        )

        result = await self.actions.async_play_on_players(
            self.hass,
            self.client,
            source="youtube",
            target="dQw4w9WgXcQ",
            entity_ids=["media_player.first", "media_player.second"],
            target_platforms={
                "media_player.first": "cast",
                "media_player.second": "cast",
            },
            target_device_classes={
                "media_player.first": "tv",
                "media_player.second": "tv",
            },
            target_supported_features={
                "media_player.first": 512,
                "media_player.second": 512,
            },
        )

        self.assertEqual(1, result["target_count"])
        self.assertEqual(["media_player.second"], result["skipped_targets"])
        self.client.async_stop.assert_not_awaited()
        self.client.async_update_session.assert_awaited_once_with(
            "youtube",
            "dQw4w9WgXcQ",
            ["media_player.first"],
            media_content_type=None,
            volume_level=None,
        )


if __name__ == "__main__":
    unittest.main()
