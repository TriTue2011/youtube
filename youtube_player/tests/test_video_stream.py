"""Picture-only stream for a browser when YouTube refuses to embed a video.

Owner 14/09/2026: a record-label video showed "Video này không hoạt động" in the card
when Home Assistant was opened by IP address, "trên youtube vẫn xem được"; chose "only
when YouTube refuses", quality "by screen, up to 1080p", a browser at home fetching
straight from YouTube and asking before using the home's upload when away.
"""
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

import streaming  # noqa: E402
from server import create_server  # noqa: E402

GV = "https://rr1---sn-abc.googlevideo.com/videoplayback?itag={}"


def fmt(itag, ext, vcodec, height, tbr, protocol="https", acodec="none"):
    return {"format_id": str(itag), "url": GV.format(itag), "ext": ext, "vcodec": vcodec, "acodec": acodec,
            "height": height, "tbr": tbr, "protocol": protocol}


# The shape yt-dlp returned for Xruhj0zOI7A (shortened).
FORMATS = {"formats": [
    fmt(140, "m4a", "none", None, 130, acodec="mp4a.40.2"),
    fmt(231, "mp4", "avc1.4D401E", 480, 556, protocol="m3u8_native"),
    fmt(135, "mp4", "avc1.4d401e", 480, 343),
    fmt(136, "mp4", "avc1.4d401f", 720, 1002),
    fmt(247, "webm", "vp9", 720, 1092),
    fmt(137, "mp4", "avc1.640028", 1080, 2806),
    fmt(399, "mp4", "av01.0.08M.08", 1080, 1308),
]}


class PictureFormatTests(unittest.TestCase):
    def resolve(self, target, info=FORMATS):
        return streaming.resolve_youtube_video(target, extractor=lambda url, timeout: info)

    def test_highest_not_above_the_screen_prefers_avc1_and_skips_m3u8(self):
        best = self.resolve("Xruhj0zOI7A:1080")
        self.assertEqual((GV.format(137), "video/mp4", 1080, 2806), (best["url"], best["content_type"], best["height"], best["bitrate_kbps"]))
        self.assertEqual(GV.format(136), self.resolve("Xruhj0zOI7A:720")["url"])
        only_480 = {"formats": [f for f in FORMATS["formats"] if (f["height"] or 0) <= 480]}
        self.assertEqual(GV.format(135), self.resolve("A_HekkBbd1M:1080", only_480)["url"])
        with self.assertRaises(streaming.StreamUnavailableError):
            self.resolve("A_HekkBbd1M:1080", {"formats": [FORMATS["formats"][0]]})

    def test_targets_snap_to_standard_heights_and_sign(self):
        self.assertEqual("Xruhj0zOI7A:720", streaming.youtube_video_target("Xruhj0zOI7A", 900))
        self.assertEqual("Xruhj0zOI7A:360", streaming.youtube_video_target("Xruhj0zOI7A", 10))
        token = streaming.create_stream_token("Xruhj0zOI7A:1080", "secret", source="youtube_video", now=1000)
        self.assertEqual(("youtube_video", "Xruhj0zOI7A:1080"), streaming.verify_stream_token(token, "secret", now=1001))
        with self.assertRaises(ValueError):
            streaming.create_stream_token("Xruhj0zOI7A:999", "secret", source="youtube_video")


class PictureStreamHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.server = create_server(
            host="127.0.0.1", port=0, data_dir=Path(self.temp_dir.name), app_title="Test", max_history=5,
            integration_token="test-integration-token", public_base_url="http://172.16.10.200:8099",
        )
        self.server.prefetch_streams = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    @patch("server.resolve_youtube_video")
    def test_integration_stream_returns_the_direct_and_the_signed_picture_url(self, resolve):
        resolve.return_value = {"url": GV.format(136), "headers": {}, "content_type": "video/mp4", "height": 720, "bitrate_kbps": 1002}
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.server.server_port}/api/integration/stream",
            data=json.dumps({"source": "youtube_video", "target": "https://youtu.be/Xruhj0zOI7A", "max_height": 1000}).encode(),
            headers={"Authorization": "Bearer test-integration-token", "Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.load(response)
        resolve.assert_called_once_with("Xruhj0zOI7A:720")
        self.assertEqual(("video/mp4", 720, 1002, GV.format(136)),
                         (body["media_content_type"], body["height"], body["bitrate_kbps"], body["direct_url"]))
        token = body["stream_url"].rsplit("/", 1)[-1]
        self.assertTrue(body["stream_url"].startswith("http://172.16.10.200:8099/api/stream/"))
        self.assertEqual(("youtube_video", "Xruhj0zOI7A:720"), streaming.verify_stream_token(token, "test-integration-token"))


if __name__ == "__main__":
    unittest.main()
