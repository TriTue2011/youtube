"""NV227 — playlist/queue MỚI tạo trên thẻ không hiện trong ô chọn của action HA.

Đo từng giả thuyết trong spec bằng lõi thật (store + handler tạo + lua_chon_action):

(1) Đường tạo trên thẻ có kích làm mới không?
    → CÓ cho playlist (POST /playlists) và queue (POST /queue) — xem DuongTaoTrenTheTests.
(2) Gộp 3 giây có sai không? → KHÔNG: hẹn lại huỷ hẹn cũ (HenGioTests ở test_lua_chon_action.py),
    lần làm mới chạy đúng 3 giây sau lần đổi cuối.
(3) `async_set_service_schema` chỉ cập nhật bộ nhớ đệm phía HA — giao diện HA (tab Hành động)
    đã tải mô tả một lần và CHỈ tải lại khi có sự kiện `service_registered`/`service_removed`
    (mã HA: `ServiceRegistry.async_register`/`async_remove` trong core.py bắn hai sự kiện này;
    `helpers/service.py: async_set_service_schema` KHÔNG bắn gì). → Đây là gốc rễ: backend có
    danh sách mới sau ~3 giây nhưng frontend không bao giờ biết. Xem SuKienFrontendTests.
(4) Đường KHÁC nguồn: phát bằng mã chia sẻ TTPL1 (action/Assist) NHẬP một playlist mới vào kho
    mà không hề báo đổi → ô chọn thiếu cả ở phía backend. Xem DuongMaChiaSeTests.

Nguyên tắc sửa: MỌI thay đổi kho playlist/queue đi qua MỘT điểm báo đổi duy nhất
(`lam_moi_lua_chon_sau`), và sau khi đặt lại mô tả, `async_cap_nhat_lua_chon` bắn
`service_registered` cho từng action để frontend tải lại mô tả ngay — không cần khởi động lại HA.
"""

import base64
import json
import types
import unittest
import zlib
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.tritue_youtube_player import http as http_view
from custom_components.tritue_youtube_player import lua_chon_action as lc
from custom_components.tritue_youtube_player import share_codes as sc
from custom_components.tritue_youtube_player.api import YouTubePlayerApiError
from custom_components.tritue_youtube_player.const import DOMAIN
from custom_components.tritue_youtube_player.queue_store import QueueStore

SUKIEN = "service_registered"          # homeassistant.const.EVENT_SERVICE_REGISTERED


class _KhoTrongBoNho:
    """Thay `homeassistant.helpers.storage.Store`: không chạm đĩa, không cần vòng lặp sự kiện của hass thật."""

    def __init__(self):
        self.doc = None

    async def async_load(self):
        return self.doc

    async def async_save(self, doc):
        self.doc = doc


def _pl(pid, name, n=1):
    return {"id": pid, "name": name, "items": [{"id": f"v{i}"} for i in range(n)]}


def _hass_va_entry(playlists):
    """hass giả: một entry LOADED mà client trả `playlists` (list này sửa được để giả lập máy phát)."""
    hass = MagicMock()
    hass.data = {}
    hass.async_add_executor_job = AsyncMock(side_effect=lambda f, *a: f(*a))
    hass.states.async_all.return_value = []
    client = MagicMock()
    client.async_playlists = AsyncMock(side_effect=lambda: {"playlists": playlists})
    entry = MagicMock()
    entry.domain = DOMAIN
    entry.state = lc.ConfigEntryState.LOADED
    entry.runtime_data.client = client
    hass.config_entries.async_entries.return_value = [entry]
    hass.config_entries.async_get_entry.return_value = entry
    store = MagicMock()
    store.async_load = AsyncMock()
    store.code = "abcdef012345"
    store.async_get = AsyncMock(return_value={"items": []})
    return hass, entry, client, store


class _CapNhatBase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        registry = MagicMock()
        registry.async_get.return_value = None
        for p in (patch.object(lc.er, "async_get", return_value=registry),
                  patch.object(lc, "Store", side_effect=lambda *a, **k: MagicMock(async_load=AsyncMock(return_value=None)))):
            p.start()
            self.addCleanup(p.stop)


class SuKienFrontendTests(_CapNhatBase):
    """Gốc rễ (giả thuyết 3): đặt lại mô tả PHẢI kèm sự kiện service_registered cho frontend."""

    async def test_ban_service_registered_cho_tung_action_sau_khi_dat_mo_ta(self):
        hass, _entry, _client, store = _hass_va_entry([_pl("aaaaaaaaaaaa", "home", 44)])
        thu_tu = []
        with patch.object(lc, "get_queue_store", return_value=store), \
             patch.object(lc, "async_set_service_schema", new=lambda h, d, s, desc: thu_tu.append(("dat", s))):
            hass.bus.async_fire.side_effect = lambda ten, data=None, **k: thu_tu.append(("ban", data["service"]))
            await lc.async_cap_nhat_lua_chon(hass)
        ban = [c for c in hass.bus.async_fire.call_args_list if c.args[0] == SUKIEN]
        self.assertEqual(
            {(DOMAIN, "play_playlist"), (DOMAIN, "play_queue"), (DOMAIN, "play_on_players")},
            {(c.args[1]["domain"], c.args[1]["service"]) for c in ban},
        )
        for svc in ("play_playlist", "play_queue", "play_on_players"):   # đặt mô tả XONG mới bắn: frontend tải lại là thấy bản mới
            self.assertLess(thu_tu.index(("dat", svc)), thu_tu.index(("ban", svc)))

    async def test_reset_cung_ban_su_kien(self):
        hass, _entry, _client, store = _hass_va_entry([])
        with patch.object(lc, "get_queue_store", return_value=store), \
             patch.object(lc, "async_set_service_schema"):
            await lc.async_cap_nhat_lua_chon(hass, reset=True)
        ban = [c for c in hass.bus.async_fire.call_args_list if c.args[0] == SUKIEN]
        self.assertEqual(3, len(ban))

    async def test_loi_ban_su_kien_khong_pha_va_mo_ta_van_dat_du(self):
        hass, _entry, _client, store = _hass_va_entry([_pl("aaaaaaaaaaaa", "home")])
        hass.bus.async_fire.side_effect = RuntimeError("bus hỏng")
        with patch.object(lc, "get_queue_store", return_value=store), \
             patch.object(lc, "async_set_service_schema") as dat:
            await lc.async_cap_nhat_lua_chon(hass)          # không ném — chỉ log
        self.assertEqual(3, dat.call_count)                 # cả 3 mô tả vẫn được đặt trước khi bắn


class DuongTaoTrenTheTests(unittest.IsolatedAsyncioTestCase):
    """Mọi đường tạo/sửa playlist trên thẻ đều qua POST /playlists → phải báo đổi đúng MỘT lần."""

    PAYLOADS = {
        "go_ten_tao_moi": {"action": "create", "name": "Kiểm tra", "items": []},
        "dan_link_youtube": {"action": "create", "name": "Từ link", "items": [{"source": "youtube", "id": "dQw4w9WgXcQ", "title": "x"}]},
        "album_zing": {"action": "create", "name": "Zing", "items": [{"source": "zing", "id": "Z6ABWEDF", "title": "x", "url": "https://zingmp3.vn/bai-hat/Z6ABWEDF.html"}]},
        "nhap_link": {"action": "import", "text": "https://www.youtube.com/playlist?list=PLabc"},
        "ma_ttpl1": {"action": "import", "text": "TTPL1.eJyrVkpJLUktLskvLSpOzc5TUvIBAAA"},
        "doi_ten": {"action": "rename", "id": "aaaaaaaaaaaa", "name": "Tên mới"},
        "xoa": {"action": "delete", "id": "aaaaaaaaaaaa"},
    }

    async def _post_playlists(self, payload, loi=None):
        hass, entry, _client, _store = _hass_va_entry([])
        if loi:
            entry.runtime_data.client.async_playlist_action = AsyncMock(side_effect=loi)
        else:
            entry.runtime_data.client.async_playlist_action = AsyncMock(return_value={"playlists": []})
        request = MagicMock()
        request.app = {"hass": hass}
        request.json = AsyncMock(return_value={**payload, "entry_id": "e1"})
        view = http_view.TriTuePlaylistsView()
        view.json = lambda data, status=200: MagicMock(status=int(status), data=data)   # stub HA không có HomeAssistantView.json
        with patch.object(http_view, "lam_moi_lua_chon_sau") as bao:
            resp = await view.post(request)
        return resp, bao, hass

    async def test_moi_duong_tao_sua_xoa_playlist_deu_bao_doi(self):
        for ten, payload in self.PAYLOADS.items():
            with self.subTest(duong=ten):
                _resp, bao, hass = await self._post_playlists(payload)
                bao.assert_called_once_with(hass)

    async def test_lenh_loi_thi_khong_bao_doi(self):
        resp, bao, _hass = await self._post_playlists(
            {"action": "create", "name": "x"}, loi=YouTubePlayerApiError("invalid_playlist"))
        self.assertEqual(400, resp.status)
        bao.assert_not_called()


class DuongQueueTests(unittest.IsolatedAsyncioTestCase):
    """Kho queue đổi qua QueueStore (thẻ, Assist, phát nhạc) — điểm báo đổi duy nhất phải nằm ở kho."""

    def _store(self):
        # hass tối thiểu (Store thật của HA đọc config_dir lúc khởi tạo) + kho lưu trong bộ nhớ:
        # chạy được cả với HA giả lẫn HA thật (CI cài HA thật rồi chạy `unittest discover`).
        hass = types.SimpleNamespace(data={}, config=types.SimpleNamespace(config_dir="/nonexistent-config-for-test"))
        store = QueueStore(hass)
        store._store = _KhoTrongBoNho()
        return hass, store

    async def test_them_bai_vao_queue_bao_doi(self):
        hass, store = self._store()
        with patch.object(lc, "lam_moi_lua_chon_sau") as bao:
            await store.async_change({"action": "add", "items": [{"source": "youtube", "id": "dQw4w9WgXcQ", "title": "x"}]})
        bao.assert_called_once_with(hass)

    async def test_xoa_het_va_chuyen_bai_cung_bao_doi(self):
        hass, store = self._store()
        await store.async_load()
        with patch.object(lc, "lam_moi_lua_chon_sau") as bao:
            await store.async_change({"action": "add", "items": [{"source": "youtube", "id": "dQw4w9WgXcQ", "title": "x"}]})
            await store.async_advance(store.code)
            await store.async_change({"action": "clear"})
        self.assertEqual(3, bao.call_count)

    async def test_payload_hong_thi_khong_bao_doi(self):
        _hass, store = self._store()
        with patch.object(lc, "lam_moi_lua_chon_sau") as bao:
            with self.assertRaises(ValueError):
                await store.async_change({"action": "add", "items": []})
        bao.assert_not_called()


def _ma_ttpl1(rows):
    raw = zlib.compress(json.dumps({"i": rows}).encode())
    return "TTPL1." + base64.urlsafe_b64encode(raw).decode().rstrip("=")


class DuongMaChiaSeTests(unittest.IsolatedAsyncioTestCase):
    """Giả thuyết (4): phát bằng mã TTPL1 NHẬP playlist mới vào kho (qua action/Assist) — phải báo đổi."""

    async def test_nhap_playlist_moi_tu_ma_ttpl1_bao_doi(self):
        hass = MagicMock()
        hass.data = {}
        client = MagicMock()
        client.async_playlists = AsyncMock(return_value={"playlists": []})
        client.async_playlist_action = AsyncMock(return_value={"playlist": {"id": "abc123def456"}})
        store = MagicMock()
        store.async_load = AsyncMock(return_value={})
        store.async_save = AsyncMock()
        with patch.object(sc, "lam_moi_lua_chon_sau", create=True) as bao:
            pid = await sc.async_playlist_id_from_code(
                hass, client, _ma_ttpl1([["youtube", "dQw4w9WgXcQ", ""]]), store=store)
        self.assertEqual("abc123def456", pid)
        bao.assert_called_once_with(hass)

    async def test_ma_trung_playlist_da_co_thi_khong_nhap_khong_bao(self):
        hass = MagicMock()
        hass.data = {}
        co_san = _pl("abc123def456", "Đã có")
        co_san["items"] = [{"source": "youtube", "id": "dQw4w9WgXcQ"}]
        client = MagicMock()
        client.async_playlists = AsyncMock(return_value={"playlists": [co_san]})
        client.async_playlist_action = AsyncMock()
        store = MagicMock()
        store.async_load = AsyncMock(return_value={})
        store.async_save = AsyncMock()
        with patch.object(sc, "lam_moi_lua_chon_sau", create=True) as bao:
            pid = await sc.async_playlist_id_from_code(
                hass, client, _ma_ttpl1([["youtube", "dQw4w9WgXcQ", ""]]), store=store)
        self.assertEqual("abc123def456", pid)
        client.async_playlist_action.assert_not_called()    # dùng lại bản đã có, kho không đổi
        bao.assert_not_called()


class TaiHienTuDauDenCuoiTests(_CapNhatBase):
    """Đúng kịch bản chủ máy: thẻ tạo «Kiểm tra» → sau 3 giây ô chọn của action phải có, frontend phải được báo."""

    async def test_tao_playlist_tren_the_roi_o_chon_co_va_frontend_duoc_bao(self):
        playlists = [_pl("aaaaaaaaaaaa", "home", 44), _pl("bbbbbbbbbbbb", "Account cafe", 1)]
        hass, entry, _client, store = _hass_va_entry(playlists)
        hen = {}
        with patch.object(lc, "get_queue_store", return_value=store), \
             patch.object(lc, "async_call_later", side_effect=lambda h, tre, cb: hen.update(tre=tre, cb=cb) or MagicMock()), \
             patch.object(lc, "async_set_service_schema") as dat:
            await lc.async_cap_nhat_lua_chon(hass)                       # lúc nạp: chỉ 2 playlist cũ
            hass.bus.async_fire.reset_mock()
            # — người dùng tạo «Kiểm tra» trên thẻ —
            entry.runtime_data.client.async_playlist_action = AsyncMock(
                side_effect=lambda p: playlists.append(_pl("cccccccccccc", "Kiểm tra", 1)) or {"playlists": playlists})
            request = MagicMock()
            request.app = {"hass": hass}
            request.json = AsyncMock(return_value={"action": "create", "name": "Kiểm tra", "items": [], "entry_id": "e1"})
            view = http_view.TriTuePlaylistsView()
            view.json = lambda data, status=200: MagicMock(status=int(status), data=data)
            await view.post(request)
            self.assertEqual(lc.TRE_LAM_MOI_GIAY, hen["tre"])             # làm mới sau đúng 3 giây (gộp)
            await hen["cb"](None)                                          # hẹn giờ chạy
        dat_theo = {c.args[2]: c.args[3] for c in dat.call_args_list}
        nhan = [o["label"] for o in dat_theo["play_playlist"]["fields"]["playlist_code"]["selector"]["select"]["options"]]
        self.assertIn("Kiểm tra (1 bài)", nhan)                            # backend: ô chọn đã có mục mới
        ban = [c for c in hass.bus.async_fire.call_args_list
               if c.args[0] == SUKIEN and c.args[1] == {"domain": DOMAIN, "service": "play_playlist"}]
        self.assertTrue(ban, "frontend không được báo: ô chọn trên giao diện vẫn cũ cho tới khi tải lại trang")


class BaoDoiHongKhongPhaViecTaoTests(unittest.IsolatedAsyncioTestCase):
    """Luật cứng NV227: lỗi làm mới/báo đổi chỉ ghi log — việc tạo vừa thành công không được vỡ theo."""

    async def test_bao_doi_voi_hass_thieu_manh_khong_nem(self):
        lc.lam_moi_lua_chon_sau(None)                       # hass=None (nơi gọi cũ truyền khi đã có store riêng)
        lc.lam_moi_lua_chon_sau(MagicMock(data=None))       # hass dở dang — không ném là đạt

    async def test_nhap_ma_ttpl1_xong_du_bao_doi_hong(self):
        client = MagicMock()
        client.async_playlists = AsyncMock(return_value={"playlists": []})
        client.async_playlist_action = AsyncMock(return_value={"playlist": {"id": "abc123def456"}})
        store = MagicMock()
        store.async_load = AsyncMock(return_value={})
        store.async_save = AsyncMock()
        # hass thật của nơi gọi cũ có thể thiếu mảnh (không .data/.config_entries): báo đổi hỏng bên trong
        # điểm báo đổi duy nhất — việc NHẬP vừa xong vẫn trả id bình thường.
        pid = await sc.async_playlist_id_from_code(
            object(), client, _ma_ttpl1([["youtube", "dQw4w9WgXcQ", ""]]), store=store)
        self.assertEqual("abc123def456", pid)


if __name__ == "__main__":
    unittest.main()
