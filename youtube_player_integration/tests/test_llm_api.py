"""Unit tests for the Assist LLM API tools in TriTue YouTube Player."""

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import llm, entity_registry as er
import custom_components.tritue_youtube_player.llm_api as llm_api_mod


class AssistLLMAPITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.api_mod = llm_api_mod
        self.mock_registry = MagicMock(entities={})
        self.patch_er = patch.object(er, "async_get", return_value=self.mock_registry)
        self.patch_er.start()
        self.addCleanup(self.patch_er.stop)

        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value=[])
        mock_store.async_save = AsyncMock()
        self.patch_store = patch("custom_components.tritue_youtube_player.llm_api.Store", return_value=mock_store)
        self.patch_store.start()
        self.addCleanup(self.patch_store.stop)

        self.hass = types.SimpleNamespace(
            data={},
            config=types.SimpleNamespace(config_dir="/tmp"),
            config_entries=types.SimpleNamespace(
                async_entries=lambda domain: [self.entry]
            ),
            states=types.SimpleNamespace(
                async_all=lambda domain: [
                    types.SimpleNamespace(
                        entity_id="media_player.living_room",
                        name="Phòng khách",
                        state="idle",
                        attributes={"supported_features": 512},
                    )
                ],
                get=lambda entity_id: types.SimpleNamespace(
                    entity_id=entity_id,
                    name="Phòng khách",
                    state="idle",
                    attributes={"supported_features": 512},
                ),
            ),
            services=types.SimpleNamespace(async_call=AsyncMock()),
        )
        self.client = types.SimpleNamespace(
            async_playlists=AsyncMock(return_value={"playlists": []}),
            async_playlist_action=AsyncMock(),
            async_search=AsyncMock(),
        )
        self.entry = types.SimpleNamespace(
            entry_id="entry_123",
            domain="tritue_youtube_player",
            state=ConfigEntryState.LOADED,
            runtime_data=types.SimpleNamespace(
                client=self.client,
                data={},
                async_refresh=AsyncMock(),
            ),
        )
        self.context = llm.LLMContext(
            platform="conversation",
            context=types.SimpleNamespace(user_id="user_1"),
            language="vi",
            assistant="conversation",
            device_id="dev_1",
        )

    def test_api_prompt_and_tool_descriptions(self):
        prompt = self.api_mod.API_PROMPT
        # Rule: Music Assistant / multiple providers instructions
        self.assertIn("Music Assistant", prompt)
        # Rule: Playlist guidance ('kho' vs 'youtube')
        self.assertIn("tim_playlist", prompt)
        self.assertIn("kho", prompt)
        self.assertIn("youtube", prompt)
        # Rule: Queue playback immediately
        self.assertIn("phat_hang_doi", prompt)

        # Tool descriptions check
        tool_classes = {
            t.name: t
            for t in [
                self.api_mod.SearchPlaylistTool(),
                self.api_mod.PlayPlaylistTool(),
                self.api_mod.PlayQueueTool(),
                self.api_mod.QueueManageTool(),
            ]
        }
        self.assertIn("tim_playlist", tool_classes)
        self.assertIn("phat_playlist", tool_classes)
        self.assertIn("phat_hang_doi", tool_classes)
        self.assertIn("hang_doi", tool_classes)
        self.assertIn("so_playlist_trong_kho", tool_classes["tim_playlist"].description)

    def test_n11_api_prompt_khong_quang_cao_tua(self):
        """N11: API_PROMPT must not advertise seek/tua (no tua command exists)."""
        prompt = self.api_mod.API_PROMPT
        self.assertNotIn("seek", prompt.lower())

    def test_n11_api_prompt_phat_hang_doi_khop_hanh_vi(self):
        """N11: API_PROMPT must match PlayQueueTool behavior (>1 loa -> numbered ask list)."""
        prompt = self.api_mod.API_PROMPT
        self.assertNotIn("active or default", prompt)
        self.assertIn("phat_hang_doi", prompt)
        self.assertIn("numbered list", prompt)

    async def test_search_playlist_empty_kho(self):
        tool = self.api_mod.SearchPlaylistTool()
        tool_input = sys.modules["homeassistant.helpers.llm"].ToolInput(
            "tim_playlist",
            {"nguon_playlist": "kho"},
        )
        result = await tool.async_call(self.hass, tool_input, self.context)
        self.assertEqual("kho", result["nguon_playlist"])
        self.assertEqual(0, result["so_playlist_trong_kho"])
        self.assertEqual([], result["ket_qua"])
        self.assertIn("ghi_chu", result)

    async def test_search_playlist_youtube_always_includes_so_kho(self):
        self.client.async_playlists.return_value = {
            "playlists": [
                {"id": "pl1234567890", "name": "Nhạc Trịnh", "items": [{"id": "v1"}]}
            ]
        }
        tool = self.api_mod.SearchPlaylistTool()
        tool_input = sys.modules["homeassistant.helpers.llm"].ToolInput(
            "tim_playlist",
            {"nguon_playlist": "youtube", "tu_khoa": "Nhạc chill"},
        )
        result = await tool.async_call(self.hass, tool_input, self.context)
        self.assertEqual("youtube", result["nguon_playlist"])
        self.assertEqual(1, result["so_playlist_trong_kho"])
        self.assertEqual([], result["ket_qua"])
        self.assertIn("ghi_chu", result)

    async def test_search_playlist_memory_isolation(self):
        self.client.async_playlists.return_value = {
            "playlists": [
                {"id": "pl1234567890", "name": "Nhạc Trịnh", "items": [{"id": "v1"}]},
                {"id": "pl1234567891", "name": "Bolero", "items": [{"id": "v2"}]},
            ]
        }
        tool = self.api_mod.SearchPlaylistTool()
        # Search kho
        await tool.async_call(
            self.hass,
            sys.modules["homeassistant.helpers.llm"].ToolInput(
                "tim_playlist", {"nguon_playlist": "kho"}
            ),
            self.context,
        )
        # Search youtube link
        await tool.async_call(
            self.hass,
            sys.modules["homeassistant.helpers.llm"].ToolInput(
                "tim_playlist",
                {
                    "nguon_playlist": "youtube",
                    "tu_khoa": "https://www.youtube.com/playlist?list=PL1234567890",
                },
            ),
            self.context,
        )
        mem = self.api_mod._memory(self.hass)
        self.assertIn("playlist_kho", mem)
        self.assertIn("playlist_youtube", mem)
        # Kho has 2 items
        self.assertEqual(2, len(mem["playlist_kho"]["user_1"]["items"]))
        # YouTube has 1 item
        self.assertEqual(1, len(mem["playlist_youtube"]["user_1"]["items"]))

    async def test_play_playlist_number_out_of_range(self):
        self.client.async_playlists.return_value = {
            "playlists": [{"id": "pl1234567890", "name": "Nhạc Trịnh", "items": [{"id": "v1"}]}]
        }
        tool_search = self.api_mod.SearchPlaylistTool()
        await tool_search.async_call(
            self.hass,
            sys.modules["homeassistant.helpers.llm"].ToolInput(
                "tim_playlist", {"nguon_playlist": "kho"}
            ),
            self.context,
        )
        tool_play = self.api_mod.PlayPlaylistTool()
        # Number 99 out of range
        result = await tool_play.async_call(
            self.hass,
            sys.modules["homeassistant.helpers.llm"].ToolInput(
                "phat_playlist",
                {"danh_sach": "99", "loa": "phòng khách", "nguon_playlist": "kho"},
            ),
            self.context,
        )
        self.assertIn("loi", result)

    async def test_play_playlist_expired_memory(self):
        mem = self.api_mod._memory(self.hass)
        mem.setdefault("playlist_kho_user_1", {})["items"] = [{"id": "pl1", "name": "P1"}]
        mem["playlist_kho_user_1"]["at"] = 100.0
        tool_play = self.api_mod.PlayPlaylistTool()
        with patch("time.monotonic", return_value=5000.0):
            result = await tool_play.async_call(
                self.hass,
                sys.modules["homeassistant.helpers.llm"].ToolInput(
                    "phat_playlist",
                    {"danh_sach": "1", "loa": "phòng khách", "nguon_playlist": "kho"},
                ),
                self.context,
            )
        self.assertIn("loi", result)
        self.assertIn("hết hạn", result["loi"])

    def test_n8_play_playlist_schema_requires_nguon_playlist(self):
        """N8: PlayPlaylistTool schema must require nguon_playlist."""
        tool = self.api_mod.PlayPlaylistTool()
        with self.assertRaises(vol.MultipleInvalid):
            tool.parameters({"danh_sach": "1", "loa": "phòng khách"})

    def test_n11_no_tua_in_control_tool(self):
        """N11: ControlMusicTool must not accept 'tua' command."""
        tool = self.api_mod.ControlMusicTool()
        with self.assertRaises(vol.MultipleInvalid):
            tool.parameters({"lenh": "tua", "loa": "phòng khách"})

    async def test_n3_play_queue_tool_mode_is_none(self):
        """N3: PlayQueueTool must not use queue.mode, default mode must be None."""
        tool = self.api_mod.PlayQueueTool()
        store = self.api_mod.get_queue_store(self.hass)
        store._store.async_save = AsyncMock()
        store._store.async_load = AsyncMock(return_value={"queues": {}})
        await store.async_change({
            "key": "media_player.living_room",
            "action": "add",
            "items": [{"id": "dQw4w9WgXcQ", "title": "Song 1", "source": "youtube"}],
        })
        # Set queue mode to video
        await store.async_change({
            "key": "media_player.living_room",
            "action": "set",
            "mode": "video",
        })

        with patch("custom_components.tritue_youtube_player.services.async_dispatch", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = {"session_id": "sess_1"}
            tool_input = sys.modules["homeassistant.helpers.llm"].ToolInput(
                "phat_hang_doi",
                {"loa": "phòng khách"},
            )
            await tool.async_call(self.hass, tool_input, self.context)
            mock_dispatch.assert_called_once()
            _, kwargs = mock_dispatch.call_args
            self.assertIsNone(kwargs.get("mode"), "PlayQueueTool should pass mode=None by default, not queue.mode")

            # M11 check: when caller specifies mode, it MUST be passed to dispatch
            mock_dispatch.reset_mock()
            tool_input_mode = sys.modules["homeassistant.helpers.llm"].ToolInput(
                "phat_hang_doi",
                {"loa": "phòng khách", "mode": "audio"},
            )
            await tool.async_call(self.hass, tool_input_mode, self.context)
            mock_dispatch.assert_called_once()
            _, kwargs = mock_dispatch.call_args
            self.assertEqual("audio", kwargs.get("mode"), "PlayQueueTool should pass explicit mode to dispatch")

    async def test_n3_queue_manage_tool_jump_failure_retains_current(self):
        """N3: hang_doi nhay failure must not move current and must catch HomeAssistantError."""
        tool = self.api_mod.QueueManageTool()
        store = self.api_mod.get_queue_store(self.hass)
        store._store.async_save = AsyncMock()
        store._store.async_load = AsyncMock(return_value={"queues": {}})
        await store.async_change({
            "key": "media_player.living_room",
            "action": "add",
            "items": [
                {"id": "dQw4w9WgXcQ", "title": "Song 1", "source": "youtube"},
                {"id": "kJQP7kiw5Fk", "title": "Song 2", "source": "youtube"},
            ],
        })
        q_before = await store.async_get("media_player.living_room")
        self.assertIsNone(q_before["current"])

        from homeassistant.exceptions import HomeAssistantError
        with patch("custom_components.tritue_youtube_player.services.async_dispatch", side_effect=HomeAssistantError("Speaker unavailable")):
            tool_input = sys.modules["homeassistant.helpers.llm"].ToolInput(
                "hang_doi",
                {"lenh": "nhay", "loa": "phòng khách", "so": "2"},
            )
            result = await tool.async_call(self.hass, tool_input, self.context)
            self.assertIn("loi", result)
            q_after = await store.async_get("media_player.living_room")
            self.assertIsNone(q_after["current"], "current should NOT be moved when dispatch fails")

    async def test_n11_play_queue_without_speaker_asks_when_multiple(self):
        """N11: PlayQueueTool without speaker must return can_hoi when multiple speakers available."""
        tool = self.api_mod.PlayQueueTool()
        self.hass.states.async_all = lambda domain: [
            types.SimpleNamespace(entity_id="media_player.living_room", name="Phòng khách", state="idle", attributes={"supported_features": 512}),
            types.SimpleNamespace(entity_id="media_player.kitchen", name="Nhà bếp", state="idle", attributes={"supported_features": 512}),
        ]
        tool_input = sys.modules["homeassistant.helpers.llm"].ToolInput("phat_hang_doi", {})
        result = await tool.async_call(self.hass, tool_input, self.context)
        self.assertIn("can_hoi", result, "Should ask which speaker when multiple available")

    async def test_n11_queue_manage_huge_number_and_superscript(self):
        """N11: QueueManageTool with 9*5000 or superscript must not crash with ValueError."""
        tool = self.api_mod.QueueManageTool()
        store = self.api_mod.get_queue_store(self.hass)
        store._store.async_save = AsyncMock()
        store._store.async_load = AsyncMock(return_value={"queues": {}})
        await store.async_change({
            "key": "media_player.living_room",
            "action": "add",
            "items": [{"id": "dQw4w9WgXcQ", "title": "Song 1", "source": "youtube"}],
        })

        for weird_input in ["9" * 5000, "²"]:
            tool_input = sys.modules["homeassistant.helpers.llm"].ToolInput(
                "hang_doi",
                {"lenh": "nhay", "loa": "phòng khách", "so": weird_input},
            )
            result = await tool.async_call(self.hass, tool_input, self.context)
            self.assertIn("loi", result)

    async def test_n8_queue_manage_multiple_matches_returns_can_hoi(self):
        """N8: QueueManageTool with ambiguous song title must return can_hoi."""
        tool = self.api_mod.QueueManageTool()
        store = self.api_mod.get_queue_store(self.hass)
        store._store.async_save = AsyncMock()
        store._store.async_load = AsyncMock(return_value={"queues": {}})
        await store.async_change({
            "key": "media_player.living_room",
            "action": "add",
            "items": [
                {"id": "dQw4w9WgXcQ", "title": "Nhạc Trịnh 1", "source": "youtube"},
                {"id": "kJQP7kiw5Fk", "title": "Nhạc Trịnh 2", "source": "youtube"},
            ],
        })
        tool_input = sys.modules["homeassistant.helpers.llm"].ToolInput(
            "hang_doi",
            {"lenh": "nhay", "loa": "phòng khách", "so": "Nhạc Trịnh"},
        )
        result = await tool.async_call(self.hass, tool_input, self.context)
        self.assertIn("can_hoi", result)
        self.assertEqual(2, len(result["danh_sach"]))


if __name__ == "__main__":
    unittest.main()
