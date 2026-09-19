import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest.mock import patch

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from server import (  # noqa: E402
    StreamUnavailableError,
    create_server,
    resolve_integration_token,
)


class YouTubePlayerHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.server = create_server(
            host="127.0.0.1",
            port=0,
            data_dir=Path(self.temp_dir.name),
            app_title="Test Player",
            max_history=2,
            integration_token="test-integration-token",
            public_base_url="http://172.16.10.200:8099",
        )
        # Background prefetch would run real yt-dlp; tests that need it turn it on.
        self.server.prefetch_streams = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def request(self, path, *, method="GET", payload=None, headers=None):
        body = None
        request_headers = dict(headers or {})
        if payload is not None:
            body = json.dumps(payload).encode()
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=body, headers=request_headers, method=method
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.load(response)

    def test_learns_the_lan_address_so_speakers_need_no_configuration(self):
        """Khong dat public_base_url: dia chi hoc duoc tu loi goi da xac thuc duoc dung."""
        self.server.public_base_url = ""
        self.server.learned_base_url = ""
        # Loopback/link-local/unspecified khong dung duoc cho loa -> phai bo qua.
        for host in ("127.0.0.1", "::1", "0.0.0.0", "169.254.3.4", "khong-phai-ip"):
            self.server.note_reachable_address(host, 8099)
            self.assertEqual(self.server.learned_base_url, "", host)
        with self.assertRaises(ValueError) as caught:
            self.server.create_stream_url("youtube", "dQw4w9WgXcQ")
        self.assertEqual(str(caught.exception), "public_base_url_required")

        # Mang noi bo cua Supervisor/docker: loa khong voi toi, phai tu choi.
        for host in ("172.30.32.1", "172.30.33.5", "172.17.0.4", "172.31.255.254"):
            self.server.note_reachable_address(host, 8099)
            self.assertEqual(self.server.learned_base_url, "", host)
        # 172.16.0.0/16 la LAN that o nhieu nha, khong duoc chan.
        self.server.note_reachable_address("172.16.99.10", 8099)
        self.assertEqual(self.server.learned_base_url, "http://172.16.99.10:8099")
        self.server.learned_base_url = ""
        self.server.note_reachable_address("192.0.2.28", 8099)
        self.assertEqual(self.server.learned_base_url, "http://192.0.2.28:8099")
        self.assertTrue(
            self.server.create_stream_url("youtube", "dQw4w9WgXcQ").startswith(
                "http://192.0.2.28:8099"
            )
        )

    def test_home_assistant_hint_is_used_when_the_option_is_empty(self):
        """Add-on sau NAT khong tu biet dia chi LAN; Home Assistant thi biet."""
        self.server.public_base_url = ""
        self.server.learned_base_url = ""
        url = self.server.create_stream_url(
            "youtube", "dQw4w9WgXcQ", hint="http://192.0.2.28:8099"
        )
        self.assertTrue(url.startswith("http://192.0.2.28:8099"), url)
        for xau in ("khong-phai-url", "ftp://192.0.2.28",
                    "http://192.0.2.28:8099/co/duong/dan", ""):
            with self.assertRaises(ValueError) as caught:
                self.server.create_stream_url("youtube", "dQw4w9WgXcQ", hint=xau)
            self.assertEqual(str(caught.exception), "public_base_url_required")

    def test_explicit_option_wins_over_the_hint(self):
        """public_base_url dat tay luon thang goi y cua Home Assistant."""
        url = self.server.create_stream_url(
            "youtube", "dQw4w9WgXcQ", hint="http://192.0.2.99:8099"
        )
        self.assertTrue(url.startswith("http://172.16.10.200:8099"), url)

    def test_explicit_public_base_url_wins_over_the_learned_one(self):
        """Nguoi dung dat tay thi luon thang, ke ca khi da hoc duoc dia chi khac."""
        self.server.learned_base_url = "http://192.0.2.28:8099"
        self.assertTrue(
            self.server.create_stream_url("youtube", "dQw4w9WgXcQ").startswith(
                "http://172.16.10.200:8099"
            )
        )
        # Cong ngoai khoang hop le thi khong ghi nhan.
        self.server.learned_base_url = ""
        for port in (0, 70000, "abc", None):
            self.server.note_reachable_address("192.0.2.28", port)
            self.assertEqual(self.server.learned_base_url, "", repr(port))

    def remember_public_zing_target(self, target):
        self.server.remember_public_zing_results(
            [{"source": "zing", "kind": "song", "url": target}]
        )

    def test_health_reports_ready(self):
        status, body = self.request("/api/health")

        self.assertEqual(200, status)
        self.assertEqual({"status": "ok"}, body)

    def test_integration_token_is_created_once_and_reused(self):
        token = resolve_integration_token(Path(self.temp_dir.name), "")
        reused = resolve_integration_token(Path(self.temp_dir.name), "")

        self.assertEqual(token, reused)
        self.assertGreaterEqual(len(token), 32)
        self.assertEqual(
            token,
            (Path(self.temp_dir.name) / "integration_token").read_text(
                encoding="utf-8"
            ),
        )

    def test_integration_api_requires_bearer_authentication(self):
        for headers in ({}, {"Authorization": "Bearer wrong-token"}):
            with self.subTest(headers=headers):
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    self.request("/api/integration/health", headers=headers)
                self.assertEqual(401, raised.exception.code)
                self.assertEqual({"error": "invalid_auth"}, json.load(raised.exception))

        status, body = self.request(
            "/api/integration/health",
            headers={"Authorization": "Bearer test-integration-token"},
        )

        self.assertEqual(200, status)
        self.assertEqual("ok", body["status"])
        self.assertEqual("1", body["api_version"])
        self.assertIn("play", body["capabilities"])

    def test_integration_can_play_and_read_status_and_history(self):
        headers = {"Authorization": "Bearer test-integration-token"}

        status, played = self.request(
            "/api/integration/play",
            method="POST",
            payload={"target": "https://youtu.be/dQw4w9WgXcQ"},
            headers=headers,
        )

        self.assertEqual(200, status)
        self.assertTrue(played["success"])
        self.assertEqual("dQw4w9WgXcQ", played["item"]["id"])

        _, player = self.request("/api/player")
        self.assertEqual("playing", player["state"])
        self.assertEqual("dQw4w9WgXcQ", player["item"]["id"])

        _, integration_status = self.request("/api/integration/status", headers=headers)
        self.assertEqual("playing", integration_status["state"])
        self.assertEqual(1, integration_status["history_count"])

        _, history = self.request("/api/integration/history", headers=headers)
        self.assertEqual(1, history["total"])
        self.assertEqual("dQw4w9WgXcQ", history["items"][0]["id"])

        _, stopped = self.request(
            "/api/integration/stop", method="POST", headers=headers
        )
        self.assertTrue(stopped["success"])
        _, player = self.request("/api/player")
        self.assertEqual({"state": "idle", "item": None}, player)

    def test_integration_status_is_derived_from_one_session_snapshot(self):
        headers = {"Authorization": "Bearer test-integration-token"}

        with patch.object(
            self.server,
            "get_player",
            side_effect=AssertionError("status requested a second snapshot"),
        ):
            status, body = self.request(
                "/api/integration/status", headers=headers
            )

        self.assertEqual(200, status)
        self.assertEqual(body["session"]["state"], body["state"])
        self.assertEqual(body["session"]["item"], body["item"])

    def test_conditional_stop_does_not_stop_a_newer_session(self):
        headers = {"Authorization": "Bearer test-integration-token"}
        _, first = self.request(
            "/api/integration/play",
            method="POST",
            payload={"target": "dQw4w9WgXcQ"},
            headers=headers,
        )
        _, second = self.request(
            "/api/integration/play",
            method="POST",
            payload={"target": "M7lc1UVf-VE"},
            headers=headers,
        )

        _, stale_stop = self.request(
            "/api/integration/stop",
            method="POST",
            payload={"expected_revision": first["session_revision"]},
            headers=headers,
        )
        self.assertFalse(stale_stop["stopped"])
        self.assertEqual("M7lc1UVf-VE", stale_stop["session"]["item"]["id"])

        _, current_stop = self.request(
            "/api/integration/stop",
            method="POST",
            payload={"expected_revision": second["session_revision"]},
            headers=headers,
        )
        self.assertTrue(current_stop["stopped"])
        self.assertEqual("idle", current_stop["session"]["state"])

    @patch("server.search_youtube")
    def test_integration_can_search_music_metadata(self, search_youtube):
        search_youtube.return_value = [
            {
                "kind": "video",
                "id": "dQw4w9WgXcQ",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "channel": "Rick Astley",
                "duration": 213,
                "thumbnail": "https://img.example/cover.jpg",
            }
        ]

        status, body = self.request(
            "/api/integration/search?q=Rick+Astley&limit=5",
            headers={"Authorization": "Bearer test-integration-token"},
        )

        self.assertEqual(200, status)
        self.assertTrue(body["success"])
        self.assertEqual(1, body["total"])
        self.assertEqual("dQw4w9WgXcQ", body["items"][0]["id"])
        search_youtube.assert_called_once_with("Rick Astley", limit=5)

    @patch("server.search_youtube")
    def test_integration_search_accepts_a_pasted_youtube_link(self, search_youtube):
        search_youtube.return_value = []
        link = "https://www.youtube.com/watch?app=desktop&v=llPioQNSBLY&list=RDllPioQNSBLY&start_radio=1&pp=ygUadHLDs3QgdGluIHbDoG8gbOG7nWkgaOG7qWGgBwE%3D&ra=m"
        status, _ = self.request(
            "/api/integration/search?" + urllib.parse.urlencode({"q": link}),
            headers={"Authorization": "Bearer test-integration-token"},
        )
        self.assertEqual(200, status)
        search_youtube.assert_called_once_with(link, limit=20)

        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request(
                "/api/integration/search?" + urllib.parse.urlencode({"q": "x" * 2049}),
                headers={"Authorization": "Bearer test-integration-token"},
            )
        self.assertEqual(400, raised.exception.code)
        self.assertEqual({"error": "invalid_search_query"}, json.load(raised.exception))

    @patch("server.search_youtube")
    def test_playing_a_search_result_preserves_metadata_and_queue(
        self, search_youtube
    ):
        search_youtube.return_value = [
            {
                "source": "youtube",
                "kind": "video",
                "id": "dQw4w9WgXcQ",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "channel": "Rick Astley",
                "album": "Whenever You Need Somebody",
                "duration": 213,
                "thumbnail": "https://img.example/cover.jpg",
            },
            {
                "source": "youtube",
                "kind": "video",
                "id": "M7lc1UVf-VE",
                "url": "https://www.youtube.com/watch?v=M7lc1UVf-VE",
                "title": "YouTube Developers Live",
                "channel": "YouTube Developers",
                "duration": 160,
                "thumbnail": "https://img.example/next.jpg",
            },
        ]
        headers = {"Authorization": "Bearer test-integration-token"}
        self.request(
            "/api/integration/search?q=Rick+Astley&limit=5",
            headers=headers,
        )

        self.request(
            "/api/integration/play",
            method="POST",
            payload={"target": "https://youtu.be/dQw4w9WgXcQ"},
            headers=headers,
        )
        _, status = self.request("/api/integration/status", headers=headers)

        self.assertEqual("playing", status["session"]["state"])
        self.assertEqual("youtube", status["session"]["item"]["source"])
        self.assertEqual(
            "Never Gonna Give You Up", status["session"]["item"]["title"]
        )
        self.assertEqual("Rick Astley", status["session"]["item"]["artist"])
        self.assertEqual(213, status["session"]["duration"])
        self.assertEqual(0, status["session"]["position"])
        self.assertEqual(0, status["session"]["queue"]["index"])
        self.assertEqual(2, len(status["session"]["queue"]["items"]))
        self.assertIn("stop", status["session"]["supported_actions"])
        self.assertRegex(
            status["session"]["updated_at"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        )

    @patch("server.search_zing")
    def test_integration_can_select_the_zing_search_provider(self, search_zing):
        search_zing.return_value = [
            {
                "source": "zing",
                "kind": "song",
                "id": "ZZ90FD0B",
                "url": "https://zingmp3.vn/bai-hat/Thuc-Giac/ZZ90FD0B.html",
                "title": "Thức Giấc",
                "channel": "Da LAB",
                "duration": 269,
                "thumbnail": "https://photo-resize-zmp3.zmdcdn.me/cover.jpg",
            }
        ]

        status, body = self.request(
            "/api/integration/search?source=zing&q=Da+LAB&limit=5",
            headers={"Authorization": "Bearer test-integration-token"},
        )

        self.assertEqual(200, status)
        self.assertEqual("zing", body["source"])
        self.assertEqual("ZZ90FD0B", body["items"][0]["id"])
        search_zing.assert_called_once_with("Da LAB", limit=5)

    @patch("server.search_zing")
    def test_integration_records_zing_outputs_in_shared_session(
        self, search_zing
    ):
        target = "https://zingmp3.vn/bai-hat/Thuc-Giac/ZZ90FD0B.html"
        search_zing.return_value = [
            {
                "source": "zing",
                "kind": "song",
                "id": "ZZ90FD0B",
                "url": target,
                "title": "Thức Giấc",
                "channel": "Da LAB",
                "duration": 269,
                "thumbnail": "https://photo-resize-zmp3.zmdcdn.me/cover.jpg",
            }
        ]
        headers = {"Authorization": "Bearer test-integration-token"}
        self.request(
            "/api/integration/search?source=zing&q=Da+LAB&limit=5",
            headers=headers,
        )

        status, body = self.request(
            "/api/integration/session",
            method="POST",
            payload={
                "source": "zing",
                "target": target,
                "output_entity_ids": [
                    "media_player.phong_khach",
                    "media_player.nha_bep",
                ],
                "volume_level": 0.42,
            },
            headers=headers,
        )

        self.assertEqual(200, status)
        self.assertEqual("Thức Giấc", body["session"]["item"]["title"])
        self.assertEqual(
            ["media_player.phong_khach", "media_player.nha_bep"],
            body["session"]["output_entity_ids"],
        )
        self.assertEqual(0.42, body["session"]["volume_level"])

    @patch("server.search_youtube")
    def test_sessions_per_speaker_group(self, search_youtube):
        headers = {"Authorization": "Bearer test-integration-token"}

        def results(*ids):
            return [
                {"source": "youtube", "kind": "video", "id": video_id,
                 "url": f"https://www.youtube.com/watch?v={video_id}",
                 "title": f"Bai {video_id}", "channel": "Kenh", "duration": 200,
                 "thumbnail": "https://img.example/a.jpg"}
                for video_id in ids
            ]

        def record(target, outputs, **extra):
            status, body = self.request(
                "/api/integration/session", method="POST",
                payload={"source": "youtube", "target": target, "output_entity_ids": outputs, **extra},
                headers=headers,
            )
            self.assertEqual(200, status, body)
            return body["session"]

        def sessions():
            _, body = self.request("/api/integration/status", headers=headers)
            return body

        search_youtube.return_value = results("dQw4w9WgXcQ", "M7lc1UVf-VE", "llPioQNSBLY")
        self.request("/api/integration/search?q=a", headers=headers)

        # Every speaker its own song.
        living = record("dQw4w9WgXcQ", ["media_player.phong_khach"], controller="ha:abc")
        kitchen = record("M7lc1UVf-VE", ["media_player.bep"])
        body = sessions()
        self.assertEqual(2, len(body["sessions"]))
        self.assertEqual(kitchen["session_id"], body["session"]["session_id"])  # v1: latest
        self.assertNotEqual(living["session_id"], kitchen["session_id"])
        self.assertEqual("ha:abc", living["controller"])
        self.assertTrue(living["auto_advance"])

        # Same speakers again reuse their session; next track keeps its own queue
        # even after a different search.
        search_youtube.return_value = results("fyzu_MvTZvg")
        self.request("/api/integration/search?q=b", headers=headers)
        again = record("llPioQNSBLY", ["media_player.phong_khach"], session_id=living["session_id"])
        self.assertEqual(living["session_id"], again["session_id"])
        self.assertEqual((2, 3), (again["queue"]["index"], len(again["queue"]["items"])))
        self.assertEqual("Bai llPioQNSBLY", again["item"]["title"])

        # Several speakers, one song: both leave their old sessions.
        together = record("fyzu_MvTZvg", ["media_player.phong_khach", "media_player.bep"])
        body = sessions()
        self.assertEqual([together["session_id"]], [s["session_id"] for s in body["sessions"]])

        # Taking one speaker out keeps the other on the shared song.
        alone = record("fyzu_MvTZvg", ["media_player.bep"])
        by_id = {s["session_id"]: s for s in sessions()["sessions"]}
        self.assertEqual(["media_player.phong_khach"], by_id[together["session_id"]]["output_entity_ids"])
        self.assertEqual(["media_player.bep"], by_id[alone["session_id"]]["output_entity_ids"])

        # Untick a speaker: the song keeps playing on the rest, no restart.
        _, moved = self.request(
            "/api/integration/session/outputs", method="POST",
            payload={"session_id": together["session_id"], "output_entity_ids": ["media_player.phong_khach", "media_player.bep"]},
            headers=headers,
        )
        self.assertEqual(["media_player.phong_khach", "media_player.bep"], moved["session"]["output_entity_ids"])
        self.assertEqual("Bai fyzu_MvTZvg", moved["session"]["item"]["title"])
        self.assertEqual([together["session_id"]], [s["session_id"] for s in sessions()["sessions"]])
        _, emptied = self.request(
            "/api/integration/session/outputs", method="POST",
            payload={"session_id": together["session_id"], "output_entity_ids": []},
            headers=headers,
        )
        self.assertTrue(emptied["stopped"])
        self.assertEqual([], sessions()["sessions"])
        alone = record("fyzu_MvTZvg", ["media_player.bep"])

        # Stop one session only.
        record("dQw4w9WgXcQ", ["media_player.phong_khach"])
        _, stopped = self.request(
            "/api/integration/stop", method="POST",
            payload={"session_id": alone["session_id"]}, headers=headers,
        )
        self.assertTrue(stopped["stopped"])
        self.assertEqual([["media_player.phong_khach"]], [s["output_entity_ids"] for s in sessions()["sessions"]])

        with self.assertRaises(urllib.error.HTTPError) as raised:
            record("dQw4w9WgXcQ", ["media_player.bep"], session_id="Bad Id!")
        self.assertEqual(400, raised.exception.code)
        self.assertEqual({"error": "invalid_session_id"}, json.load(raised.exception))

    def test_integration_records_valid_direct_http_audio_session(self):
        headers = {"Authorization": "Bearer test-integration-token"}

        status, body = self.request(
            "/api/integration/session",
            method="POST",
            payload={
                "source": "http",
                "target": "https://audio.example/album/My%20Song.flac",
                "media_content_type": "audio/flac",
                "output_entity_ids": ["media_player.esp32"],
            },
            headers=headers,
        )

        self.assertEqual(200, status)
        self.assertEqual("My Song.flac", body["session"]["item"]["title"])
        self.assertEqual(
            "audio/flac", body["session"]["item"]["media_content_type"]
        )

    def test_integration_rejects_a_web_page_as_direct_http_audio(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request(
                "/api/integration/session",
                method="POST",
                payload={
                    "source": "http",
                    "target": "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
                    "output_entity_ids": ["media_player.speaker"],
                },
                headers={"Authorization": "Bearer test-integration-token"},
            )

        self.assertEqual(400, raised.exception.code)
        self.assertEqual(
            {"error": "invalid_http_audio_target"},
            json.load(raised.exception),
        )

    def test_integration_rejects_unknown_search_provider(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request(
                "/api/integration/search?source=unknown&q=music",
                headers={"Authorization": "Bearer test-integration-token"},
            )

        self.assertEqual(400, raised.exception.code)
        self.assertEqual(
            {"error": "invalid_search_source"}, json.load(raised.exception)
        )

    @patch("server.resolve_zing_stream")
    def test_integration_creates_a_short_lived_zing_stream_url(self, resolve):
        target = "https://zingmp3.vn/bai-hat/Thuc-Giac-Da-LAB/ZZ90FD0B.html"
        self.remember_public_zing_target(target)
        resolve.return_value = {
            "url": "https://audio.zmdcdn.me/song.mp3",
            "headers": {},
            "content_type": "audio/mpeg",
        }
        status, body = self.request(
            "/api/integration/stream",
            method="POST",
            payload={
                "source": "zing",
                "target": target,
            },
            headers={"Authorization": "Bearer test-integration-token"},
        )

        self.assertEqual(200, status)
        self.assertEqual("zing", body["source"])
        self.assertEqual("audio/mpeg", body["media_content_type"])
        self.assertTrue(
            body["stream_url"].startswith(
                "http://172.16.10.200:8099/api/stream/"
            )
        )
        resolve.assert_called_once()

    @patch("server.resolve_zing_stream")
    def test_stream_api_rejects_a_zing_url_not_returned_by_search(self, resolve):
        resolve.return_value = {
            "url": "https://audio.zmdcdn.me/song.mp3",
            "headers": {},
            "content_type": "audio/mpeg",
        }

        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request(
                "/api/integration/stream",
                method="POST",
                payload={
                    "source": "zing",
                    "target": (
                        "https://zingmp3.vn/bai-hat/Unverified/ZZ90FD0B.html"
                    ),
                },
                headers={"Authorization": "Bearer test-integration-token"},
            )

        self.assertEqual(403, raised.exception.code)
        self.assertEqual(
            {"error": "unverified_zing_target"}, json.load(raised.exception)
        )
        resolve.assert_not_called()

    @patch("server.urlopen")
    @patch("server.resolve_zing_stream")
    def test_signed_stream_relays_audio_and_range_requests(
        self, resolve, open_upstream
    ):
        target = "https://zingmp3.vn/bai-hat/Thuc-Giac/ZZ90FD0B.html"
        self.remember_public_zing_target(target)
        resolve.return_value = {
            "url": "https://audio.zmdcdn.me/song.mp3",
            "headers": {"Referer": "https://zingmp3.vn/"},
            "content_type": "audio/mpeg",
        }
        upstream = io.BytesIO(b"MP3!")
        upstream.headers = {
            "Content-Type": "audio/mpeg",
            "Content-Length": "4",
            "Content-Range": "bytes 0-3/4",
            "Accept-Ranges": "bytes",
        }
        upstream.getcode = lambda: 206
        open_upstream.return_value = upstream
        _, created = self.request(
            "/api/integration/stream",
            method="POST",
            payload={
                "source": "zing",
                "target": target,
            },
            headers={"Authorization": "Bearer test-integration-token"},
        )
        token = created["stream_url"].rsplit("/", 1)[-1]
        request = urllib.request.Request(
            f"{self.base_url}/api/stream/{token}",
            headers={"Range": "bytes=0-3"},
        )

        with urllib.request.urlopen(request, timeout=2) as response:
            self.assertEqual(206, response.status)
            self.assertEqual("audio/mpeg", response.headers["Content-Type"])
            self.assertEqual(b"MP3!", response.read())

        upstream_request = open_upstream.call_args.args[0]
        self.assertEqual("bytes=0-3", upstream_request.get_header("Range"))

    @patch("server.resolve_zing_stream")
    def test_stream_creation_reports_an_unplayable_zing_result(self, resolve):
        target = "https://zingmp3.vn/bai-hat/Thuc-Giac/ZZ90FD0B.html"
        self.remember_public_zing_target(target)
        resolve.side_effect = StreamUnavailableError("stream_provider_failed")
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request(
                "/api/integration/stream",
                method="POST",
                payload={
                    "source": "zing",
                    "target": target,
                },
                headers={"Authorization": "Bearer test-integration-token"},
            )

        self.assertEqual(502, raised.exception.code)
        self.assertEqual({"error": "stream_unavailable"}, json.load(raised.exception))

    def test_public_stream_rejects_an_invalid_signature(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/api/stream/not-a-valid-token")

        self.assertEqual(403, raised.exception.code)
        self.assertEqual({"error": "invalid_stream_token"}, json.load(raised.exception))

    @patch("server.resolve_youtube_audio")
    def test_integration_creates_a_youtube_audio_stream_url(self, resolve):
        resolve.return_value = {
            "url": "https://rr3---sn-abc.googlevideo.com/videoplayback?x=1",
            "headers": {"User-Agent": "TriTue"},
            "content_type": "audio/mp4",
        }
        status, body = self.request(
            "/api/integration/stream",
            method="POST",
            payload={
                "source": "youtube",
                "target": "https://youtu.be/dQw4w9WgXcQ",
            },
            headers={"Authorization": "Bearer test-integration-token"},
        )

        self.assertEqual(200, status)
        self.assertEqual("youtube", body["source"])
        self.assertEqual("audio/mp4", body["media_content_type"])
        self.assertTrue(
            body["stream_url"].startswith("http://172.16.10.200:8099/api/stream/")
        )
        resolve.assert_called_once_with("dQw4w9WgXcQ")

    def test_youtube_audio_stream_rejects_a_playlist(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request(
                "/api/integration/stream",
                method="POST",
                payload={
                    "source": "youtube",
                    "target": "https://www.youtube.com/playlist?list=PL1234567890",
                },
                headers={"Authorization": "Bearer test-integration-token"},
            )

        self.assertEqual(400, raised.exception.code)
        self.assertEqual(
            {"error": "youtube_audio_requires_video"}, json.load(raised.exception)
        )

    def test_stream_api_rejects_an_unknown_source(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request(
                "/api/integration/stream",
                method="POST",
                payload={"source": "spotify", "target": "anything"},
                headers={"Authorization": "Bearer test-integration-token"},
            )

        self.assertEqual(400, raised.exception.code)
        self.assertEqual(
            {"error": "unsupported_stream_source"}, json.load(raised.exception)
        )

    @patch("server.urlopen")
    @patch("server.resolve_youtube_audio")
    def test_signed_youtube_stream_relays_googlevideo_audio(
        self, resolve, open_upstream
    ):
        resolve.return_value = {
            "url": "https://rr3---sn-abc.googlevideo.com/videoplayback",
            "headers": {"User-Agent": "TriTue"},
            "content_type": "audio/mp4",
        }
        upstream = io.BytesIO(b"M4A!")
        upstream.headers = {"Content-Type": "audio/mp4", "Content-Length": "4"}
        upstream.getcode = lambda: 200
        open_upstream.return_value = upstream
        _, created = self.request(
            "/api/integration/stream",
            method="POST",
            payload={"source": "youtube", "target": "dQw4w9WgXcQ"},
            headers={"Authorization": "Bearer test-integration-token"},
        )
        token = created["stream_url"].rsplit("/", 1)[-1]

        with urllib.request.urlopen(
            f"{self.base_url}/api/stream/{token}", timeout=2
        ) as response:
            self.assertEqual(200, response.status)
            self.assertEqual("audio/mp4", response.headers["Content-Type"])
            self.assertEqual(b"M4A!", response.read())

        # The prepared stream is cached, so the proxy reuses it instead of
        # asking yt-dlp to resolve the short-lived googlevideo URL twice.
        resolve.assert_called_once_with("dQw4w9WgXcQ")

    @patch("server.urlopen")
    @patch("server.resolve_youtube_audio")
    def test_stream_proxy_answers_head_for_dlna_renderers(
        self, resolve, open_upstream
    ):
        resolve.return_value = {
            "url": "https://rr3---sn-abc.googlevideo.com/videoplayback",
            "headers": {"User-Agent": "TriTue"},
            "content_type": "audio/mp4",
        }
        upstream = io.BytesIO(b"")
        upstream.headers = {
            "Content-Type": "audio/mp4",
            "Content-Range": "bytes 0-0/3449447",
        }
        open_upstream.return_value = upstream
        _, created = self.request(
            "/api/integration/stream",
            method="POST",
            payload={"source": "youtube", "target": "dQw4w9WgXcQ"},
            headers={"Authorization": "Bearer test-integration-token"},
        )
        token = created["stream_url"].rsplit("/", 1)[-1]

        request = urllib.request.Request(
            f"{self.base_url}/api/stream/{token}", method="HEAD"
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            self.assertEqual(200, response.status)
            self.assertEqual("audio/mp4", response.headers["Content-Type"])
            self.assertEqual("bytes", response.headers["Accept-Ranges"])
            self.assertEqual("3449447", response.headers["Content-Length"])
        # HEAD probes upstream with a zero-length range, never the whole body.
        self.assertEqual(
            "bytes=0-0", open_upstream.call_args.args[0].get_header("Range")
        )

    @patch("server.urlopen")
    @patch("server.resolve_youtube_audio")
    def test_stream_refused_by_youtube_is_resolved_again_once(self, resolve, open_upstream):
        resolve.side_effect = [
            {"url": "https://rr3---sn-old.googlevideo.com/videoplayback", "headers": {}, "content_type": "audio/mp4"},
            {"url": "https://rr3---sn-new.googlevideo.com/videoplayback", "headers": {}, "content_type": "audio/mp4"},
        ]
        upstream = io.BytesIO(b"M4A!")
        upstream.headers = {"Content-Type": "audio/mp4", "Content-Length": "4"}
        upstream.getcode = lambda: 200

        def open_url(request, timeout):
            if "sn-old" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)
            return upstream

        open_upstream.side_effect = open_url
        _, created = self.request(
            "/api/integration/stream",
            method="POST",
            payload={"source": "youtube", "target": "dQw4w9WgXcQ"},
            headers={"Authorization": "Bearer test-integration-token"},
        )
        token = created["stream_url"].rsplit("/", 1)[-1]
        with urllib.request.urlopen(f"{self.base_url}/api/stream/{token}", timeout=2) as response:
            self.assertEqual(b"M4A!", response.read())
        self.assertEqual(2, resolve.call_count)

    @patch("server.search_youtube")
    @patch("server.resolve_youtube_audio")
    def test_speaker_session_prefetches_the_next_song(self, resolve, search):
        search.return_value = [
            {"source": "youtube", "kind": "video", "id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}",
             "title": video_id, "channel": "", "duration": 200}
            for video_id in ("dQw4w9WgXcQ", "M7lc1UVf-VE", "llPioQNSBLY")
        ]
        resolve.return_value = {"url": "https://rr3---sn-abc.googlevideo.com/videoplayback", "headers": {}, "content_type": "audio/mp4"}
        self.server.search("youtube", "x", 3)
        self.server.prefetch_streams = True
        self.server.record_session(
            "youtube", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", output_entity_ids=["media_player.bep"]
        )
        for _ in range(50):
            if resolve.call_count:
                break
            time.sleep(0.02)
        resolve.assert_called_once_with("M7lc1UVf-VE")
        # A session without speakers (the web page) does not prefetch.
        resolve.reset_mock()
        self.server.record_session("youtube", "https://www.youtube.com/watch?v=M7lc1UVf-VE", output_entity_ids=[])
        time.sleep(0.2)
        resolve.assert_not_called()

    def test_video_url_is_normalized_and_persisted(self):
        status, target = self.request(
            "/api/history",
            method="POST",
            payload={"target": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )

        self.assertEqual(201, status)
        self.assertEqual("video", target["kind"])
        self.assertEqual("dQw4w9WgXcQ", target["id"])
        self.assertEqual(
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1",
            target["embed_url"],
        )

        _, history = self.request("/api/history")
        self.assertEqual([target], history["items"])

        persisted = json.loads(
            (Path(self.temp_dir.name) / "history.json").read_text(encoding="utf-8")
        )
        self.assertEqual([target], persisted)

    def test_playlist_and_short_urls_are_supported_and_history_is_bounded(self):
        _, playlist = self.request(
            "/api/history",
            method="POST",
            payload={"target": "https://youtube.com/playlist?list=PL1234567890abc"},
        )
        self.assertEqual("playlist", playlist["kind"])
        self.assertEqual(
            "https://www.youtube-nocookie.com/embed/videoseries?list=PL1234567890abc&autoplay=1",
            playlist["embed_url"],
        )

        self.request(
            "/api/history",
            method="POST",
            payload={"target": "https://youtube.com/shorts/aqz-KE-bpKQ"},
        )
        _, newest = self.request(
            "/api/history", method="POST", payload={"target": "M7lc1UVf-VE"}
        )

        _, history = self.request("/api/history")
        self.assertEqual(2, len(history["items"]))
        self.assertEqual(newest, history["items"][0])
        self.assertEqual("aqz-KE-bpKQ", history["items"][1]["id"])

    def test_watch_url_preserves_playlist_context_for_cast(self):
        _, target = self.request(
            "/api/history",
            method="POST",
            payload={
                "target": (
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234567890abc"
                )
            },
        )

        self.assertEqual("video", target["kind"])
        self.assertEqual("dQw4w9WgXcQ", target["id"])
        self.assertEqual("PL1234567890abc", target["playlist_id"])
        self.assertEqual(
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
            "?list=PL1234567890abc&autoplay=1",
            target["embed_url"],
        )

    def test_invalid_payload_has_a_stable_error_contract(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request("/api/history", method="POST", payload=[])

        self.assertEqual(400, raised.exception.code)
        self.assertEqual({"error": "invalid_request"}, json.load(raised.exception))
        _, history = self.request("/api/history")
        self.assertEqual([], history["items"])

    def test_history_can_be_cleared(self):
        self.request("/api/history", method="POST", payload={"target": "dQw4w9WgXcQ"})

        status, body = self.request("/api/history", method="DELETE")

        self.assertEqual(200, status)
        self.assertEqual({"items": []}, body)
        _, history = self.request("/api/history")
        self.assertEqual([], history["items"])

    def test_history_accepts_a_chunked_request_body(self):
        # Home Assistant Ingress re-streams POST bodies with
        # Transfer-Encoding: chunked and no Content-Length.
        import socket

        body = b'{"target": "dQw4w9WgXcQ"}'
        chunked = f"{len(body):x}\r\n".encode() + body + b"\r\n0\r\n\r\n"
        request = (
            b"POST /api/history HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Type: application/json\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Connection: close\r\n\r\n" + chunked
        )
        with socket.create_connection(
            ("127.0.0.1", self.server.server_port), timeout=3
        ) as sock:
            sock.sendall(request)
            response = b""
            while True:
                part = sock.recv(4096)
                if not part:
                    break
                response += part

        self.assertIn(b"201", response.split(b"\r\n", 1)[0])
        self.assertIn(b'"id": "dQw4w9WgXcQ"', response)

    def test_web_ui_and_runtime_config_are_served(self):
        with urllib.request.urlopen(f"{self.base_url}/", timeout=2) as response:
            page = response.read().decode("utf-8")
            self.assertEqual(200, response.status)
            self.assertEqual(
                "text/html; charset=utf-8", response.headers["Content-Type"]
            )

        self.assertIn("TriTue YouTube Player", page)
        self.assertIn('aria-label="Trình phát YouTube"', page)
        # Home Assistant Ingress pages carry "Referrer-Policy: no-referrer"; a
        # YouTube embed without a Referer fails with Error 153, so the iframe sets
        # its own policy.
        self.assertIn('referrerpolicy="strict-origin-when-cross-origin"', page)

        with urllib.request.urlopen(f"{self.base_url}/app.js", timeout=2) as response:
            script = response.read().decode("utf-8")
        self.assertIn('api("api/history")', script)
        self.assertIn('api("api/player")', script)

        with urllib.request.urlopen(
            f"{self.base_url}/favicon.svg", timeout=2
        ) as response:
            self.assertEqual("image/svg+xml", response.headers["Content-Type"])

        _, config = self.request("/api/config")
        self.assertEqual(
            {
                "app_title": "Test Player",
                "max_history": 2,
                "sources": ["youtube", "zing", "facebook"],
            },
            config,
        )

    def test_process_reads_home_assistant_options(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]

        options_path = Path(self.temp_dir.name) / "options.json"
        options_path.write_text(
            json.dumps({"app_title": "Configured Player", "max_history": 3}),
            encoding="utf-8",
        )
        environment = {
            **os.environ,
            "HOST": "127.0.0.1",
            "PORT": str(port),
            "DATA_DIR": self.temp_dir.name,
        }
        process = subprocess.Popen(
            [sys.executable, str(APP_DIR / "server.py")],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/config", timeout=0.2
                    ) as response:
                        config = json.load(response)
                    break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(0.05)
            else:
                output = process.stdout.read() if process.stdout else ""
                self.fail(f"server did not start: {output}")

            self.assertEqual(
                {
                    "app_title": "Configured Player",
                    "max_history": 3,
                    "sources": ["youtube", "zing", "facebook"],
                },
                config,
            )
        finally:
            process.terminate()
            process.wait(timeout=2)
            if process.stdout:
                process.stdout.close()


if __name__ == "__main__":
    unittest.main()
