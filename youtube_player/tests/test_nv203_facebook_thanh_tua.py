"""NV203 — bài Facebook cũng phải có thanh tua (như YouTube/Zing).

ĐO (đỏ trước khi sửa). Bốn phát hiện:

- F1: POST /api/integration/stream với source=facebook / facebook_video bị từ
  chối 400 unsupported_stream_source — dù prepare_stream/_resolve_stream,
  actions.py (đường loa) và http.py (đường thẻ) đều đã sẵn đường Facebook.
  Hậu quả: phát Facebook ra loa bằng action HỎNG HẲN, và thẻ không lấy được
  hình facebook_video.
- F2: resolve_facebook_audio / resolve_facebook_video không giữ `duration` từ
  dữ liệu yt-dlp (dù info có) — bản ghi luồng không mang thời lượng.
- F3: phản hồi /api/integration/stream không có `duration`.
- F4: phiên đang phát Facebook giữ duration=0 dù luồng đã dựng xong và biết
  thời lượng thật — thẻ không có `tong` để vẽ thanh tua / cho tua (kieu loa/uoc).
"""

import importlib.util
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

import server as server_module  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FacebookThanhTuaTests(unittest.TestCase):
    VIDEO_ID = "1807802260572674"

    def setUp(self):
        self.server_module = server_module
        self.temp_dir = tempfile.TemporaryDirectory()
        self.server = server_module.create_server(
            host="127.0.0.1",
            port=0,
            data_dir=Path(self.temp_dir.name),
            app_title="Test Player",
            max_history=2,
            integration_token="nv203-test-token",
            public_base_url="http://172.16.10.200:8099",
        )
        self.server.prefetch_streams = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.headers = {"Authorization": "Bearer nv203-test-token"}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def request(self, path, *, method="GET", payload=None):
        body = None
        request_headers = dict(self.headers)
        if payload is not None:
            body = json.dumps(payload).encode()
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=body, headers=request_headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def _stream_record(self):
        return {
            "url": "https://video-hkg1-2.xx.fbcdn.net/v/tieng.m4a",
            "headers": {},
            "content_type": "audio/mpeg",
            "duration": 187,
        }

    # --- F1: endpoint phải nhận facebook -------------------------------------
    @patch("server.resolve_facebook_audio")
    def test_endpoint_stream_chap_nhan_facebook(self, resolve):
        resolve.return_value = self._stream_record()
        status, body = self.request(
            "/api/integration/stream",
            method="POST",
            payload={"source": "facebook", "target": self.VIDEO_ID},
        )
        self.assertEqual(200, status, body)
        self.assertTrue(body["success"])
        self.assertTrue(body["stream_url"].startswith("http://172.16.10.200:8099/api/stream/"))

    @patch("server.resolve_facebook_video")
    def test_endpoint_stream_chap_nhan_facebook_video(self, resolve):
        resolve.return_value = {
            "url": "https://video-hkg1-2.xx.fbcdn.net/v/hd.mp4",
            "headers": {},
            "content_type": "video/mp4",
            "duration": 187,
        }
        status, body = self.request(
            "/api/integration/stream",
            method="POST",
            payload={"source": "facebook_video", "target": self.VIDEO_ID, "max_height": 720},
        )
        self.assertEqual(200, status, body)
        self.assertTrue(body["success"])

    # --- F2+F3: luồng và phản hồi phải mang duration --------------------------
    @patch("server.resolve_facebook_audio")
    def test_stream_response_co_duration(self, resolve):
        resolve.return_value = self._stream_record()
        status, body = self.request(
            "/api/integration/stream",
            method="POST",
            payload={"source": "facebook", "target": self.VIDEO_ID},
        )
        self.assertEqual(200, status, body)
        self.assertEqual(187, body.get("duration"))

    def test_resolve_facebook_audio_giu_duration(self):
        streaming = _load("streaming_nv203", APP_DIR / "streaming.py")

        def fake_extract(watch_url, timeout):
            return {
                "duration": 187,
                "formats": [
                    {
                        "format_id": "38352274251084823a",
                        "ext": "m4a",
                        "acodec": "mp4a.40.5",
                        "vcodec": "none",
                        "url": "https://video-hkg1-2.xx.fbcdn.net/v/tieng.m4a",
                    }
                ],
            }

        result = streaming.resolve_facebook_audio(self.VIDEO_ID, extractor=fake_extract)
        self.assertEqual(187, result.get("duration"))

    def test_resolve_facebook_video_giu_duration(self):
        streaming = _load("streaming_nv203", APP_DIR / "streaming.py")

        def fake_extract(watch_url, timeout):
            return {
                "duration": 243,
                "formats": [
                    {
                        "format_id": "hd",
                        "ext": "mp4",
                        "url": "https://video-hkg1-2.xx.fbcdn.net/v/hd.mp4",
                    },
                    {
                        "format_id": "sd",
                        "ext": "mp4",
                        "url": "https://video-hkg1-2.xx.fbcdn.net/v/sd.mp4",
                    },
                ],
            }

        result = streaming.resolve_facebook_video(f"{self.VIDEO_ID}:720", extractor=fake_extract)
        self.assertEqual(243, result.get("duration"))

    # --- F4: phiên được ghi duration khi dựng luồng ----------------------------
    @patch("server.resolve_facebook_audio")
    def test_phien_duoc_ghi_duration_khi_dung_luong(self, resolve):
        resolve.return_value = self._stream_record()
        # Bài Facebook trong hàng đợi tìm kiếm nhưng CHƯA biết thời lượng
        # (đúng ca playlist lưu sẵn / action với target trần).
        self.server.playback_session.remember_search(
            "facebook",
            [
                {
                    "source": "facebook",
                    "kind": "video",
                    "id": self.VIDEO_ID,
                    "url": f"https://www.facebook.com/watch/?v={self.VIDEO_ID}",
                    "title": "Reel test",
                    "duration": 0,
                }
            ],
        )
        status, body = self.request(
            "/api/integration/session",
            method="POST",
            payload={
                "source": "facebook",
                "target": self.VIDEO_ID,
                "output_entity_ids": ["media_player.phong_khach"],
            },
        )
        self.assertEqual(200, status, body)
        self.assertEqual(0, body["session"]["duration"])

        status, _ = self.request(
            "/api/integration/stream",
            method="POST",
            payload={"source": "facebook", "target": self.VIDEO_ID},
        )
        self.assertEqual(200, status)

        _, status_body = self.request("/api/integration/status")
        session = status_body["session"]
        self.assertEqual(187, session["duration"])
        self.assertEqual(187, (session["item"] or {}).get("duration"))

    @patch("server.resolve_facebook_audio")
    def test_ghi_lai_cung_bai_giu_duration_da_do(self, resolve):
        """actions.py ghi lại phiên sau khi dựng luồng (đổi media_content_type):
        ghi lại cùng bài không được xoá thời lượng đã đo."""
        resolve.return_value = self._stream_record()
        self.server.playback_session.remember_search(
            "facebook",
            [
                {
                    "source": "facebook",
                    "kind": "video",
                    "id": self.VIDEO_ID,
                    "url": f"https://www.facebook.com/watch/?v={self.VIDEO_ID}",
                    "title": "Reel test",
                    "duration": 0,
                }
            ],
        )
        payload = {
            "source": "facebook",
            "target": self.VIDEO_ID,
            "output_entity_ids": ["media_player.phong_khach"],
        }
        status, _ = self.request("/api/integration/session", method="POST", payload=payload)
        self.assertEqual(200, status)
        status, _ = self.request(
            "/api/integration/stream", method="POST",
            payload={"source": "facebook", "target": self.VIDEO_ID},
        )
        self.assertEqual(200, status)
        # Ghi lại như actions.py làm sau khi dựng luồng (kèm media_content_type).
        status, body = self.request(
            "/api/integration/session", method="POST",
            payload={**payload, "media_content_type": "audio/mpeg"},
        )
        self.assertEqual(200, status, body)
        self.assertEqual(187, body["session"]["duration"])
        self.assertEqual(187, (body["session"]["item"] or {}).get("duration"))

    @patch("server.resolve_facebook_audio")
    def test_khong_ghi_de_duration_da_biet(self, resolve):
        resolve.return_value = self._stream_record()
        self.server.playback_session.remember_search(
            "facebook",
            [
                {
                    "source": "facebook",
                    "kind": "video",
                    "id": self.VIDEO_ID,
                    "url": f"https://www.facebook.com/watch/?v={self.VIDEO_ID}",
                    "title": "Reel test",
                    "duration": 200,
                }
            ],
        )
        status, body = self.request(
            "/api/integration/session",
            method="POST",
            payload={
                "source": "facebook",
                "target": self.VIDEO_ID,
                "output_entity_ids": ["media_player.phong_khach"],
            },
        )
        self.assertEqual(200, status, body)
        self.request(
            "/api/integration/stream",
            method="POST",
            payload={"source": "facebook", "target": self.VIDEO_ID},
        )
        _, status_body = self.request("/api/integration/status")
        # Đã biết 200 thì giữ 200, không ghi đè bằng 187 của luồng.
        self.assertEqual(200, status_body["session"]["duration"])


if __name__ == "__main__":
    unittest.main()
