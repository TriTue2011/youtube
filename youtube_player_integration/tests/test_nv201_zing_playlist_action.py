"""NV201 BƯỚC 1 — đo đỏ: action play_playlist với bài Zing.

Lỗi: `_async_handle_play_playlist` (services.py) và Assist PlayPlaylistTool
(llm_api.py) chọn target bằng `first.get("id") or first.get("url")`.
Với bài Zing, `id` là mã bài trần (vd "ZWABCDEF") trong khi máy phát
BẮT BUỘC URL đầy đủ (`validate_zing_target`) ở cả hai tầng:
`record_session` -> `require_public_zing_result` và
`/api/integration/stream` -> `prepare_stream`.

Harness: client GIẢ gọi vào PlayerServer THẬT (record_session,
require_public_zing_result, prepare_stream thật; chỉ `_resolve_stream`
— bước chạm mạng — bị vá). `async_dispatch` THẬT, không mock.

Ghi chú môi trường: test này ưu tiên `homeassistant` thật nếu có;
khi chạy trong sandbox thiếu HA thì dùng stub tối thiểu trong /tmp/nv201_stubs
(chỉ để import được, không thay đổi hành vi logic).
"""

import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

try:
    import homeassistant  # noqa: F401
except ImportError:  # sandbox thiếu HA: dùng stub tối thiểu (chỉ để import được)
    for _cand in ("/home/hatch/workspace/nv201-stubs", "/tmp/nv201_stubs"):
        if Path(_cand).is_dir() and _cand not in sys.path:
            sys.path.insert(0, _cand)
            break

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
APP_DIR = ROOT / "youtube_player" / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import custom_components.tritue_youtube_player.services as services_mod
import custom_components.tritue_youtube_player.llm_api as llm_api_mod
from custom_components.tritue_youtube_player.services import async_dispatch
from custom_components.tritue_youtube_player.sessions import item_target
from youtube_player.app.server import PlayerServer, PlayerHandler
from youtube_player.app.playlists import normalize_item

ZING_URL = "https://zingmp3.vn/bai-hat/ZWABCDEF.html"
ZING_ID = "ZWABCDEF"
YT_ID = "dQw4w9WgXcQ"
FB_ID = "1807802260572674"
SPEAKER = "media_player.loa_phong_khach"

YOUTUBE_ITEM = {"source": "youtube", "id": YT_ID, "title": "Bai YouTube"}
ZING_ITEM = {"source": "zing", "url": ZING_URL, "title": "Bai Zing"}


class FakeClient:
    """Client giả: mọi lời gọi đi vào PlayerServer thật."""

    def __init__(self, server):
        self.server = server
        self.base_url = "http://127.0.0.1:8099"

    async def async_playlists(self):
        return {"playlists": self.server.playlists.list()}

    async def async_update_session(self, source, target, output_entity_ids, *,
                                   media_content_type=None, volume_level=None,
                                   session_id=None, controller=None, playlist_id=None):
        session = self.server.record_session(
            source, target,
            output_entity_ids=list(output_entity_ids),
            media_content_type=media_content_type or "",
            volume_level=volume_level,
            session_id=session_id,
            controller=controller or "",
            playlist_id=playlist_id,
        )
        return {"success": True, "session": session}

    async def async_create_stream(self, source, target, *, max_height=None,
                                  public_base_url=None):
        # Chuẩn hoá + kiểm quyền THẬT; chỉ bước giải luồng mạng là giả.
        target, resolved = self.server.prepare_stream(source, target)
        return {
            "stream_url": f"http://127.0.0.1:9/stream/{source}",
            "media_content_type": resolved.get("media_content_type") or "audio/mpeg",
        }


class ZingDispatchHarness(unittest.IsolatedAsyncioTestCase):
    """Dựng PlayerServer thật + hass giả; async_dispatch thật."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.server = PlayerServer(
            ("127.0.0.1", 0), PlayerHandler,
            data_dir=Path(self.temp_dir.name),
            app_title="Test NV201",
            max_history=10,
            integration_token="tok-" + "test""test-token",
            public_base_url="http://127.0.0.1:8099",
        )
        self.addCleanup(self.server.server_close)
        self.server.prefetch_streams = False
        # Giả lớp mạng: không giải luồng thật, giữ nguyên mọi bước kiểm tra.
        self.server._resolve_stream = lambda source, target: {
            "url": "http://127.0.0.1:9/fake.mp3",
            "media_content_type": "audio/mpeg",
        }
        self.client = FakeClient(self.server)

        self.hass = MagicMock()
        self.hass.data = {}
        self.hass.states.get = MagicMock(return_value=types.SimpleNamespace(
            state="idle", attributes={"supported_features": 512}))
        self.hass.services.async_call = AsyncMock()
        self.entry = types.SimpleNamespace(
            entry_id="e1",
            runtime_data=types.SimpleNamespace(
                client=self.client, data={}, async_refresh=AsyncMock()),
        )
        patches = [
            patch.object(services_mod, "_virtual_players", return_value=set()),
            patch.object(services_mod.er, "async_get",
                         return_value=MagicMock(async_get=lambda e: None)),
            patch.object(services_mod, "_loaded_entry_or_raise",
                         return_value=self.entry),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _tao_playlist(self, items):
        pl = self.server.playlists.create("PL NV201", items)
        return pl["id"]

    def _goi_play_playlist(self, playlist_id):
        call = MagicMock(data={
            "entry_id": "e1",
            "playlist_code": playlist_id,
            "entity_id": [SPEAKER],
        })
        return services_mod._async_handle_play_playlist(self.hass, call)

    def _play_media_calls(self):
        return [
            c for c in self.hass.services.async_call.await_args_list
            if c.args[:2] == ("media_player", "play_media")
        ]

    # ---- BƯỚC 1(a): playlist chỉ toàn bài Zing ----
    async def test_a_playlist_chi_zing_phat_duoc(self):
        pid = self._tao_playlist([dict(ZING_ITEM)])
        await self._goi_play_playlist(pid)
        calls = self._play_media_calls()
        self.assertEqual(1, len(calls), "play_playlist với bài Zing phải phát ra loa")

    # ---- BƯỚC 1(b): bài ĐẦU là Zing, sau là YouTube ----
    async def test_b_bai_dau_zing_sau_youtube(self):
        pid = self._tao_playlist([dict(ZING_ITEM), dict(YOUTUBE_ITEM)])
        await self._goi_play_playlist(pid)
        self.assertEqual(1, len(self._play_media_calls()))

    # ---- BƯỚC 1(c): bài đầu YouTube, giữa có Zing (đối chứng: vốn đã chạy) ----
    async def test_c_bai_dau_youtube_giua_zing(self):
        pid = self._tao_playlist([dict(YOUTUBE_ITEM), dict(ZING_ITEM)])
        await self._goi_play_playlist(pid)
        self.assertEqual(1, len(self._play_media_calls()))

    # ---- BƯỚC 1(d): bài Zing lưu thiếu url bị normalize_item loại ----
    def test_d_zing_thieu_url_bi_loai_khoi_normalize(self):
        self.assertIsNone(normalize_item({"source": "zing", "id": ZING_ID}))
        item = normalize_item({"source": "zing", "url": ZING_URL})
        self.assertIsNotNone(item)
        self.assertEqual(ZING_ID, item["id"])
        self.assertEqual(ZING_URL, item["url"])

    # ---- BƯỚC 1(e): id Zing trần không phải thứ đường phát nhận ----
    def test_e_id_zing_tran_bi_may_phat_tu_choi(self):
        with self.assertRaises(ValueError) as cm:
            self.server.require_public_zing_result(ZING_ID)
        self.assertEqual("invalid_zing_target", str(cm.exception))
        # NƠI RƠI khi đi đường play_playlist: record_session cũng chặn ở đây.
        with self.assertRaises(ValueError):
            self.server.record_session("zing", ZING_ID, output_entity_ids=[SPEAKER])

    # ---- BỔ SUNG: đường Assist (llm_api PlayPlaylistTool) cùng lớp lỗi ----
    async def test_f_duong_assist_playlist_zing(self):
        from homeassistant.helpers import llm as llm_helpers
        pid = self._tao_playlist([dict(ZING_ITEM)])
        hass = types.SimpleNamespace(
            data={},
            config_entries=types.SimpleNamespace(
                async_entries=lambda domain: [types.SimpleNamespace(
                    entry_id="e1", domain="tritue_youtube_player",
                    state=__import__("homeassistant.config_entries", fromlist=["ConfigEntryState"]).ConfigEntryState.LOADED,
                    runtime_data=types.SimpleNamespace(
                        client=self.client, data={}, async_refresh=AsyncMock()),
                )]
            ),
            states=types.SimpleNamespace(
                async_all=lambda domain: [types.SimpleNamespace(
                    entity_id=SPEAKER, name="Phòng khách", state="idle",
                    attributes={"supported_features": 512})],
                get=lambda entity_id: types.SimpleNamespace(
                    entity_id=entity_id, name="Phòng khách", state="idle",
                    attributes={"supported_features": 512}),
            ),
            services=types.SimpleNamespace(async_call=AsyncMock()),
        )
        context = llm_helpers.LLMContext(
            platform="conversation",
            context=types.SimpleNamespace(user_id="user_1"),
            language="vi", assistant="conversation", device_id="dev_1",
        )
        mock_store = MagicMock()
        mock_store.async_load = AsyncMock(return_value=[])
        mock_store.async_save = AsyncMock()
        with patch.object(llm_api_mod.er, "async_get",
                          return_value=MagicMock(entities={})), \
             patch("custom_components.tritue_youtube_player.llm_api.Store",
                   return_value=mock_store):
            tool = llm_api_mod.PlayPlaylistTool()
            result = await tool.async_call(
                hass,
                llm_helpers.ToolInput("phat_playlist", {
                    "danh_sach": pid, "loa": "phòng khách", "nguon_playlist": "kho"}),
                context,
            )
        self.assertNotIn("loi", result,
                         f"Assist phát playlist Zing phải chạy được, got: {result}")
        play_calls = [c for c in hass.services.async_call.await_args_list
                      if c.args[:2] == ("media_player", "play_media")]
        self.assertEqual(1, len(play_calls))

    # ---- BỔ SUNG: đường play_queue vốn đã dùng url-trước (đối chứng) ----
    async def test_g_duong_play_queue_zing_van_chay(self):
        from custom_components.tritue_youtube_player.playback import async_play_queue
        from custom_components.tritue_youtube_player.queue_store import DATA_KEY
        # Hàng đợi dùng bài đã có trong kho playlist -> URL Zing đã xác thực.
        self._tao_playlist([dict(ZING_ITEM)])
        queue = {"items": [{**normalize_item(dict(ZING_ITEM)), "uid": "u1"}],
                 "current": "u1"}
        fake_store = MagicMock()
        fake_store.async_get = AsyncMock(return_value=queue)
        fake_store.async_change = AsyncMock(return_value=(queue, 0))
        self.hass.data[DATA_KEY] = fake_store
        await async_play_queue(
            self.hass, self.entry, queue_code="ab12cd34ef56",
            entity_ids=[SPEAKER], dispatch_fn=async_dispatch)
        self.assertEqual(1, len(self._play_media_calls()))

    # ---- Nguyên tắc chọn target: url trước, id sau — cho MỌI nguồn ----
    def test_h_item_target_url_truoc_moi_nguon(self):
        self.assertEqual(ZING_URL, item_target({"source": "zing", "id": ZING_ID, "url": ZING_URL}))
        self.assertEqual(f"https://www.youtube.com/watch?v={YT_ID}",
                         item_target({"source": "youtube", "id": YT_ID,
                                      "url": f"https://www.youtube.com/watch?v={YT_ID}"}))
        self.assertEqual(f"https://www.facebook.com/watch/?v={FB_ID}",
                         item_target({"source": "facebook", "id": FB_ID,
                                      "url": f"https://www.facebook.com/watch/?v={FB_ID}"}))
        self.assertEqual("http://example.com/a.mp3",
                         item_target({"source": "http", "id": "http://example.com/a.mp3",
                                      "url": "http://example.com/a.mp3"}))
        # Rút về id khi thiếu url.
        self.assertEqual(YT_ID, item_target({"source": "youtube", "id": YT_ID}))

    # ---- Chống tái phạm: không còn chỗ nào chọn id-trước-url trong integration ----
    def test_i_khong_con_id_truoc_url_trong_integration(self):
        mau = re.compile(r'get\("id"\)\s*or[^#\n]*get\("url"\)')
        vi_pham = []
        comp = ROOT / "custom_components" / "tritue_youtube_player"
        for py in sorted(comp.glob("*.py")):
            for i, dong in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if mau.search(dong):
                    vi_pham.append(f"{py.name}:{i}: {dong.strip()}")
        self.assertEqual([], vi_pham,
                         "còn chỗ chọn id trước url: " + "; ".join(vi_pham))


if __name__ == "__main__":
    unittest.main()
