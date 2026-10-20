"""Mã chia sẻ `TTPL1.` (nút chia sẻ cũ của thẻ) dùng được cho play_playlist / phat_playlist.

Mã mang cả nội dung playlist nên lần đầu được NHẬP vào kho (như thẻ làm khi dán mã); các lần sau dùng lại id đã nhập,
không tạo bản trùng. Ánh xạ «băm của mã → id» nằm ở bộ nhớ của Home Assistant.
"""

import base64
import json
import unittest
import zlib
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.tritue_youtube_player import services as services_mod
from custom_components.tritue_youtube_player import share_codes
from custom_components.tritue_youtube_player.api import CannotConnectError, YouTubePlayerApiError


def make_code(name="Nhac thu", rows=None):
    """Dựng mã đúng định dạng của máy phát: TTPL1. + base64url(zlib(JSON gọn))."""
    rows = rows if rows is not None else [["youtube", "dQw4w9WgXcQ", "", "Bai A", "", 200, ""]]
    raw = zlib.compress(json.dumps({"n": name, "i": rows}, ensure_ascii=False, separators=(",", ":")).encode(), 9)
    return "TTPL1." + base64.urlsafe_b64encode(raw).decode().rstrip("=")


class FakeStore:
    def __init__(self, data=None):
        self.data = data
        self.saved = None

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.saved = dict(data)
        self.data = dict(data)


def client_with(playlists, imported_id="abcdef012345", import_error=None):
    client = MagicMock()
    client.async_playlists = AsyncMock(return_value={"playlists": playlists})
    if import_error:
        client.async_playlist_action = AsyncMock(side_effect=import_error)
    else:
        client.async_playlist_action = AsyncMock(return_value={"playlist": {"id": imported_id}, "playlists": []})
    return client


class ResolveShareCodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_id_trong_kho_di_thang_khong_goi_may_chu(self):
        client = client_with([])
        got = await share_codes.async_playlist_id_from_code(None, client, "abcdef012345", store=FakeStore())
        self.assertEqual("abcdef012345", got)
        client.async_playlists.assert_not_called()
        client.async_playlist_action.assert_not_called()

    async def test_ma_moi_duoc_nhap_mot_lan_va_nho_anh_xa(self):
        code = make_code()
        client, store = client_with([]), FakeStore()
        got = await share_codes.async_playlist_id_from_code(None, client, code, store=store)
        self.assertEqual("abcdef012345", got)
        client.async_playlist_action.assert_awaited_once_with({"action": "import", "text": code})
        self.assertEqual(1, len(store.saved))
        self.assertEqual(["abcdef012345"], list(store.saved.values()))

    async def test_goi_lai_cung_ma_khong_tao_ban_trung(self):
        code = make_code()
        store = FakeStore()
        first = client_with([])
        await share_codes.async_playlist_id_from_code(None, first, code, store=store)
        # lần sau: playlist đã nhập vẫn còn trong kho → dùng lại id, KHÔNG nhập nữa
        second = client_with([{"id": "abcdef012345", "name": "Nhac thu", "items": []}])
        got = await share_codes.async_playlist_id_from_code(None, second, code, store=store)
        self.assertEqual("abcdef012345", got)
        second.async_playlist_action.assert_not_called()

    async def test_playlist_da_bi_xoa_khoi_kho_thi_nhap_lai(self):
        code = make_code()
        from hashlib import sha256
        digest = sha256(code.encode()).hexdigest()
        store = FakeStore({digest: "oldoldoldold"})
        client = client_with([{"id": "khacid012345", "name": "x", "items": []}], imported_id="newnewnewnew")
        got = await share_codes.async_playlist_id_from_code(None, client, code, store=store)
        self.assertEqual("newnewnewnew", got)
        client.async_playlist_action.assert_awaited_once()

    async def test_khoang_trang_va_xuong_dong_trong_ma_duoc_bo(self):
        code = make_code()
        spaced = code[:20] + "\n  " + code[20:]
        client = client_with([])
        await share_codes.async_playlist_id_from_code(None, client, spaced, store=FakeStore())
        client.async_playlist_action.assert_awaited_once_with({"action": "import", "text": code})

    async def test_ma_hong_hoac_qua_dai_la_loi_sach(self):
        for bad in ("", "TTPL1." + "A" * 300_001, "ttpl1.abc", "https://youtu.be/x", "../../etc/passwd", "abc"):
            with self.subTest(code=bad[:15]):
                client = client_with([])
                with self.assertRaises(ValueError) as cm:
                    await share_codes.async_playlist_id_from_code(None, client, bad, store=FakeStore())
                self.assertEqual("invalid_playlist_code", str(cm.exception))
                client.async_playlist_action.assert_not_called()

    async def test_nhap_that_bai_khong_ghi_nho_va_bao_ma_loi(self):
        store = FakeStore()
        bad_id = client_with([], imported_id="id la!")
        with self.assertRaises(ValueError) as cm:
            await share_codes.async_playlist_id_from_code(None, bad_id, make_code(), store=store)
        self.assertEqual("playlist_import_failed", str(cm.exception))
        self.assertIsNone(store.saved)
        down = client_with([], import_error=CannotConnectError("x"))
        with self.assertRaises(YouTubePlayerApiError):
            await share_codes.async_playlist_id_from_code(None, down, make_code(), store=store)
        self.assertIsNone(store.saved)

    async def test_so_anh_xa_nho_duoc_chan_tran(self):
        store = FakeStore({f"{i:064x}": "aaaaaaaaaaaa" for i in range(share_codes.MAX_SHARE_IMPORTS)})
        await share_codes.async_playlist_id_from_code(None, client_with([]), make_code(), store=store)
        self.assertLessEqual(len(store.saved), share_codes.MAX_SHARE_IMPORTS)


def _row(vid, title="Bai"):
    return ["youtube", vid, "", title, "", 100, ""]


def _playlist(pid, vids, name="home"):
    return {"id": pid, "name": name, "items": [{"source": "youtube", "id": v} for v in vids]}


class KhongTaoBanSaoTests(unittest.IsolatedAsyncioTestCase):
    """Báo cáo chủ máy 20/10/2026: playlist «home» (44 bài) đã có trong kho, chạy play_playlist với mã TTPL1 của chính nó
    thì kho có thêm một «home» thứ hai. Ánh xạ «mã → id» chỉ nhớ những gì action tự nhập nên bản có sẵn bị bỏ qua."""

    VIDS = ["dQw4w9WgXcQ", "kJQP7kiw5Fk", "9bZkp7q19f0"]

    def _code(self, vids=None, name="home"):
        return make_code(name=name, rows=[_row(v) for v in (vids or self.VIDS)])

    async def test_playlist_giong_het_da_co_thi_dung_lai_khong_nhap_them(self):
        code, store = self._code(), FakeStore()
        client = client_with([_playlist("aaaaaaaaaaaa", ["x" * 11], name="khac"), _playlist("bbbbbbbbbbbb", self.VIDS)])
        got = await share_codes.async_playlist_id_from_code(None, client, code, store=store)
        self.assertEqual("bbbbbbbbbbbb", got)
        client.async_playlist_action.assert_not_called()
        self.assertEqual(["bbbbbbbbbbbb"], list(store.saved.values()))   # lần sau khỏi so sánh nữa

    async def test_doi_ten_khong_lam_no_thanh_ban_khac(self):
        client = client_with([_playlist("bbbbbbbbbbbb", self.VIDS, name="Ten da doi")])
        got = await share_codes.async_playlist_id_from_code(None, client, self._code(name="home"), store=FakeStore())
        self.assertEqual("bbbbbbbbbbbb", got)

    async def test_khac_thu_tu_hoac_khac_bai_thi_van_nhap_moi(self):
        for have in (list(reversed(self.VIDS)), self.VIDS[:2], self.VIDS + ["x1x1x1x1x1x"]):
            with self.subTest(have=len(have)):
                client = client_with([_playlist("bbbbbbbbbbbb", have)], imported_id="cccccccccccc")
                got = await share_codes.async_playlist_id_from_code(None, client, self._code(), store=FakeStore())
                self.assertEqual("cccccccccccc", got)
                client.async_playlist_action.assert_awaited_once()

    async def test_playlist_rong_khong_bao_gio_duoc_coi_la_ban_trung(self):
        # mã không có bài hợp lệ → khoá rỗng → để máy phát phán (playlist_empty), không dùng lại playlist rỗng nào
        code = make_code(rows=[["youtube", "sai", "", "x", "", 0, ""]])
        client = client_with([_playlist("bbbbbbbbbbbb", [])], imported_id="cccccccccccc")
        await share_codes.async_playlist_id_from_code(None, client, code, store=FakeStore())
        client.async_playlist_action.assert_awaited_once()

    async def test_gap_loi_ket_noi_sau_khi_may_phat_da_tao_thi_lan_sau_khong_tao_tiep(self):
        code, store = self._code(), FakeStore()
        down = client_with([], import_error=CannotConnectError("het gio"))
        with self.assertRaises(YouTubePlayerApiError):
            await share_codes.async_playlist_id_from_code(None, down, code, store=store)
        # máy phát thực ra đã tạo xong trước khi hết giờ: lần chạy lại thấy nó trong kho
        retry = client_with([_playlist("dddddddddddd", self.VIDS)])
        got = await share_codes.async_playlist_id_from_code(None, retry, code, store=store)
        self.assertEqual("dddddddddddd", got)
        retry.async_playlist_action.assert_not_called()

    async def test_hai_lan_goi_chong_nhau_chi_nhap_mot_lan(self):
        import asyncio
        code, store = self._code(), FakeStore()
        kho = []

        async def playlists():
            return {"playlists": list(kho)}

        async def action(payload):
            await asyncio.sleep(0.05)               # lúc máy phát đang đọc, lần gọi thứ hai đã tới
            kho.append(_playlist("eeeeeeeeeeee", self.VIDS))
            return {"playlist": {"id": "eeeeeeeeeeee"}, "playlists": []}

        client = MagicMock()
        client.async_playlists = playlists
        client.async_playlist_action = AsyncMock(side_effect=action)
        got = await asyncio.gather(*[share_codes.async_playlist_id_from_code(None, client, code, store=store) for _ in range(5)])
        self.assertEqual(["eeeeeeeeeeee"] * 5, got)
        self.assertEqual(1, client.async_playlist_action.await_count)

    async def test_nhan_playlist_code_dan_nguyen_dong_duoc_chap_nhan(self):
        client = client_with([])
        for raw in ("playlist_code: abcdef012345", "'playlist_code: abcdef012345'", ' PLAYLIST_CODE:"abcdef012345" '):
            with self.subTest(raw=raw):
                got = await share_codes.async_playlist_id_from_code(None, client, raw, store=FakeStore())
                self.assertEqual("abcdef012345", got)
        code = self._code()
        client2 = client_with([_playlist("bbbbbbbbbbbb", self.VIDS)])
        got = await share_codes.async_playlist_id_from_code(None, client2, f"playlist_code: {code}", store=FakeStore())
        self.assertEqual("bbbbbbbbbbbb", got)


class HandlerShareCodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_play_playlist_nhan_ttpl1_va_phat_theo_id_da_nhap(self):
        hass, entry = MagicMock(), MagicMock()
        playlist = {"id": "abcdef012345", "name": "Nhac thu", "items": [{"source": "youtube", "id": "dQw4w9WgXcQ"}]}
        entry.runtime_data.client = client_with([playlist])
        code = make_code()
        call = MagicMock(data={"entry_id": "e", "playlist_code": code, "entity_id": ["media_player.s1"]})
        with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry), \
             patch.object(services_mod, "async_dispatch", new=AsyncMock()) as dispatch, \
             patch.object(share_codes, "Store", return_value=FakeStore()):
            await services_mod._async_handle_play_playlist(hass, call)
        kwargs = dispatch.await_args.kwargs
        self.assertEqual("abcdef012345", kwargs["playlist_id"])
        self.assertEqual("dQw4w9WgXcQ", kwargs["target"])

    async def test_play_playlist_ma_hong_la_loi_dich_vu_sach(self):
        hass, entry = MagicMock(), MagicMock()
        entry.runtime_data.client = client_with([])
        call = MagicMock(data={"entry_id": "e", "playlist_code": "TTPL1.%%%", "entity_id": ["media_player.s1"]})
        with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry), \
             patch.object(share_codes, "Store", return_value=FakeStore()):
            with self.assertRaises(services_mod.ServiceValidationError) as cm:
                await services_mod._async_handle_play_playlist(hass, call)
        self.assertEqual("invalid_playlist_code", cm.exception.translation_key)

    async def test_may_chu_loi_khi_nhap_la_communication_error(self):
        hass, entry = MagicMock(), MagicMock()
        entry.runtime_data.client = client_with([], import_error=CannotConnectError("x"))
        call = MagicMock(data={"entry_id": "e", "playlist_code": make_code(), "entity_id": ["media_player.s1"]})
        with patch.object(services_mod, "_loaded_entry_or_raise", return_value=entry), \
             patch.object(share_codes, "Store", return_value=FakeStore()):
            with self.assertRaises(services_mod.ServiceValidationError) as cm:
                await services_mod._async_handle_play_playlist(hass, call)
        self.assertEqual("communication_error", cm.exception.translation_key)


if __name__ == "__main__":
    unittest.main()
