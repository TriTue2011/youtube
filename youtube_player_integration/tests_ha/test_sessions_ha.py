"""End-to-end on a real Home Assistant: the real add-on server (local HTTP) + the integration.

Covers: one song per speaker / several speakers on one song, auto-advance when a
speaker finishes (no browser involved), a stop mid-track does not advance,
next track per session, removing a speaker from a session, stopping a session.

Run: pip install pytest-homeassistant-custom-component, then
     pytest youtube_player_integration/tests_ha
"""
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "youtube_player" / "app"))

import server as addon  # noqa: E402
import custom_components.tritue_youtube_player as comp  # noqa: E402
from homeassistant.core import ServiceCall  # noqa: E402
from homeassistant.util import dt as dt_util  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

DOMAIN = "tritue_youtube_player"
TOKEN = "token-thu-dau-cuoi"
IDS = ["dQw4w9WgXcQ", "M7lc1UVf-VE", "llPioQNSBLY"]
KET_QUA = [
    {"source": "youtube", "kind": "video", "id": i, "url": f"https://www.youtube.com/watch?v={i}",
     "title": f"Bai {n}", "channel": "Kenh", "duration": 200, "thumbnail": "https://img.example/a.jpg"}
    for n, i in enumerate(IDS, 1)
]
LOA_A, LOA_B = "media_player.phong_khach", "media_player.bep"
LOA_FEATURES = 152461 | 512  # Google Home thật: PAUSE, VOLUME, PLAY_MEDIA, STOP…


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def addon_server(socket_enabled):
    tmp = tempfile.mkdtemp()
    srv = addon.create_server(host="127.0.0.1", port=0, data_dir=tmp, app_title="Thu", max_history=20,
                              integration_token=TOKEN)
    port = srv.server_address[1]
    srv.public_base_url = f"http://127.0.0.1:{port}"
    patches = [
        patch.object(addon, "search_youtube", return_value=KET_QUA),
        patch.object(addon, "resolve_youtube_audio",
                     side_effect=lambda vid: {"url": f"https://rr.googlevideo.com/{vid}", "headers": {}, "content_type": "audio/mp4"}),
    ]
    for p in patches:
        p.start()
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv
    srv.shutdown()
    for p in patches:
        p.stop()


async def _setup(hass, addon_server):
    calls = []

    async def ghi(call: ServiceCall):
        data = dict(call.data)
        ids = data.get("entity_id")
        data["entity_id"] = [ids] if isinstance(ids, str) else list(ids or [])
        calls.append((call.service, data))

    for loa, ten in ((LOA_A, "Phòng khách"), (LOA_B, "Bếp")):
        hass.states.async_set(loa, "idle", {"friendly_name": ten, "device_class": "speaker", "supported_features": LOA_FEATURES})
    entry = MockConfigEntry(domain=DOMAIN, data={"url": f"http://127.0.0.1:{addon_server.server_address[1]}", "token": TOKEN},
                            unique_id="thu")
    entry.add_to_hass(hass)
    with patch.object(comp, "async_register_frontend"):
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # Sau khi tích hợp nạp (nó kéo theo media_player thật): thay dịch vụ loa bằng bản ghi lại.
    for service in ("play_media", "media_stop", "volume_set", "media_play_pause"):
        hass.services.async_register("media_player", service, ghi)
    return entry, calls


def _phien(hass):
    s = hass.states.get("media_player.thu_player") or next(
        st for st in hass.states.async_all("media_player") if "sessions" in st.attributes)
    return s.attributes["sessions"]


async def _choi(hass, entry, target, loa, **them):
    await hass.services.async_call(DOMAIN, "play_on_players", {
        "entry_id": entry.entry_id, "source": "youtube", "target": target, "entity_id": loa, **them}, blocking=True)
    await hass.async_block_till_done()


def _loa_phat(hass, loa, vi_tri, thoi_luong=200, trang_thai="playing"):
    hass.states.async_set(loa, trang_thai, {
        "friendly_name": loa, "device_class": "speaker", "supported_features": LOA_FEATURES,
        "media_position": vi_tri, "media_position_updated_at": dt_util.utcnow().isoformat(), "media_duration": thoi_luong})


async def test_moi_loa_mot_bai_tu_chuyen_bai_va_dieu_khien_theo_phien(hass, addon_server):
    entry, calls = await _setup(hass, addon_server)
    client = entry.runtime_data.client
    await client.async_search("trót tin", limit=3)

    # Mỗi loa một bài.
    await _choi(hass, entry, KET_QUA[0]["url"], [LOA_A])
    await _choi(hass, entry, KET_QUA[1]["url"], [LOA_B])
    phien = _phien(hass)
    assert {tuple(p["output_entity_ids"]): p["title"] for p in phien} == {(LOA_A,): "Bai 1", (LOA_B,): "Bai 2"}
    play_a = [d for s, d in calls if s == "play_media" and d["entity_id"] == [LOA_A]]
    stream_url = play_a[-1]["media_content_id"] if play_a else ""
    assert stream_url.startswith(f"http://127.0.0.1:{addon_server.server_address[1]}/") and "/api/stream/" in stream_url

    # Loa A hết bài (trình duyệt đóng hết): tích hợp tự phát bài 2 ra A, B không bị đụng.
    calls.clear()
    _loa_phat(hass, LOA_A, 20)
    await hass.async_block_till_done()
    _loa_phat(hass, LOA_A, 195)
    await hass.async_block_till_done()
    hass.states.async_set(LOA_A, "idle", {"friendly_name": "Phòng khách", "device_class": "speaker", "supported_features": LOA_FEATURES})
    await hass.async_block_till_done()
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert [d["entity_id"] for s, d in calls if s == "play_media"] == [[LOA_A]]
    by_loa = {tuple(p["output_entity_ids"]): p for p in _phien(hass)}
    assert (by_loa[(LOA_A,)]["title"], by_loa[(LOA_A,)]["queue_index"]) == ("Bai 2", 1)
    assert by_loa[(LOA_B,)]["title"] == "Bai 2" and by_loa[(LOA_B,)]["queue_index"] == 1

    # Dừng tay giữa bài (50/200 rồi idle): KHÔNG chuyển bài.
    calls.clear()
    _loa_phat(hass, LOA_A, 50)
    await hass.async_block_till_done()
    hass.states.async_set(LOA_A, "idle", {"friendly_name": "Phòng khách", "device_class": "speaker", "supported_features": LOA_FEATURES})
    await hass.async_block_till_done()
    assert [s for s, _ in calls if s == "play_media"] == []

    # Bài kế theo phiên của B.
    sid_b = by_loa[(LOA_B,)]["session_id"]
    await hass.services.async_call(DOMAIN, "skip", {"entry_id": entry.entry_id, "session_id": sid_b, "step": 1}, blocking=True)
    await hass.async_block_till_done()
    assert [d["entity_id"] for s, d in calls if s == "play_media"] == [[LOA_B]]
    assert {tuple(p["output_entity_ids"]): p["title"] for p in _phien(hass)}[(LOA_B,)] == "Bai 3"

    # Nhiều loa chung một bài: gộp A + B vào một phiên.
    await _choi(hass, entry, KET_QUA[0]["url"], [LOA_A, LOA_B])
    phien = _phien(hass)
    assert [sorted(p["output_entity_ids"]) for p in phien] == [sorted([LOA_A, LOA_B])]

    # Bỏ tích B: A phát tiếp, B dừng.
    calls.clear()
    hass.states.async_set(LOA_B, "playing", {"friendly_name": "Bếp", "device_class": "speaker", "supported_features": LOA_FEATURES})
    await hass.services.async_call(DOMAIN, "remove_players", {"entry_id": entry.entry_id, "entity_id": [LOA_B]}, blocking=True)
    await hass.async_block_till_done()
    assert [(s, d["entity_id"]) for s, d in calls] == [("media_stop", [LOA_B])]
    assert [p["output_entity_ids"] for p in _phien(hass)] == [[LOA_A]]

    # Tích lại B để nghe chung: chỉ B nhận bài, A không bị phát lại.
    calls.clear()
    sid = _phien(hass)[0]["session_id"]
    await _choi(hass, entry, KET_QUA[0]["url"], [LOA_B], session_id=sid, join=True)
    assert [d["entity_id"] for s, d in calls if s == "play_media"] == [[LOA_B]]
    assert [sorted(p["output_entity_ids"]) for p in _phien(hass)] == [sorted([LOA_A, LOA_B])]

    # Dừng phiên.
    calls.clear()
    await hass.services.async_call(DOMAIN, "stop_session", {"entry_id": entry.entry_id, "session_id": sid}, blocking=True)
    await hass.async_block_till_done()
    assert sorted(d["entity_id"][0] for s, d in calls if s == "media_stop") == sorted([LOA_A, LOA_B]) or \
        [sorted(d["entity_id"]) for s, d in calls if s == "media_stop"] == [sorted([LOA_A, LOA_B])]
    assert _phien(hass) == []


async def test_assist_tim_10_bai_chon_loa_phat_va_dieu_khien(hass, addon_server):
    from homeassistant.core import Context
    from homeassistant.helpers import llm

    entry, calls = await _setup(hass, addon_server)
    ctx = llm.LLMContext(platform="test", context=Context(user_id="u1"), language="vi", assistant="conversation", device_id=None)
    api = await llm.async_get_api(hass, "tritue_youtube_player", ctx)
    names = {tool.name for tool in api.tools}
    assert {"tim_nhac", "danh_sach_loa", "phat_nhac", "dieu_khien_nhac", "dang_phat"} <= names

    async def call(tool, **args):
        result = await api.async_call_tool(llm.ToolInput(tool_name=tool, tool_args=args))
        await hass.async_block_till_done()
        return result

    found = await call("tim_nhac", tu_khoa="trót tin")
    assert [r["so"] for r in found["ket_qua"]] == [1, 2, 3] and found["ket_qua"][1]["ten"] == "Bai 2"
    speakers = await call("danh_sach_loa")
    assert [s["ten"] for s in speakers["loa"]] == ["Bếp", "Phòng khách"]

    # "bài 2 ở tất cả loa"
    played = await call("phat_nhac", bai="2", loa="tất cả")
    assert played["da_phat"] == "Bai 2" and sorted(played["tren_loa"]) == ["Bếp", "Phòng khách"]
    assert sorted(d["entity_id"][0] for s, d in calls if s == "play_media") == sorted([LOA_A, LOA_B])

    # "bài 3 riêng ở phong khach" (không dấu) → mỗi loa một bài
    calls.clear()
    played = await call("phat_nhac", bai="3", loa="phong khach")
    assert played["tren_loa"] == ["Phòng khách"]
    now = await call("dang_phat")
    assert sorted((p["bai"], tuple(p["loa"])) for p in now["dang_phat"]) == [("Bai 2", ("Bếp",)), ("Bai 3", ("Phòng khách",))]

    # "bài kế ở bếp", "dừng loa 2" (số theo danh sách), loa lạ
    calls.clear()
    await call("dieu_khien_nhac", lenh="bai_ke", loa="bếp")
    assert [d["entity_id"] for s, d in calls if s == "play_media"] == [[LOA_B]]
    stopped = await call("dieu_khien_nhac", lenh="dung", loa="2")
    assert [p["loa"] for p in stopped["dang_phat"]] == [["Bếp"]]
    wrong = await call("phat_nhac", bai="1", loa="gác xép")
    assert "loi" in wrong and "Phòng khách" in wrong["loa_co_the_chon"]


async def test_the_lay_luong_de_nghe_tren_may(hass, addon_server, hass_client, hass_client_no_auth):
    """Nút nghe trên thẻ / video YouTube chặn nhúng: thẻ xin luồng tiếng của bài qua HA.

    Luồng đi qua chính HA (đường dẫn đã ký): trình duyệt mở HA bằng địa chỉ nào (trong nhà,
    tên miền HTTPS, Nabu Casa) cũng tải được — chủ máy 15/09/2026 dùng 5G bị NotSupportedError
    vì thẻ đưa link http://172.16.10.38:3030/… của mạng nhà."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from homeassistant.setup import async_setup_component

    from custom_components.tritue_youtube_player.http import TriTueProxyView, TriTueStreamView

    DU_LIEU = bytes(range(256)) * 40
    da_hoi = []

    class Goc(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            da_hoi.append((self.path, self.headers.get("Range")))
            rg = self.headers.get("Range")
            if rg:
                dau, _, cuoi = rg[6:].partition("-")
                dau, cuoi = int(dau), int(cuoi or len(DU_LIEU) - 1)
                khuc = DU_LIEU[dau:cuoi + 1]
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {dau}-{dau + len(khuc) - 1}/{len(DU_LIEU)}")
            else:
                khuc = DU_LIEU
                self.send_response(200)
            self.send_header("Content-Type", "audio/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(len(khuc)))
            self.end_headers()
            self.wfile.write(khuc)

    goc = ThreadingHTTPServer(("127.0.0.1", 0), Goc)
    threading.Thread(target=goc.serve_forever, daemon=True).start()
    cong_goc = goc.server_address[1]

    entry, _ = await _setup(hass, addon_server)
    assert await async_setup_component(hass, "http", {})
    hass.http.register_view(TriTueStreamView)
    hass.http.register_view(TriTueProxyView)
    await entry.runtime_data.client.async_search("trót tin", limit=3)
    client = await hass_client()
    url = "/api/tritue_youtube_player/stream"

    with patch.object(addon, "resolve_youtube_audio",
                      side_effect=lambda vid: {"url": f"http://127.0.0.1:{cong_goc}/am/{vid}", "headers": {}, "content_type": "audio/mp4"}):
        r = await client.post(url, json={"entry_id": entry.entry_id, "source": "youtube", "target": KET_QUA[1]["url"]})
        body = await r.json()
        assert r.status == 200, body
        assert body["stream_url"].startswith("/api/tritue_youtube_player/proxy/") and "authSig=" in body["stream_url"]
        # Trình duyệt không gửi được token: đường dẫn đã ký tự đủ quyền, có Range để tua.
        tho = await hass_client_no_auth()
        r = await tho.get(body["stream_url"])
        assert r.status == 200 and await r.read() == DU_LIEU and r.headers["Content-Type"] == "audio/mp4"
        r = await tho.get(body["stream_url"], headers={"Range": "bytes=100-199"})
        assert r.status == 206 and await r.read() == DU_LIEU[100:200]
        assert r.headers["Content-Range"] == f"bytes 100-199/{len(DU_LIEU)}"
        assert da_hoi[-1] == (f"/am/{KET_QUA[1]['id']}", "bytes=100-199")
        # Không có chữ ký, hoặc mã không do thẻ xin: không chuyển tiếp.
        assert (await tho.get(body["stream_url"].split("?", 1)[0])).status == 401
        assert (await client.get("/api/tritue_youtube_player/proxy/khong-co")).status == 404
    goc.shutdown()

    # Hình của video YouTube chặn nhúng: link đã ký + link lấy thẳng cho máy trong nhà.
    with patch.object(addon, "resolve_youtube_video", return_value={
            "url": "https://rr1.googlevideo.com/v?itag=136", "headers": {}, "content_type": "video/mp4",
            "height": 720, "bitrate_kbps": 1002}) as hinh:
        r = await client.post(url, json={"entry_id": entry.entry_id, "source": "youtube_video",
                                         "target": KET_QUA[1]["url"], "max_height": 720})
        body = await r.json()
    assert r.status == 200, body
    hinh.assert_called_once_with(f"{KET_QUA[1]['id']}:720")
    assert (body["direct_url"], body["height"], body["bitrate_kbps"], body["media_content_type"]) == (
        "https://rr1.googlevideo.com/v?itag=136", 720, 1002, "video/mp4")
    assert body["stream_url"].startswith("/api/tritue_youtube_player/proxy/")

    for sai, ma in (({"entry_id": entry.entry_id, "source": "spotify", "target": "x"}, 400),
                    ({"entry_id": entry.entry_id, "source": "youtube", "target": ""}, 400),
                    ({"entry_id": "khong-co", "source": "youtube", "target": KET_QUA[0]["url"]}, 404)):
        assert (await client.post(url, json=sai)).status == ma
    assert (await (await hass_client_no_auth()).post(url, json={"entry_id": entry.entry_id})).status == 401


def _hop_mp4(typ: bytes, payload: bytes) -> bytes:
    return (8 + len(payload)).to_bytes(4, "big") + typ + payload


def _sidx_mp4(timescale: int, refs: list[tuple[int, int]]) -> bytes:
    body = bytearray()
    body += bytes((0, 0, 0, 0))
    body += (1).to_bytes(4, "big")
    body += timescale.to_bytes(4, "big")
    body += (0).to_bytes(4, "big")
    body += (0).to_bytes(4, "big")
    body += (0).to_bytes(2, "big")
    body += len(refs).to_bytes(2, "big")
    for dai, giay_don in refs:
        body += dai.to_bytes(4, "big")
        body += giay_don.to_bytes(4, "big")
        body += (0).to_bytes(4, "big")
    return _hop_mp4(b"sidx", bytes(body))


def _tep_cat_manh() -> bytes:
    """ftyp + moov + sidx + hai khúc tiếng. Khúc đầu dài 10 giây, 100 byte.

    Phần đuôi đệm cho đủ 256 KB: lời xin mục lục hỏi đúng khoảng đó, tệp ngắn
    hơn thì máy phát cứ mở khúc kế và vòng lặp không dừng.
    """
    ftyp = _hop_mp4(b"ftyp", b"dash" + b"\x00" * 12)
    moov = _hop_mp4(b"moov", b"\x00" * 20)
    sx = _sidx_mp4(1000, [(100, 10000), (40, 5000)])
    tep = ftyp + moov + sx + (b"A" * 100) + (b"B" * 40)
    return tep + bytes(262144 - len(tep))


UA_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
)


async def test_iphone_youtube_nhan_danh_sach_khuc(hass, addon_server, hass_client, hass_client_no_auth):
    """iPhone xin tiếng YouTube thì nhận danh sách khúc, không nhận cả tệp.

    Khúc đầu là 100 byte / 10 giây. Hình (youtube_video) và Android vẫn nhận tệp liền.
    """
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urljoin

    from homeassistant.setup import async_setup_component

    from custom_components.tritue_youtube_player.http import TriTueProxyView, TriTueStreamView

    tep = _tep_cat_manh()
    da_hoi = []

    class Goc(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            da_hoi.append(self.headers.get("Range"))
            rg = self.headers.get("Range")
            if rg:
                dau, _, cuoi = rg[6:].partition("-")
                dau = int(dau or 0)
                cuoi = int(cuoi) if cuoi else len(tep) - 1
                cuoi = min(cuoi, len(tep) - 1)
                khuc = tep[dau:cuoi + 1]
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {dau}-{dau + len(khuc) - 1}/{len(tep)}")
            else:
                khuc = tep
                self.send_response(200)
            self.send_header("Content-Type", "audio/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(len(khuc)))
            self.end_headers()
            self.wfile.write(khuc)

    goc = ThreadingHTTPServer(("127.0.0.1", 0), Goc)
    threading.Thread(target=goc.serve_forever, daemon=True).start()
    cong = goc.server_address[1]
    entry, _ = await _setup(hass, addon_server)
    assert await async_setup_component(hass, "http", {})
    hass.http.register_view(TriTueStreamView)
    hass.http.register_view(TriTueProxyView)
    client = await hass_client()
    tho = await hass_client_no_auth()
    url = "/api/tritue_youtube_player/stream"
    try:
        with patch.object(
            addon, "resolve_youtube_audio",
            side_effect=lambda vid: {
                "url": f"http://127.0.0.1:{cong}/am/{vid}",
                "headers": {},
                "content_type": "audio/mp4",
            },
        ):
            r = await client.post(
                url,
                json={"entry_id": entry.entry_id, "source": "youtube", "target": KET_QUA[1]["url"]},
                headers={"User-Agent": "Mozilla/5.0 (Linux; Android 14) Chrome/128.0.0.0"},
            )
            body = await r.json()
            assert r.status == 200, body
            # Tệp liền vẫn có. Danh sách là đường riêng, mọi máy đều nhận.
            assert not body["stream_url"].split("?", 1)[0].endswith(".m3u8")
            assert body["danh_sach_url"].split("?", 1)[0].endswith(".m3u8")
            ds = await tho.get(body["danh_sach_url"])
            text = await ds.text()
            assert ds.status == 200, text
            assert ds.headers["Content-Type"].startswith("application/vnd.apple.mpegurl")
            assert "#EXTINF:10.000," in text
            assert "#EXT-X-BYTERANGE:100@" in text
            # Lời xin mục lục phải có đầu có cuối, không phải «bytes=0-» cả tệp.
            assert da_hoi and da_hoi[0].startswith("bytes=0-") and da_hoi[0].split("-", 1)[1] != ""
            tuong_doi = next(dong for dong in text.splitlines() if "khoi=1" in dong and not dong.startswith("#"))
            khuc_url = urljoin("http://ha" + body["danh_sach_url"], tuong_doi).removeprefix("http://ha")
            # Mảnh đầu: 100 byte chữ A, không phải cả tệp.
            mo = text.split('BYTERANGE="', 1)[1]
            khoi = int(mo.split("@", 1)[0])
            vi = text.split("#EXT-X-BYTERANGE:100@", 1)[1]
            bat_dau = int(vi.splitlines()[0])
            r = await tho.get(khuc_url, headers={"Range": f"bytes={bat_dau}-{bat_dau + 99}"})
            assert r.status == 206
            assert await r.read() == b"A" * 100
            # Đoạn mở đầu không kéo theo phần tiếng.
            r = await tho.get(khuc_url, headers={"Range": f"bytes=0-{khoi - 1}"})
            assert r.status == 206 and len(await r.read()) == khoi
            # Đường tệp liền vẫn trả cả tệp, cho máy không nối được khúc.
            nguyen = await tho.get(body["stream_url"])
            assert nguyen.status == 200 and await nguyen.read() == tep

            # Hình YouTube cũng có danh sách, đường tệp không bị đổi thành danh sách.
            with patch.object(addon, "resolve_youtube_video", return_value={
                "url": f"http://127.0.0.1:{cong}/hinh", "headers": {},
                "content_type": "video/mp4", "height": 720, "bitrate_kbps": 1000,
            }):
                r = await client.post(
                    url,
                    json={"entry_id": entry.entry_id, "source": "youtube_video",
                          "target": KET_QUA[1]["url"], "max_height": 720},
                    headers={"User-Agent": UA_IPHONE},
                )
                hinh = await r.json()
            assert r.status == 200, hinh
            assert not hinh["stream_url"].split("?", 1)[0].endswith(".m3u8")
            assert hinh["danh_sach_url"].split("?", 1)[0].endswith(".m3u8")
    finally:
        goc.shutdown()


async def test_playlist_luu_qua_the_va_phat_ca_playlist_ra_loa(hass, addon_server, hass_client):
    """Thẻ HA: lệnh playlist qua view của tích hợp tới add-on thật; phát playlist → hàng đợi là cả playlist."""
    from homeassistant.setup import async_setup_component

    from custom_components.tritue_youtube_player.http import TriTuePlaylistsView

    entry, calls = await _setup(hass, addon_server)
    assert await async_setup_component(hass, "http", {})
    hass.http.register_view(TriTuePlaylistsView)
    client = await hass_client()
    url = "/api/tritue_youtube_player/playlists"

    r = await client.post(url, json={"entry_id": entry.entry_id, "action": "create", "name": "Nhà", "items": [KET_QUA[2], KET_QUA[0]]})
    body = await r.json()
    assert r.status == 200, body
    pid = body["playlist"]["id"]
    r = await client.get(f"{url}?entry_id={entry.entry_id}")
    assert [p["name"] for p in (await r.json())["playlists"]] == ["Nhà"]
    # Lỗi của máy phát về tới thẻ nguyên mã để thẻ giải thích.
    r = await client.post(url, json={"entry_id": entry.entry_id, "action": "import", "text": "https://example.com/x"})
    assert (r.status, (await r.json())["error"]) == (400, "invalid_playlist_link")
    assert (await client.get(f"{url}?entry_id=khong-co")).status == 404

    # Phát bài 1 của playlist ra loa: hàng đợi của phiên là playlist (không phải kết quả tìm).
    await _choi(hass, entry, KET_QUA[2]["url"], [LOA_A], playlist_id=pid)
    phien = _phien(hass)[0]
    assert (phien["title"], phien["queue_index"], phien["queue_size"]) == ("Bai 3", 0, 2)
    assert [d["entity_id"] for s, d in calls if s == "play_media"] == [[LOA_A]]
