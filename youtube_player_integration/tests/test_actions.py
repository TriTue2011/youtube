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
    @staticmethod
    async def _record(source, target, outputs, **kwargs):
        """Echo the player server: the session reserved for these speakers."""
        item = (
            {"source": "youtube", "kind": "video", "id": "dQw4w9WgXcQ"}
            if source == "youtube"
            else {"source": source, "id": target}
        )
        return {
            "success": True,
            "session": {
                "state": "playing",
                "session_id": kwargs.get("session_id") or "s1",
                "revision": 7,
                "output_entity_ids": list(outputs),
                "item": item,
            },
        }

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
            async_update_session=AsyncMock(side_effect=self._record),
            async_stop=AsyncMock(return_value={"success": True, "state": "idle"}),
        )

    async def test_youtube_casts_to_tv_and_streams_audio_to_speaker(self):
        result = await self.actions.async_play_on_players(
            self.hass,
            self.client,
            source="youtube",
            target="dQw4w9WgXcQ",
            entity_ids=["media_player.cast", "media_player.speaker"],
            target_platforms={
                "media_player.cast": "cast",
                "media_player.speaker": "dlna_dmr",
            },
            target_device_classes={
                "media_player.cast": "tv",
                "media_player.speaker": "speaker",
            },
            target_supported_features={
                "media_player.cast": 516,
                "media_player.speaker": 516,
            },
            volume_level=0.35,
        )

        self.assertEqual(2, result["target_count"])
        self.assertEqual([], result["skipped_targets"])
        services = self.hass.services.calls
        self.assertEqual("volume_set", services[0]["service"])
        self.assertEqual(
            {"entity_id": ["media_player.cast", "media_player.speaker"]},
            services[0]["target"],
        )
        play_calls = [call for call in services if call["service"] == "play_media"]
        cast_call = next(
            call for call in play_calls
            if call["target"] == {"entity_id": "media_player.cast"}
        )
        self.assertEqual("cast", cast_call["service_data"]["media_content_type"])
        speaker_call = next(
            call for call in play_calls
            if call["target"] == {"entity_id": "media_player.speaker"}
        )
        self.assertEqual(
            "http://192.0.2.10:8099/api/stream/signed",
            speaker_call["service_data"]["media_content_id"],
        )
        self.assertEqual(
            "audio/mpeg", speaker_call["service_data"]["media_content_type"]
        )
        self.client.async_create_stream.assert_awaited_once_with(
            "youtube", "dQw4w9WgXcQ"
        )
        # Reserve the session (moves these speakers out of other sessions), then
        # record the stream type in the same session.
        self.assertEqual(
            [
                (("youtube", "dQw4w9WgXcQ", ["media_player.cast", "media_player.speaker"]),
                 {"media_content_type": None, "volume_level": 0.35, "session_id": None, "controller": None}),
                (("youtube", "dQw4w9WgXcQ", ["media_player.cast", "media_player.speaker"]),
                 {"media_content_type": "audio/mpeg", "volume_level": 0.35, "session_id": "s1", "controller": None}),
            ],
            [(c.args, c.kwargs) for c in self.client.async_update_session.await_args_list],
        )
        self.assertEqual("s1", result["session_id"])
        self.client.async_play.assert_not_awaited()

    async def test_youtube_launches_native_app_on_lg_webos_tv(self):
        result = await self.actions.async_play_on_players(
            self.hass,
            self.client,
            source="youtube",
            target="dQw4w9WgXcQ",
            entity_ids=["media_player.lg_tv"],
            target_platforms={"media_player.lg_tv": "webostv"},
            target_device_classes={"media_player.lg_tv": "tv"},
            target_supported_features={"media_player.lg_tv": 24381},
        )

        self.assertEqual(1, result["target_count"])
        calls = self.hass.services.calls
        self.assertEqual(
            [("webostv", "command", {"entity_id": "media_player.lg_tv"})],
            [(c["domain"], c["service"], c["target"]) for c in calls],
        )
        self.assertEqual(
            {"id": "youtube.leanback.v4", "contentId": "dQw4w9WgXcQ"},
            calls[0]["service_data"]["payload"],
        )
        self.client.async_create_stream.assert_not_awaited()

    async def test_youtube_streams_audio_to_a_screenless_speaker(self):
        result = await self.actions.async_play_on_players(
            self.hass,
            self.client,
            source="youtube",
            target="dQw4w9WgXcQ",
            entity_ids=["media_player.esp32"],
            target_platforms={"media_player.esp32": "esphome"},
            target_device_classes={"media_player.esp32": "speaker"},
            target_supported_features={"media_player.esp32": 516},
        )

        self.client.async_play.assert_not_awaited()
        self.client.async_create_stream.assert_awaited_once_with(
            "youtube", "dQw4w9WgXcQ"
        )
        play_call = self.hass.services.calls[-1]
        self.assertEqual("play_media", play_call["service"])
        self.assertEqual(
            "http://192.0.2.10:8099/api/stream/signed",
            play_call["service_data"]["media_content_id"],
        )
        self.assertEqual(1, result["target_count"])

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
        self.assertEqual(
            {"media_content_type": "audio/mpeg", "volume_level": None, "session_id": "s1", "controller": None},
            self.client.async_update_session.await_args_list[-1].kwargs,
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
            session_id=None,
            controller=None,
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

    async def test_youtube_targets_without_play_media_fail_before_mutating_server(self):
        with self.assertRaises(self.actions.UnsupportedTargetMediaError):
            await self.actions.async_play_on_players(
                self.hass,
                self.client,
                source="youtube",
                target="dQw4w9WgXcQ",
                entity_ids=["media_player.screenless"],
                target_platforms={"media_player.screenless": "dlna_dmr"},
                target_device_classes={"media_player.screenless": "speaker"},
                target_supported_features={"media_player.screenless": 0},
            )

        self.client.async_update_session.assert_not_awaited()
        self.client.async_create_stream.assert_not_awaited()
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

        # Nothing played: the reserved session is stopped again.
        self.client.async_stop.assert_awaited_once_with(session_id="s1")
        self.client.async_update_session.assert_awaited_once()

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
        final = self.client.async_update_session.await_args_list[-1]
        self.assertEqual(["media_player.first"], final.args[2])
        self.assertEqual("s1", final.kwargs["session_id"])

    async def test_joining_speaker_gets_the_song_others_keep_playing(self):
        result = await self.actions.async_play_on_players(
            self.hass,
            self.client,
            source="zing",
            target="https://zingmp3.vn/bai-hat/Thuc-Giac/ZZ90FD0B.html",
            entity_ids=["media_player.kitchen"],
            target_platforms={},
            session_id="s9",
            controller="ha:abc",
            join_entity_ids=["media_player.living_room"],
        )

        self.assertEqual(
            {"entity_id": ["media_player.kitchen"]}, self.hass.services.calls[0]["target"]
        )
        first = self.client.async_update_session.await_args_list[0]
        self.assertEqual(["media_player.living_room", "media_player.kitchen"], first.args[2])
        self.assertEqual(("s9", "ha:abc"), (first.kwargs["session_id"], first.kwargs["controller"]))
        self.assertEqual("s9", result["session_id"])


if __name__ == "__main__":
    unittest.main()
