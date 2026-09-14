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
