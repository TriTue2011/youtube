"""NV202: playlist GỘP NHIỀU NGUỒN (YouTube + Zing + Facebook + link http) phải
chạy HẾT — tự chuyển bài qua lại giữa các nguồn, qua cả hai đường action và thẻ.

BƯỚC 1 (đo đỏ trước): các test dưới đây chạy qua `advance` + `async_dispatch`
thật (giả mạng/phát), ghi NƠI RƠI khi hỏng.

Chạy: python3 -m pytest youtube_player_integration/tests/test_nv202_playlist_gop_nhieu_nguon.py -q
"""

import asyncio
import enum
import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import voluptuous as vol

ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"
GOI = "tritue_youtube_player_nv202_test"

_STUB_DA_CAI = []


def _dat_stub(ten, mod):
    sys.modules[ten] = mod
    _STUB_DA_CAI.append(ten)


def cai_stub_homeassistant():
    """Stub tối thiểu cho homeassistant.* và aiohttp — chỉ đủ nạp module ở mức import."""
    if "homeassistant" in sys.modules:
        return
    # Chỉ giả aiohttp khi gói thật KHÔNG có: thay gói thật bằng bản giả làm hỏng test khác chạy chung (test_api).
    if importlib.util.find_spec("aiohttp") is None:
        _dat_aiohttp_gia()
    _dat_homeassistant_gia()


def _dat_aiohttp_gia():
    aiohttp = types.ModuleType("aiohttp")

    class ClientSession:
        pass

    class ClientTimeout:
        def __init__(self, *a, **k):
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

    comp = types.ModuleType("homeassistant.components")
    comp.__path__ = []
    _dat_stub("homeassistant.components", comp)
    mp = types.ModuleType("homeassistant.components.media_player")

    class MediaPlayerEntityFeature(enum.IntFlag):
        SEEK = 2
        VOLUME_SET = 4

    mp.MediaPlayerEntityFeature = MediaPlayerEntityFeature
    _dat_stub("homeassistant.components.media_player", mp)

    ce = types.ModuleType("homeassistant.config_entries")
    ce.ConfigEntryState = types.SimpleNamespace(LOADED="loaded")
    _dat_stub("homeassistant.config_entries", ce)

    const = types.ModuleType("homeassistant.const")
    const.ATTR_ENTITY_ID = "entity_id"
    const.STATE_UNAVAILABLE = "unavailable"
    _dat_stub("homeassistant.const", const)

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = MagicMock
    core.ServiceCall = MagicMock
    core.Event = MagicMock
    core.EventStateChangedData = MagicMock
    core.callback = lambda f: f
    _dat_stub("homeassistant.core", core)

    exc = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    class ServiceValidationError(HomeAssistantError):
        def __init__(self, msg="", translation_domain=None, translation_key=None, **kw):
            super().__init__(msg or translation_key)
            self.translation_domain = translation_domain
            self.translation_key = translation_key

    exc.HomeAssistantError = HomeAssistantError
    exc.ServiceValidationError = ServiceValidationError
    _dat_stub("homeassistant.exceptions", exc)

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

    net = types.ModuleType("homeassistant.helpers.network")
    net.get_url = MagicMock(side_effect=Exception("no url"))
    _dat_stub("homeassistant.helpers.network", net)
    helpers.network = net

    storage = types.ModuleType("homeassistant.helpers.storage")

    class Store:
        def __init__(self, hass, version, key):
            pass

        async def async_load(self):
            return None

        async def async_save(self, data):
            pass

    storage.Store = Store
    _dat_stub("homeassistant.helpers.storage", storage)
    helpers.storage = storage

    event = types.ModuleType("homeassistant.helpers.event")
    event.async_call_later = MagicMock()
    event.async_track_state_change_event = MagicMock()
    _dat_stub("homeassistant.helpers.event", event)
    helpers.event = event

    util = types.ModuleType("homeassistant.util")
    util.__path__ = []
    _dat_stub("homeassistant.util", util)
    dt = types.ModuleType("homeassistant.util.dt")
    from datetime import datetime, timezone

    dt.utcnow = lambda: datetime.now(timezone.utc)
    _dat_stub("homeassistant.util.dt", dt)
    util.dt = dt


def tai(ten):
    cai_stub_homeassistant()
    if GOI not in sys.modules:
        package = types.ModuleType(GOI)
        package.__path__ = [str(COMPONENT_DIR)]
        sys.modules[GOI] = package
    return importlib.import_module(f"{GOI}.{ten}")


def tearDownModule():
    for ten in reversed(_STUB_DA_CAI):
        sys.modules.pop(ten, None)
    sys.modules.pop(GOI, None)
    _STUB_DA_CAI.clear()


services_mod = tai("services")
advance_mod = tai("advance")
sessions_mod = tai("sessions")
api_mod = tai("api")


def tai_session_addon():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "nv202_session_addon", ROOT / "youtube_player" / "app" / "session.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


session_addon = tai_session_addon()

def _nen(goi):
    """Nén các lần gọi liên tiếp trùng nhau (re-record media type là hành vi thật)."""
    ra = []
    for g in goi:
        if not ra or ra[-1] != g:
            ra.append(g)
    return ra


YOUTUBE = {"source": "youtube", "id": "dQw4w9WgXcQ",
           "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
           "title": "YT", "duration": 200}
YOUTUBE2 = {"source": "youtube", "id": "kJQP7kiw5Fk",
            "url": "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
            "title": "YT2", "duration": 210}
ZING = {"source": "zing", "id": "ZWO7W9WB",
        "url": "https://zingmp3.vn/bai-hat/ZWO7W9WB.html",
        "title": "Zing", "duration": 180}
FACEBOOK = {"source": "facebook", "id": "123456789012345",
            "url": "https://www.facebook.com/watch/?v=123456789012345",
            "title": "FB", "duration": 120}
HTTP = {"source": "http", "id": "https://example.com/a.mp3",
        "url": "https://example.com/a.mp3", "title": "HTTP", "duration": 100}


# ---------------------------------------------------------------------------
# A. Phiên add-on giữ hàng đợi khi chuyển bài (session.py — thuần, không cần HA)
# ---------------------------------------------------------------------------

class PhienGiuHangDoiTests(unittest.TestCase):
    def test_http_giua_playlist_khong_lam_mat_hang_doi(self):
        """Playlist [YT, Zing, FB, HTTP]: sang bài HTTP rồi vẫn còn bài kế.

        NƠI RƠI (trước sửa): PlaybackSession.start() nhánh `source == "http"`
        dựng lại hàng đợi thành [http] — playlist 4 bài còn 1 bài, hết bài HTTP
        thì dừng hẳn thay vì báo hết playlist.
        """
        ps = session_addon.PlaybackSession()
        items = [dict(i) for i in (YOUTUBE, ZING, FACEBOOK, HTTP)]
        s = ps.start("youtube", YOUTUBE["url"],
                     fallback_item={"source": "youtube", "id": YOUTUBE["id"],
                                    "url": YOUTUBE["url"], "title": "YT"},
                     output_entity_ids=["media_player.loa1"],
                     controller="ha:x", queue_items=items)
        self.assertEqual([i["source"] for i in s["queue"]["items"]],
                         ["youtube", "zing", "facebook", "http"])
        for source, tgt, fb in (
            ("zing", ZING["url"], {"source": "zing", "id": ZING["id"], "url": ZING["url"]}),
            ("facebook", FACEBOOK["id"], {"source": "facebook", "id": FACEBOOK["id"], "url": FACEBOOK["url"]}),
            ("http", HTTP["url"], None),
        ):
            s = ps.start(source, tgt, fallback_item=fb,
                         output_entity_ids=["media_player.loa1"],
                         controller="ha:x", session_id="s1")
        self.assertEqual([i["source"] for i in s["queue"]["items"]],
                         ["youtube", "zing", "facebook", "http"],
                         "sang bài http không được làm mất các bài còn lại của playlist")
        self.assertEqual(s["queue"]["index"], 3)
        nxt = sessions_mod.queue_item(
            {"queue": s["queue"]}, 1)
        # hết playlist sau bài http cuối → None (dừng êm), nhưng hàng đợi còn nguyên
        self.assertIsNone(nxt)

    def test_http_dau_playlist_tim_dung_vi_tri(self):
        """Phát từ bài HTTP giữa playlist: `find` khớp theo URL chuẩn hoá."""
        ps = session_addon.PlaybackSession()
        items = [dict(i) for i in (YOUTUBE, HTTP, ZING)]
        s = ps.start("http", HTTP["url"], fallback_item=None,
                     output_entity_ids=["media_player.loa1"],
                     controller="ha:x", queue_items=items)
        self.assertEqual(s["queue"]["index"], 1)
        self.assertEqual(s["item"]["source"], "http")

    def test_http_rieng_le_van_mot_bai(self):
        """Phát một link http riêng lẻ (không playlist): hàng đợi 1 bài như cũ."""
        ps = session_addon.PlaybackSession()
        s = ps.start("http", HTTP["url"], fallback_item=None,
                     output_entity_ids=["media_player.loa1"], controller="ha:x")
        self.assertEqual(len(s["queue"]["items"]), 1)
        self.assertEqual(s["item"]["source"], "http")


# ---------------------------------------------------------------------------
# B. Client phân loại lỗi 4xx theo nguyên tắc (mã HTTP), không theo tên nguồn
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def json(self, content_type=None):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _FakeAioSession:
    def __init__(self, status, payload):
        self._resp = _FakeResp(status, payload)

    def request(self, method, url, **kwargs):
        return self._resp


def _client_voi(status, payload):
    return api_mod.YouTubePlayerClient(
        "http://localhost:8099", "tok", _FakeAioSession(status, payload))


class ClientLoi4xxTests(unittest.IsolatedAsyncioTestCase):
    async def test_400_invalid_zing_target_la_loi_vinh_vien(self):
        """400 invalid_zing_target → InvalidTargetError (vĩnh viễn: bỏ qua bài).

        NƠI RƠI (trước sửa): api.py chỉ map riêng `invalid_youtube_target`;
        các mã 400 khác thành YouTubePlayerApiError → advance coi là tạm thời →
        thử lại 3 lần rồi DỪNG CẢ playlist.
        """
        client = _client_voi(400, {"error": "invalid_zing_target"})
        with self.assertRaises(api_mod.InvalidTargetError):
            await client._async_request("POST", "/api/integration/session")

    async def test_400_invalid_facebook_target_la_loi_vinh_vien(self):
        client = _client_voi(400, {"error": "invalid_facebook_target"})
        with self.assertRaises(api_mod.InvalidTargetError):
            await client._async_request("POST", "/api/integration/session")

    async def test_400_invalid_request_la_loi_vinh_vien(self):
        client = _client_voi(400, {"error": "invalid_request"})
        with self.assertRaises(api_mod.InvalidTargetError):
            await client._async_request("POST", "/api/integration/session")

    async def test_403_unverified_zing_target_la_loi_vinh_vien(self):
        """403: máy chủ từ chối dứt khoát — thử lại không đổi gì → vĩnh viễn."""
        client = _client_voi(403, {"error": "unverified_zing_target"})
        with self.assertRaises(api_mod.InvalidTargetError):
            await client._async_request("POST", "/api/integration/session")

    async def test_401_van_la_loi_xac_thuc(self):
        client = _client_voi(401, {"error": "unauthorized"})
        with self.assertRaises(api_mod.AuthenticationError):
            await client._async_request("POST", "/api/integration/session")

    async def test_502_stream_unavailable_van_la_tam_thoi(self):
        """502: lỗi phía máy phát/nguồn — vẫn tạm thời để advance thử lại."""
        client = _client_voi(502, {"error": "stream_unavailable"})
        with self.assertRaises(api_mod.YouTubePlayerApiError) as ctx:
            await client._async_request("POST", "/api/integration/stream")
        self.assertNotIsInstance(ctx.exception, api_mod.InvalidTargetError)


# ---------------------------------------------------------------------------
# C. Advance: bài giữa lỗi vĩnh viễn → bỏ qua, đi tiếp, không giết phiên
# ---------------------------------------------------------------------------

class _FakeState:
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}


class _FakeHass:
    def __init__(self):
        self.data = {}
        # loa hỗ trợ play_media (512) + volume_set (4) như loa thật
        self._states = {"media_player.loa1": _FakeState(
            "playing", {"supported_features": 512 | 4})}
        self.states = types.SimpleNamespace(get=lambda eid: self._states.get(eid))
        self.services = MagicMock()

    @property
    def loop(self):
        return asyncio.get_event_loop()


def _tao_entry(phien):
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.runtime_data = MagicMock()
    entry.runtime_data.data = {"sessions": [phien]}
    entry.runtime_data.async_refresh = AsyncMock()
    return entry


class _MayPhatGia:
    """Giả máy phát dùng PlaybackSession THẬT của add-on.

    `hong` = tập (source, target) sẽ lỗi như client thật sau sửa:
    InvalidTargetError (vĩnh viễn). Ghi lại mọi lần gọi phát.
    """

    def __init__(self, hong=frozenset(), hong_stream=frozenset()):
        self.ps = session_addon.PlaybackSession()
        self.hong = hong                # hỏng ở async_update_session (ngoài try)
        self.hong_stream = hong_stream  # hỏng ở async_create_stream (trong try)
        self.goi_phat = []          # [(source, target)] — mọi lần thử phát
        self.da_dung = []           # session_id bị stop

    async def async_update_session(self, source, target, outputs, **kw):
        sid = kw.get("session_id")
        pid = kw.get("playlist_id")
        self.goi_phat.append((source, target))
        if (source, target) in self.hong:
            raise api_mod.InvalidTargetError("invalid_target")
        queue_items = None
        if pid:
            queue_items = [dict(i) for i in self._playlist]
        fb = {"source": source, "id": target, "url": target, "title": target}
        return {"session": self.ps.start(
            source, target, fallback_item=fb if source != "http" else None,
            output_entity_ids=list(outputs), session_id=sid,
            controller="ha:test_entry", queue_items=queue_items)}

    async def async_create_stream(self, source, target, **kw):
        # zing/facebook/http: luồng tạo TRƯỚC khi ghi phiên (đúng thứ tự thật) —
        # bài hỏng thì lỗi ngay ở đây như client thật sau fix NV202.
        if (source, target) in self.hong_stream:
            raise api_mod.InvalidTargetError("invalid_target")
        return {"stream_url": "http://192.0.2.20:8099/api/stream/x.mp3",
                "media_content_type": "audio/mpeg"}

    async def async_stop(self, session_id=None, expected_revision=None):
        self.da_dung.append(session_id)
        return self.ps.stop(session_id=session_id)


class AdvanceBoQuaBaiLoiTests(unittest.IsolatedAsyncioTestCase):
    async def _dung(self, playlist, hong=frozenset(), hong_stream=frozenset()):
        hass = _FakeHass()
        may = _MayPhatGia(hong, hong_stream)
        may._playlist = [dict(i) for i in playlist]
        # phát bài đầu qua playlist_id như action play_playlist — bài đầu đang
        # phát (không nằm trong tập hỏng), chỉ các lần advance sau mới lỗi
        hong, may.hong = may.hong, frozenset()
        try:
            rec = await may.async_update_session(
                playlist[0]["source"], playlist[0]["url"],
                ["media_player.loa1"], playlist_id="pl123")
        finally:
            may.hong = hong
        phien = rec["session"]
        entry = _tao_entry(phien)
        entry.runtime_data.client = may
        return hass, entry, may, phien

    async def _chay_advance(self, hass, entry, may, phien, so_lan):
        """Chạy advance `so_lan` lần qua advance + skip + dispatch + play_on_players
        THẬT; chỉ giả client (máy phát) và loa."""
        hass.services.async_call = AsyncMock()  # loa nhận lệnh OK
        reg = MagicMock()
        reg.entities.values = MagicMock(return_value=[])
        sys.modules["homeassistant.helpers.entity_registry"].async_get = MagicMock(
            return_value=reg)

        adv = advance_mod.SessionAutoAdvance(hass, entry)
        for _ in range(so_lan):
            await adv._async_chuyen_bai_co_thu_lai(
                phien, services_mod.async_play_queue_next, services_mod.async_skip)
            # đồng bộ ảnh chụp phiên như coordinator refresh sau mỗi lần phát
            snap = may.ps.snapshot(phien["session_id"])
            if snap.get("session_id"):
                phien.update(snap)
        return may.goi_phat

    async def test_bai_giua_loi_vinh_vien_bo_qua_di_tiep(self):
        """Playlist [YT, Zing(hỏng), FB, HTTP]: bài Zing hỏng vĩnh viễn thì bỏ
        qua, các bài còn lại vẫn phát đủ, phiên KHÔNG bị giết giữa chừng."""
        playlist = [YOUTUBE, ZING, FACEBOOK, HTTP]
        hong = {("zing", ZING["url"])}
        hong_stream = {("facebook", FACEBOOK["url"])}  # item_target = url
        hass, entry, may, phien = await self._dung(playlist, hong, hong_stream)
        goi = await self._chay_advance(hass, entry, may, phien, 4)
        nguon = [s for s, _ in _nen(goi)]
        # youtube đầu là lần phát mở playlist; zing hỏng ở record, facebook hỏng
        # ở stream (trong try) → cả hai bị bỏ qua, http vẫn phát
        self.assertEqual(nguon, ["youtube", "zing", "facebook", "http"],
                         f"phải bỏ qua zing+fb hỏng rồi phát tiếp http; thực tế: {goi}")
        self.assertEqual(may.da_dung, [],
                         "không được stop phiên khi chỉ là bài giữa hỏng")

    async def test_het_playlist_dung_em_khong_bao_loi(self):
        """Hết bài: advance dừng êm, không ném lỗi, không thông báo."""
        playlist = [YOUTUBE, YOUTUBE2]
        hass, entry, may, phien = await self._dung(playlist)
        with patch.object(advance_mod.SessionAutoAdvance,
                           "_async_bao_loi_nguoi_dung",
                           new_callable=AsyncMock) as bao_loi:
            await self._chay_advance(hass, entry, may, phien, 2)
            bao_loi.assert_not_awaited()
        self.assertEqual([s for s, _ in _nen(may.goi_phat)],
                         ["youtube", "youtube"])

    async def test_moi_bai_deu_loi_dung_sau_nguong_khong_treo(self):
        """Mọi bài đều hỏng vĩnh viễn: dừng sau tối đa 5 lần bỏ qua + báo 1 lần."""
        YT3 = dict(YOUTUBE2, id="x" * 11,
                   url="https://www.youtube.com/watch?v=" + "x" * 11)
        ZING2 = dict(ZING, id="ZWO000002",
                     url="https://zingmp3.vn/bai-hat/ZWO000002.html")
        playlist = [YOUTUBE, ZING, FACEBOOK, YOUTUBE2, HTTP, YT3, ZING2]
        hong = {(i["source"], i["url"]) for i in playlist[1:]}
        hass, entry, may, phien = await self._dung(playlist, hong)
        with patch.object(advance_mod.SessionAutoAdvance,
                           "_async_bao_loi_nguoi_dung",
                           new_callable=AsyncMock) as bao_loi:
            await self._chay_advance(hass, entry, may, phien, 1)
            bao_loi.assert_awaited_once()
        # 1 lần phát mở playlist + tối đa 5 lần thử bỏ qua
        self.assertLessEqual(len(may.goi_phat), 6,
                             "phải dừng sau ngưỡng bỏ qua, không lặp vô hạn")


class GiuPhienKhiLoiTests(unittest.IsolatedAsyncioTestCase):
    """Thất bại khi chuyển bài (advance) không được giết phiên.

    NƠI RƠI (trước sửa): actions.async_play_on_players luôn stop phiên khi phát
    lỗi → lần skip kế dựng lại phiên 1 bài → mất cả playlist còn lại.
    """

    def _goi_that(self, **kw):
        hass = _FakeHass()
        hass.services.async_call = AsyncMock(
            side_effect=RuntimeError("loa từ chối"))
        client = MagicMock()
        client.async_update_session = AsyncMock(
            return_value={"session": {"session_id": "s9", "revision": 3,
                                      "output_entity_ids": ["media_player.loa1"]}})
        client.async_create_stream = AsyncMock(
            return_value={"stream_url": "http://192.0.2.20:8099/api/stream/x.mp3",
                          "media_content_type": "audio/mpeg"})
        client.async_stop = AsyncMock()
        return hass, client

    async def test_advance_that_bai_giu_phien(self):
        hass, client = self._goi_that()
        with self.assertRaises(RuntimeError):
            await services_mod.async_play_on_players(
                hass, client, source="zing", target=ZING["url"],
                entity_ids=["media_player.loa1"],
                target_platforms={"media_player.loa1": None},
                session_id="s9", giu_phien_khi_loi=True)
        client.async_stop.assert_not_awaited()

    async def test_phat_truc_tiep_that_bai_van_don_phien(self):
        """Đường phát trực tiếp (không phải advance): giữ nguyên ý đồ cũ —
        phát lỗi thì dọn phiên, không để phiên «ma»."""
        hass, client = self._goi_that()
        with self.assertRaises(RuntimeError):
            await services_mod.async_play_on_players(
                hass, client, source="zing", target=ZING["url"],
                entity_ids=["media_player.loa1"],
                target_platforms={"media_player.loa1": None},
                session_id="s9")
        client.async_stop.assert_awaited_once()


# ---------------------------------------------------------------------------
# D. Chuyển bài suy nguồn từ TỪNG bài (hồi quy — đường HA đã đúng)
# ---------------------------------------------------------------------------

class ChuyenBaiTheoNguonTungBaiTests(AdvanceBoQuaBaiLoiTests):
    async def test_chuyen_het_playlist_4_nguon_dung_nguon_tung_bai(self):
        """[YT → Zing → FB → HTTP]: mỗi lần chuyển phát đúng nguồn của bài tới."""
        playlist = [YOUTUBE, ZING, FACEBOOK, HTTP]
        hass, entry, may, phien = await self._dung(playlist)
        await self._chay_advance(hass, entry, may, phien, 3)
        self.assertEqual([s for s, _ in _nen(may.goi_phat)],
                         ["youtube", "zing", "facebook", "http"])


if __name__ == "__main__":
    unittest.main()
