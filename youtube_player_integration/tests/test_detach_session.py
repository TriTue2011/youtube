"""N10: detach_session_queue must run when a session ends (async_stop_session).

Without this the module-level _SESSION_QUEUES map grows unboundedly
(attach is called on every play, detach was dead code).
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[2]

from custom_components.tritue_youtube_player import services as services_mod
from custom_components.tritue_youtube_player import sessions as sessions_mod
from custom_components.tritue_youtube_player import playback as playback_mod


class DetachOnStopTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        sessions_mod._SESSION_QUEUES.clear()
        self.client = types.SimpleNamespace(
            async_stop=AsyncMock(return_value={"success": True}),
        )
        self.session = {
            "session_id": "s9",
            "state": "playing",
            "output_entity_ids": ["media_player.living_room"],
        }
        self.runtime_data = types.SimpleNamespace(
            data={"sessions": [self.session]},
            client=self.client,
            async_refresh=AsyncMock(),
        )
        self.entry = types.SimpleNamespace(runtime_data=self.runtime_data)
        state = types.SimpleNamespace(
            state="idle", attributes={"supported_features": 512}
        )
        self.hass = types.SimpleNamespace(
            states=types.SimpleNamespace(get=lambda entity_id: state),
            services=types.SimpleNamespace(async_call=AsyncMock()),
        )

    def tearDown(self):
        sessions_mod._SESSION_QUEUES.clear()

    async def test_n10_dung_phien_thi_go_khoa_hang_doi(self):
        """N10: stopping a session detaches its queue key (no unbounded growth)."""
        sessions_mod.attach_session_queue("s9", "media_player.living_room")
        self.assertEqual(
            "media_player.living_room",
            sessions_mod.session_queue_key({"session_id": "s9"}),
        )
        await services_mod.async_stop_session(self.hass, self.entry, "s9")
        self.assertNotIn("s9", sessions_mod._SESSION_QUEUES)
        self.assertIsNone(sessions_mod.session_queue_key({"session_id": "s9"}))

    async def test_n4_async_play_queue_gan_khoa_hang_doi_vao_phien(self):
        """N4: async_play_queue gắn mã hàng đợi vào phiên để advance dùng đúng hàng đợi."""
        from custom_components.tritue_youtube_player import queue as q_mod
        from custom_components.tritue_youtube_player import queue_store as qs_mod

        # Store thật của Home Assistant đọc hass.config.config_dir lúc khởi tạo (không chạm đĩa);
        # bản HA giả không cần, bản thật thì cần — nên khai sẵn để test chạy được với cả hai.
        hass = types.SimpleNamespace(
            data={}, config=types.SimpleNamespace(config_dir="/nonexistent-config-for-test")
        )
        store = qs_mod.QueueStore(hass)
        doc = q_mod.normalize_document(
            {
                "queues": {
                    "media_player.living_room": {
                        "items": [
                            {
                                "uid": "a1b2c3d4",
                                "source": "youtube",
                                "id": "dQw4w9WgXcQ",
                                "title": "Bai A",
                            }
                        ]
                    }
                }
            }
        )
        store._store = types.SimpleNamespace(
            async_load=AsyncMock(return_value=doc),
            async_save=AsyncMock(),
        )
        hass.data[qs_mod.DATA_KEY] = store
        dispatch = AsyncMock(return_value={"session_id": "sess1"})
        result = await playback_mod.async_play_queue(
            hass,
            types.SimpleNamespace(),
            queue_code="media_player.living_room",
            entity_ids=["media_player.living_room"],
            dispatch_fn=dispatch,
        )
        self.assertEqual({"session_id": "sess1"}, result)
        self.assertEqual(
            "media_player.living_room",
            sessions_mod.session_queue_key({"session_id": "sess1"}),
        )

    async def test_n4_async_play_queue_tu_choi_queue_code_la(self):
        """N4: async_play_queue chặn queue_code lạ TRƯỚC khi chạm kho."""
        for bad in (
            "",
            "../../../etc/passwd",
            "media_player.a;b",
            "MEDIA_PLAYER.A",
            "device:short",
            "x" * 200,
        ):
            with self.subTest(code=bad[:20]):
                with self.assertRaises(ValueError):
                    await playback_mod.async_play_queue(
                        None, None, queue_code=bad, entity_ids=[]
                    )


if __name__ == "__main__":
    unittest.main()
