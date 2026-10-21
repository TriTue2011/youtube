"""NV203 — integration: phát Facebook ra loa bằng action đi đường luồng chuyển tiếp.

ĐO: action play_playlist/play_queue với bài Facebook phải gửi play_media tới
loa (đường luồng đã ký), như Zing — không rơi vào nhánh YouTube gốc im lặng.
"""
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


class FacebookDispatchTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    async def _record(source, target, outputs, **kwargs):
        return {
            "success": True,
            "session": {
                "state": "playing",
                "session_id": kwargs.get("session_id") or "s1",
                "revision": 7,
                "output_entity_ids": list(outputs),
                "item": {"source": source, "kind": "video", "id": target, "duration": 0},
            },
        }

    def setUp(self):
        self.actions = load_actions_module()
        self.hass = types.SimpleNamespace(services=FakeServices())
        self.client = types.SimpleNamespace(
            async_create_stream=AsyncMock(
                return_value={
                    "stream_url": "http://192.0.2.10:8099/api/stream/signed",
                    "media_content_type": "audio/mpeg",
                    "duration": 187,
                }
            ),
            base_url="http://192.0.2.10:8099",
            async_update_session=AsyncMock(side_effect=self._record),
            async_stop=AsyncMock(return_value={"success": True, "state": "idle"}),
        )

    async def test_facebook_gui_luong_chuyen_tiep_toi_loa(self):
        result = await self.actions.async_play_on_players(
            self.hass,
            self.client,
            source="facebook",
            target="1807802260572674",
            entity_ids=["media_player.loa"],
            target_platforms={"media_player.loa": "dlna_dmr"},
            target_device_classes={"media_player.loa": "speaker"},
            target_supported_features={"media_player.loa": 516},
        )
        self.assertEqual(1, result["target_count"])
        self.assertEqual([], result["skipped_targets"])
        self.assertEqual("s1", result["session_id"])
        play_calls = [
            call for call in self.hass.services.calls if call["service"] == "play_media"
        ]
        self.assertEqual(1, len(play_calls))
        self.assertEqual(
            "http://192.0.2.10:8099/api/stream/signed",
            play_calls[0]["service_data"]["media_content_id"],
        )
        self.assertEqual(
            "audio/mpeg", play_calls[0]["service_data"]["media_content_type"]
        )
        self.client.async_create_stream.assert_awaited_once()
        self.assertEqual(
            ("facebook", "1807802260572674"),
            self.client.async_create_stream.await_args.args,
        )


if __name__ == "__main__":
    unittest.main()
