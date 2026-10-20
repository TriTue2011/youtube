"""Tests for Home Assistant services registered by TriTue YouTube Player."""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import yaml

import voluptuous as vol

ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"

# Load services.py with real voluptuous and homeassistant from .venv
import custom_components.tritue_youtube_player.services as services_mod
from custom_components.tritue_youtube_player.const import DOMAIN
from custom_components.tritue_youtube_player.playback import UnsupportedTargetMediaError


class ServicesStructuralAndHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.yaml_path = COMPONENT_DIR / "services.yaml"
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            self.services_yaml = yaml.safe_load(f)

    def test_n5_services_yaml_matches_schemas_exactly(self):
        """N5: services.yaml fields must match registered Voluptuous schemas for all actions."""
        schema_map = {
            "play_on_players": services_mod.PLAY_ON_PLAYERS_SCHEMA,
            "play_playlist": services_mod.PLAY_PLAYLIST_SCHEMA,
            "play_queue": services_mod.PLAY_QUEUE_SCHEMA,
            "skip": services_mod.SKIP_SCHEMA,
            "stop_session": services_mod.STOP_SESSION_SCHEMA,
            "remove_players": services_mod.REMOVE_PLAYERS_SCHEMA,
        }
        for service_name, schema in schema_map.items():
            self.assertIn(service_name, self.services_yaml, f"Missing {service_name} in services.yaml")
            yaml_fields = self.services_yaml[service_name].get("fields", {})
            schema_keys = set()
            required_keys = set()
            for key in schema.schema.keys():
                k_name = key.schema if hasattr(key, "schema") else key
                schema_keys.add(k_name)
                if isinstance(key, vol.Required):
                    required_keys.add(k_name)

            self.assertEqual(
                schema_keys,
                set(yaml_fields.keys()),
                f"Field mismatch for {service_name}: schema={schema_keys} vs yaml={set(yaml_fields.keys())}",
            )
            for req_key in required_keys:
                self.assertTrue(
                    yaml_fields[req_key].get("required"),
                    f"Field {req_key} in {service_name} should be required: true in services.yaml",
                )

    def test_n1_play_on_players_schema_no_default_mode(self):
        """N1: play_on_players schema must not have default='audio' for mode."""
        validated = services_mod.PLAY_ON_PLAYERS_SCHEMA(
            {
                "entry_id": "test_entry",
                "source": "youtube",
                "target": "dQw4w9WgXcQ",
                "entity_id": ["media_player.cast_tv"],
            }
        )
        self.assertNotIn("mode", validated, "mode should NOT have a default in schema")
        # And services.yaml must not specify default: audio
        self.assertNotIn("default", self.services_yaml["play_on_players"]["fields"]["mode"])

    def test_n2_no_video_quality_in_schemas_or_yaml(self):
        """N2: video_quality must be removed from all schemas and services.yaml."""
        for svc in ("play_on_players", "play_playlist", "play_queue"):
            self.assertNotIn(
                "video_quality",
                self.services_yaml[svc].get("fields", {}),
                f"video_quality must be removed from services.yaml for {svc}",
            )
        with self.assertRaises(vol.Invalid):
            services_mod.PLAY_ON_PLAYERS_SCHEMA(
                {
                    "entry_id": "test_entry",
                    "source": "youtube",
                    "target": "dQw4w9WgXcQ",
                    "entity_id": ["media_player.cast_tv"],
                    "video_quality": 720,
                }
            )

    def test_n12_old_actions_retain_text_selector(self):
        """N12: skip, stop_session, remove_players retain 'text' selector for entry_id."""
        for svc in ("skip", "stop_session", "remove_players"):
            entry_field = self.services_yaml[svc]["fields"]["entry_id"]
            self.assertIn("text", entry_field.get("selector", {}), f"{svc} entry_id should use 'text' selector")
            self.assertNotIn("config_entry", entry_field.get("selector", {}))

    async def test_n6_n7_handle_play_playlist_validation(self):
        """N6/N7: play_playlist rejects malformed share codes and youtube links with clear errors.

        Mã chia sẻ TTPL1. HỢP LỆ được nhận (nhập vào kho một lần): xem test_share_code.py."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.runtime_data.client.async_playlists = AsyncMock(return_value={"playlists": []})

        with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry):
            # Malformed share code (not base64url) is rejected before touching the player server
            call_share = MagicMock(data={"entry_id": "e", "playlist_code": "TTPL1.%%%", "entity_id": ["media_player.s1"]})
            with self.assertRaises(services_mod.ServiceValidationError) as cm:
                await services_mod._async_handle_play_playlist(hass, call_share)
            self.assertEqual("invalid_playlist_code", cm.exception.translation_key)

            # YouTube playlist link
            call_yt = MagicMock(data={"entry_id": "e", "playlist_code": "https://www.youtube.com/playlist?list=PL12345", "entity_id": ["media_player.s1"]})
            with self.assertRaises(services_mod.ServiceValidationError) as cm:
                await services_mod._async_handle_play_playlist(hass, call_yt)
            self.assertEqual("youtube_playlist_not_imported", cm.exception.translation_key)

            # Invalid code
            call_bad = MagicMock(data={"entry_id": "e", "playlist_code": "not-valid-code!", "entity_id": ["media_player.s1"]})
            with self.assertRaises(services_mod.ServiceValidationError) as cm:
                await services_mod._async_handle_play_playlist(hass, call_bad)
            self.assertEqual("invalid_playlist_code", cm.exception.translation_key)

    async def test_n4_handle_play_queue_marks_current_and_binds_session(self):
        """N4: play_queue marks current and binds queue key to session."""
        hass = MagicMock()
        hass.data = {}
        entry = MagicMock()
        entry.entry_id = "test_entry"
        store = services_mod.get_queue_store(hass)
        store._store.async_save = AsyncMock()
        store._store.async_load = AsyncMock(return_value={"queues": {}})

        await store.async_change({
            "key": "media_player.speaker_x",
            "action": "add",
            "items": [
                {"id": "dQw4w9WgXcQ", "title": "Song 1", "source": "youtube"},
                {"id": "kJQP7kiw5Fk", "title": "Song 2", "source": "youtube"},
            ],
        })

        with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry), \
             patch.object(services_mod, "async_dispatch", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = {"session_id": "sess_123", "target_count": 1}
            call = MagicMock(data={
                "entry_id": "test_entry",
                "queue_code": "media_player.speaker_x",
                "entity_id": ["media_player.speaker_y"],
            })
            await services_mod._async_handle_play_queue(hass, call)

            q = await store.async_get("media_player.speaker_x")
            self.assertIsNotNone(q["current"])
            self.assertEqual(q["items"][0]["uid"], q["current"])
            self.assertIn(q["current"], q["played"])

            # Verify session is bound to queue key
            from custom_components.tritue_youtube_player.sessions import session_queue_key
            self.assertEqual("media_player.speaker_x", session_queue_key({"session_id": "sess_123"}))

            # N4: Playing queue X on speaker Y -> next song must come from queue X (not speaker Y)
            session = {"session_id": "sess_123", "output_entity_ids": ["media_player.speaker_y"]}
            with patch.object(services_mod, "_async_play_session_item", new_callable=AsyncMock) as mock_play_item:
                mock_play_item.return_value = {"session_id": "sess_123"}
                await services_mod.async_play_queue_next(hass, entry, session)
                mock_play_item.assert_called_once()
                item_played = mock_play_item.call_args[0][3]
                self.assertEqual(q["items"][1]["id"], item_played["id"], "Next song must come from queue X, not speaker Y")

    def test_n9_copied_yaml_snippets_match_services_fields(self):
        """N9: verify copied YAML snippet structure matches services.yaml field names."""
        with open(COMPONENT_DIR / "services.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 1. Song copy snippet: source + target for play_on_players
        pop_fields = data["play_on_players"]["fields"]
        self.assertIn("source", pop_fields)
        self.assertIn("target", pop_fields)
        song_snippet = "source: youtube\ntarget: dQw4w9WgXcQ"
        parsed_song = yaml.safe_load(song_snippet)
        self.assertSetEqual(set(parsed_song.keys()), {"source", "target"})

        # 2. Playlist copy snippet: playlist_code for play_playlist
        pp_fields = data["play_playlist"]["fields"]
        self.assertIn("playlist_code", pp_fields)
        pl_snippet = "playlist_code: abcd1234efgh"
        parsed_pl = yaml.safe_load(pl_snippet)
        self.assertSetEqual(set(parsed_pl.keys()), {"playlist_code"})

        # 3. Queue copy snippet: queue_code for play_queue
        pq_fields = data["play_queue"]["fields"]
        self.assertIn("queue_code", pq_fields)
        q_snippet = "queue_code: media_player.living_room"
        parsed_q = yaml.safe_load(q_snippet)
        self.assertSetEqual(set(parsed_q.keys()), {"queue_code"})

    async def test_m8_handle_play_queue_invalid_code_raises_validation_error(self):
        """M8: play_queue must reject invalid queue_code with invalid_queue_code error."""
        hass = MagicMock()
        hass.data = {}
        entry = MagicMock()
        entry.entry_id = "test_entry"

        with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry):
            call_bad = MagicMock(data={
                "entry_id": "test_entry",
                "queue_code": "invalid queue key with spaces!!",
                "entity_id": ["media_player.speaker_y"],
            })
            with self.assertRaises(services_mod.ServiceValidationError) as cm:
                await services_mod._async_handle_play_queue(hass, call_bad)
            self.assertEqual("invalid_queue_code", cm.exception.translation_key)

    async def test_play_queue_nhan_ca_dong_queue_code_chep_tu_the(self):
        """Chủ máy 20/10/2026: nút sao chép trên thẻ chép `queue_code: media_player.x`; dán nguyên dòng vào ô action thì báo
        «Mã hàng đợi không hợp lệ». Nhãn đúng tên trường và dấu nháy bao quanh phải được bỏ trước khi kiểm khuôn."""
        for raw in ("queue_code: media_player.speaker_x", "'queue_code: media_player.speaker_x'", ' "Queue_Code:media_player.speaker_x" '):
            with self.subTest(raw=raw):
                hass = MagicMock()
                hass.data = {}
                entry = MagicMock()
                store = services_mod.get_queue_store(hass)
                store._store.async_save = AsyncMock()
                store._store.async_load = AsyncMock(return_value={"queues": {}})
                await store.async_change({"key": "media_player.speaker_x", "action": "add",
                                          "items": [{"id": "dQw4w9WgXcQ", "title": "Song 1", "source": "youtube"}]})
                with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry), \
                     patch.object(services_mod, "async_dispatch", new_callable=AsyncMock) as mock_dispatch:
                    mock_dispatch.return_value = {"session_id": "sess_q", "target_count": 1}
                    call = MagicMock(data={"entry_id": "e", "queue_code": raw, "entity_id": ["media_player.speaker_y"]})
                    await services_mod._async_handle_play_queue(hass, call)
                    mock_dispatch.assert_awaited_once()
                q = await store.async_get("media_player.speaker_x")
                self.assertIsNotNone(q["current"])

    async def test_play_queue_nhan_sai_van_la_ma_khong_hop_le(self):
        """Chỉ gỡ ĐÚNG nhãn `queue_code:`; nhãn khác hay khoá hỏng vẫn bị từ chối (không đoán)."""
        for raw in ("playlist_code: media_player.speaker_x", "queue_code: loa phong khach!!", "queue_code:"):
            with self.subTest(raw=raw):
                hass = MagicMock()
                hass.data = {}
                with patch.object(services_mod, "_loaded_entry_or_raise", return_value=MagicMock()):
                    call = MagicMock(data={"entry_id": "e", "queue_code": raw, "entity_id": ["media_player.s"]})
                    with self.assertRaises(services_mod.ServiceValidationError) as cm:
                        await services_mod._async_handle_play_queue(hass, call)
                    self.assertEqual("invalid_queue_code", cm.exception.translation_key)

    async def test_play_queue_bo_trong_queue_code_dung_hang_doi_cua_loa_dau(self):
        hass = MagicMock()
        hass.data = {}
        entry = MagicMock()
        store = services_mod.get_queue_store(hass)
        store._store.async_save = AsyncMock()
        store._store.async_load = AsyncMock(return_value={"queues": {}})
        await store.async_change({"key": "media_player.speaker_x", "action": "add",
                                  "items": [{"id": "dQw4w9WgXcQ", "title": "Song 1", "source": "youtube"}]})
        with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry), \
             patch.object(services_mod, "async_dispatch", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = {"session_id": "sess_q2", "target_count": 1}
            call = MagicMock(data={"entry_id": "e", "entity_id": ["media_player.speaker_x", "media_player.speaker_z"]})
            await services_mod._async_handle_play_queue(hass, call)
        from custom_components.tritue_youtube_player.sessions import session_queue_key
        self.assertEqual("media_player.speaker_x", session_queue_key({"session_id": "sess_q2"}))

    async def test_play_playlist_theo_ten_ngan(self):
        from custom_components.tritue_youtube_player import share_codes  # noqa: F401
        hass, entry = MagicMock(), MagicMock()
        pls = [
            {"id": "aaaaaaaaaaaa", "name": "Account cafe", "items": [{"source": "youtube", "id": "kJQP7kiw5Fk"}]},
            {"id": "bbbbbbbbbbbb", "name": "home", "items": [{"source": "youtube", "id": "dQw4w9WgXcQ"}]},
        ]
        entry.runtime_data.client.async_playlists = AsyncMock(return_value={"playlists": pls})
        for raw in ("home", " HOME ", "'home'"):
            with self.subTest(raw=raw), \
                 patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry), \
                 patch.object(services_mod, "async_dispatch", new=AsyncMock()) as dispatch:
                call = MagicMock(data={"entry_id": "e", "playlist_code": raw, "entity_id": ["media_player.s1"]})
                await services_mod._async_handle_play_playlist(hass, call)
                self.assertEqual("bbbbbbbbbbbb", dispatch.await_args.kwargs["playlist_id"])

    async def test_play_playlist_ten_trung_thi_bat_chon_ma_khong_doan(self):
        hass, entry = MagicMock(), MagicMock()
        pls = [{"id": "aaaaaaaaaaaa", "name": "home", "items": []}, {"id": "bbbbbbbbbbbb", "name": "Home", "items": []}]
        entry.runtime_data.client.async_playlists = AsyncMock(return_value={"playlists": pls})
        with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry), \
             patch.object(services_mod, "async_dispatch", new=AsyncMock()) as dispatch:
            call = MagicMock(data={"entry_id": "e", "playlist_code": "home", "entity_id": ["media_player.s1"]})
            with self.assertRaises(services_mod.ServiceValidationError) as cm:
                await services_mod._async_handle_play_playlist(hass, call)
        self.assertEqual("playlist_name_ambiguous", cm.exception.translation_key)
        dispatch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
