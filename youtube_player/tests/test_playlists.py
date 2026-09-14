"""Household playlists: saved from a playlist link or a share code, played as a speaker queue.

Owner 14/09/2026: "thêm các bài hát yêu thích vào playlist để nghe hoặc nghe playlist
của người khác chia sẻ. Có thể tạo nhiều playlist khác nhau", "lưu luôn playlist này
lại, không phải lưu tay từng bài mà lưu toàn bộ qua link luôn".
"""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

import playlists  # noqa: E402
from server import StreamUnavailableError, create_server  # noqa: E402

TOKEN = {"Authorization": "Bearer test-integration-token"}
YT = [
    {"source": "youtube", "kind": "video", "id": i, "url": f"https://www.youtube.com/watch?v={i}",
     "title": f"Bài {n}", "channel": "Kênh", "duration": 200, "thumbnail": f"https://i.ytimg.com/vi/{i}/hqdefault.jpg"}
    for n, i in enumerate(["dQw4w9WgXcQ", "M7lc1UVf-VE", "llPioQNSBLY"], 1)
]
ZING = {"source": "zing", "kind": "song", "id": "USJgi8Pq9Ouf", "title": "Âm Thầm Bên Em", "channel": "Sơn Tùng M-TP",
        "url": "https://zingmp3.vn/bai-hat/Am-Tham-Ben-Em-Son-Tung-M-TP/USJgi8Pq9Ouf.html", "duration": 291, "thumbnail": ""}


class PlaylistStoreTests(unittest.TestCase):
    def test_share_code_round_trip_and_bad_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            store = playlists.PlaylistStore(Path(folder) / "playlists.json")
            playlist = store.create("Chia sẻ", [*YT, ZING, YT[0], {"source": "spotify", "id": "x"}])
            self.assertEqual(4, len(playlist["items"]))
            code = playlists.share_code(playlist)
            self.assertEqual(("Chia sẻ", [i["id"] for i in playlist["items"]]),
                             (playlists.read_share_code(code)[0], [i["id"] for i in playlists.read_share_code(code)[1]]))
            for bad in ("TTPL1.abc", code[:-10], "not-a-code"):
                with self.assertRaisesRegex(ValueError, "invalid_share_code"):
                    playlists.read_share_code(bad)

    def test_the_addon_and_c2a_files_stay_identical(self):
        c2a = Path("/opt/claude-c2a/chatgpt2api/services/youtube_phat/playlists.py")
        if not c2a.exists():
            self.skipTest("c2a checkout not present")
        self.assertEqual(c2a.read_text(encoding="utf-8"), (APP_DIR / "playlists.py").read_text(encoding="utf-8"))


class PlaylistHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.server = create_server(
            host="127.0.0.1", port=0, data_dir=Path(self.temp_dir.name), app_title="Test", max_history=5,
            integration_token="test-integration-token", public_base_url="http://172.16.10.200:8099",
        )
        self.server.prefetch_streams = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def call(self, path, payload=None, headers=TOKEN):
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=None if payload is None else json.dumps(payload).encode(),
            headers={**headers, "Content-Type": "application/json"}, method="GET" if payload is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_save_a_whole_youtube_playlist_from_its_link(self):
        found = {"title": "Nhạc 8x 9x", "entries": [{"id": i["id"], "title": i["title"], "channel": "K", "duration": 200} for i in YT]}
        with patch("search.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(found))) as run:
            status, body = self.call("/api/integration/playlists", {
                "action": "import", "text": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLlcU_sdTFmvhMC__SD90WlDTTLk0fPs_D"})
        self.assertEqual(200, status, body)
        command = run.call_args.args[0]
        self.assertEqual(("yt-dlp", "500"), (command[0], command[command.index("--playlist-end") + 1]))
        self.assertIn("https://www.youtube.com/playlist?list=PLlcU_sdTFmvhMC__SD90WlDTTLk0fPs_D", command)
        self.assertEqual(("Nhạc 8x 9x", 3), (body["playlist"]["name"], len(body["playlist"]["items"])))
        self.assertEqual(["Nhạc 8x 9x"], [p["name"] for p in self.call("/api/integration/playlists")[1]["playlists"]])
        self.assertEqual(401, self.call("/api/integration/playlists", headers={})[0])

    def test_zing_album_share_code_and_wrong_links(self):
        with patch("server.fetch_zing_playlist", return_value=("Sơn Tùng hay nhất", [ZING])):
            status, body = self.call("/api/integration/playlists", {
                "action": "import", "text": "https://zingmp3.vn/album/Son-Tung/n1mqFnz65jGl.html"})
        self.assertEqual(200, status, body)
        code = self.call("/api/integration/playlists", {"action": "export", "id": body["playlist"]["id"]})[1]["code"]
        status, body = self.call("/api/integration/playlists", {"action": "import", "text": code, "name": "Của bạn"})
        self.assertEqual((200, "Của bạn", ["USJgi8Pq9Ouf"]), (status, body["playlist"]["name"], [i["id"] for i in body["playlist"]["items"]]))
        self.assertEqual((400, "invalid_playlist_link"), (lambda r: (r[0], r[1]["error"]))(
            self.call("/api/integration/playlists", {"action": "import", "text": "sơn tùng"})))
        with patch("server.fetch_zing_playlist", side_effect=StreamUnavailableError("stream_provider_failed")):
            self.assertEqual((502, "playlist_unavailable"), (lambda r: (r[0], r[1]["error"]))(
                self.call("/api/integration/playlists", {"action": "import", "text": "https://zingmp3.vn/album/X/ZWZB9WAB.html"})))

    def test_edit_commands(self):
        created = self.call("/api/integration/playlists", {"action": "add", "name": "Yêu thích", "items": [YT[0]]})[1]
        pid = created["playlist"]["id"]
        body = self.call("/api/integration/playlists", {"action": "add", "id": pid, "items": [YT[0], YT[1], YT[2]]})[1]
        self.assertEqual((2, 3), (body["added"], len(body["playlist"]["items"])))
        body = self.call("/api/integration/playlists", {"action": "move", "id": pid, "index": 2, "to": 0})[1]
        body = self.call("/api/integration/playlists", {"action": "remove", "id": pid, "index": 1})[1]
        self.assertEqual(["llPioQNSBLY", "M7lc1UVf-VE"], [i["id"] for i in body["playlist"]["items"]])
        self.assertEqual("Sáng", self.call("/api/integration/playlists", {"action": "rename", "id": pid, "name": "Sáng"})[1]["playlist"]["name"])
        self.assertEqual((400, "invalid_playlist_index"), (lambda r: (r[0], r[1]["error"]))(
            self.call("/api/integration/playlists", {"action": "remove", "id": pid, "index": 9})))
        self.assertEqual([], self.call("/api/integration/playlists", {"action": "delete", "id": pid})[1]["playlists"])

    def test_playing_a_playlist_queues_the_whole_playlist_and_saved_zing_plays(self):
        pid = self.call("/api/integration/playlists", {"action": "create", "name": "Hỗn hợp", "items": [YT[0], ZING, YT[2]]})[1]["playlist"]["id"]
        status, body = self.call("/api/integration/session", {
            "source": "zing", "target": ZING["url"], "output_entity_ids": ["media_player.phong_khach"], "playlist_id": pid})
        self.assertEqual(200, status, body)
        queue = body["session"]["queue"]
        self.assertEqual((1, ["dQw4w9WgXcQ", "USJgi8Pq9Ouf", "llPioQNSBLY"]), (queue["index"], [i["id"] for i in queue["items"]]))
        status, body = self.call("/api/integration/session", {
            "source": "youtube", "target": YT[0]["url"], "output_entity_ids": ["media_player.bep"], "playlist_id": "khongcoplaylis"})
        self.assertEqual((404, "playlist_not_found"), (status, body["error"]))


if __name__ == "__main__":
    unittest.main()
