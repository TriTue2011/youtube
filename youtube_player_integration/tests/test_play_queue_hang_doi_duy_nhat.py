"""NV186: play_queue với queue_code bỏ trống = hàng đợi duy nhất của nhà.

`services.py` cần Home Assistant (không có trong môi trường này), nên file này dựng
stub tối thiểu cho các module `homeassistant.*` rồi nạp `services` qua một gói tổng
hợp (cách của test_queue.py) — không kéo `__init__.py` nặng của tích hợp vào.

Chạy: python3 -m unittest youtube_player_integration.tests.test_play_queue_hang_doi_duy_nhat
"""

import importlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import voluptuous as vol

ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"
GOI = "tritue_youtube_player_nv186_test"

_STUB_DA_CAI = []


def _dat_stub(ten, mod):
    sys.modules[ten] = mod
    _STUB_DA_CAI.append(ten)


def cai_stub_homeassistant():
    """Stub tối thiểu cho `homeassistant.*` và `aiohttp` — chỉ đủ để nạp services.py ở mức import."""
    if "homeassistant" in sys.modules:
        return
    # Chỉ giả aiohttp khi gói thật KHÔNG có: thay gói thật bằng bản giả làm hỏng mọi test khác chạy chung (test_api).
    if importlib.util.find_spec("aiohttp") is None:
        _dat_aiohttp_gia()
    _dat_homeassistant_gia()


def _dat_aiohttp_gia():
    aiohttp = types.ModuleType("aiohttp")

    class ClientSession:
        pass

    class ClientTimeout:
        def __init__(self, *args, **kwargs):
            pass

    class ClientError(Exception):
        pass

    class ContentTypeError(ClientError):
        pass

    aiohttp.ClientSession = ClientSession
    aiohttp.ClientTimeout = ClientTimeout
    aiohttp.ClientError = ClientError
    aiohttp.ContentTypeError = ContentTypeError
    _dat_stub("aiohttp", aiohttp)


def _dat_homeassistant_gia():
    ha = types.ModuleType("homeassistant")
    ha.__path__ = []
    _dat_stub("homeassistant", ha)

    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntryState = types.SimpleNamespace(LOADED="loaded")
    _dat_stub("homeassistant.config_entries", config_entries)

    const = types.ModuleType("homeassistant.const")
    const.ATTR_ENTITY_ID = "entity_id"
    const.STATE_UNAVAILABLE = "unavailable"
    _dat_stub("homeassistant.const", const)

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = MagicMock
    core.ServiceCall = MagicMock
    _dat_stub("homeassistant.core", core)

    exceptions = types.ModuleType("homeassistant.exceptions")

    class ServiceValidationError(Exception):
        def __init__(self, translation_domain=None, translation_key=None, **kwargs):
            super().__init__(translation_key)
            self.translation_domain = translation_domain
            self.translation_key = translation_key

    exceptions.ServiceValidationError = ServiceValidationError
    _dat_stub("homeassistant.exceptions", exceptions)

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    _dat_stub("homeassistant.helpers", helpers)

    cv = types.ModuleType("homeassistant.helpers.config_validation")
    cv.string = vol.Coerce(str)
    cv.boolean = vol.Coerce(bool)
    cv.entity_ids = vol.Coerce(list)
    _dat_stub("homeassistant.helpers.config_validation", cv)
    helpers.config_validation = cv

    er = types.ModuleType("homeassistant.helpers.entity_registry")
    er.async_get = MagicMock()
    _dat_stub("homeassistant.helpers.entity_registry", er)
    helpers.entity_registry = er

    storage = types.ModuleType("homeassistant.helpers.storage")

    class Store:
        def __init__(self, hass, version, key):
            self.hass = hass
            self.version = version
            self.key = key

        async def async_load(self):
            return None

        async def async_save(self, data):
            pass

    storage.Store = Store
    _dat_stub("homeassistant.helpers.storage", storage)
    helpers.storage = storage

    util = types.ModuleType("homeassistant.util")
    util.__path__ = []
    _dat_stub("homeassistant.util", util)
    dt = types.ModuleType("homeassistant.util.dt")
    from datetime import datetime, timezone

    dt.utcnow = lambda: datetime.now(timezone.utc)
    _dat_stub("homeassistant.util.dt", dt)
    util.dt = dt


def tai_services():
    cai_stub_homeassistant()
    if GOI not in sys.modules:
        package = types.ModuleType(GOI)
        package.__path__ = [str(COMPONENT_DIR)]
        sys.modules[GOI] = package
    return importlib.import_module(f"{GOI}.services")


def tearDownModule():
    for ten in reversed(_STUB_DA_CAI):
        sys.modules.pop(ten, None)
    sys.modules.pop(GOI, None)
    _STUB_DA_CAI.clear()


services_mod = tai_services()


def _tao_store(hass):
    store = services_mod.get_queue_store(hass)
    store._store.async_save = AsyncMock()
    store._store.async_load = AsyncMock(return_value={"queues": {}})
    return store


async def _them_bai(store, key, ma="dQw4w9WgXcQ"):
    await store.async_change({
        "key": key,
        "action": "add",
        "items": [{"id": ma, "title": "Song", "source": "youtube"}],
    })


class PlayQueueHangDoiDuyNhatTests(unittest.IsolatedAsyncioTestCase):
    async def test_bo_trong_queue_code_phat_hang_doi_duy_nhat(self):
        """NV186 (0.27.19): bỏ trống queue_code = hàng đợi duy nhất của nhà.

        Thêm bài bằng khoá cũ của loa B; gọi play_queue với queue_code trống trên loa A
        → phát đúng bài của loa B; phiên được gắn mã 12 ký tự của hàng đợi duy nhất."""
        hass = MagicMock()
        hass.data = {}
        entry = MagicMock()
        entry.entry_id = "test_entry"
        store = _tao_store(hass)
        await _them_bai(store, "media_player.speaker_b")
        code = store.code
        self.assertRegex(code, r"^[a-z0-9]{12}$")

        with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry), \
             patch.object(services_mod, "async_dispatch", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = {"session_id": "sess_nv186", "target_count": 1}
            call = MagicMock(data={"entry_id": "test_entry", "queue_code": "", "entity_id": ["media_player.speaker_a"]})
            await services_mod._async_handle_play_queue(hass, call)

            mock_dispatch.assert_awaited_once()
            self.assertEqual(
                "dQw4w9WgXcQ", mock_dispatch.call_args.kwargs["target"],
                "queue_code trống phải phát hàng đợi duy nhất (chứa bài thêm bằng khoá loa B), không phải hàng đợi của loa A",
            )

            sessions_mod = importlib.import_module(f"{GOI}.sessions")
            self.assertEqual(
                code, sessions_mod.session_queue_key({"session_id": "sess_nv186"}),
                "phiên phải gắn mã 12 ký tự của hàng đợi duy nhất",
            )

    async def test_khoa_cu_va_ma_12_ky_tu_cung_mot_hang_doi(self):
        """NV186: queue_code là khoá cũ (media_player.x) hay mã 12 ký tự đều phát cùng một hàng đợi."""
        hass = MagicMock()
        hass.data = {}
        entry = MagicMock()
        entry.entry_id = "test_entry"
        store = _tao_store(hass)
        await _them_bai(store, "media_player.speaker_x", ma="kJQP7kiw5Fk")
        code = store.code

        for raw in ("media_player.speaker_x", code):
            with self.subTest(raw=raw):
                with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry), \
                     patch.object(services_mod, "async_dispatch", new_callable=AsyncMock) as mock_dispatch:
                    mock_dispatch.return_value = {"session_id": "sess_k", "target_count": 1}
                    call = MagicMock(data={"entry_id": "test_entry", "queue_code": raw, "entity_id": ["media_player.s1"]})
                    await services_mod._async_handle_play_queue(hass, call)
                    mock_dispatch.assert_awaited_once()
                    self.assertEqual("kJQP7kiw5Fk", mock_dispatch.call_args.kwargs["target"])


if __name__ == "__main__":
    unittest.main()
