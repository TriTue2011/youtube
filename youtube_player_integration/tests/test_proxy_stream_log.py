"""Bug tự dừng giữa bài: proxy_stream phải LOG khi chunk relay lỗi sau khi response đã started.

Trước sửa: except (StreamUnavailableError, OSError) im lặng return khi đã bắt đầu
trả response → loa đứt đột ngột, không dấu vết trong log.
Sau sửa: log ERROR ghi rõ token (rút gọn), số chunk, loại lỗi.
"""
import importlib.util
import io
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "youtube_player" / "app"


def load_server_module():
    sys.path.insert(0, str(APP_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "tritue_player_server", APP_DIR / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["tritue_player_server"] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(APP_DIR))


class ProxyStreamLogTests(unittest.TestCase):
    def setUp(self):
        self.server_mod = load_server_module()
        self.logs = []

    def make_handler(self, open_upstream):
        handler = self.server_mod.PlayerHandler.__new__(self.server_mod.PlayerHandler)
        handler.headers = {"Range": "bytes=0-"}
        handler.server = types.SimpleNamespace(integration_token="tok")
        handler.open_upstream = open_upstream
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.send_json = MagicMock()
        handler.wfile = io.BytesIO()
        logs = self.logs
        handler.log_message = lambda message, *args: logs.append(message % args)
        return handler

    def fake_response(self):
        response = MagicMock()
        response.headers = {"Content-Type": "audio/mpeg"}
        response.read = MagicMock(side_effect=[b"x" * 100, b""])
        return response

    def test_chunk_loi_sau_khi_started_phai_log(self):
        open_upstream = MagicMock(
            side_effect=[(self.fake_response(), {})] + [OSError("google throttle")] * 10
        )
        handler = self.make_handler(open_upstream)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch.object(
            self.server_mod, "stream_total_size", return_value=10 * 1024 * 1024
        ), patch("time.sleep"):
            handler.proxy_stream("deadbeefcafef00d")
        self.assertGreater(len(self.logs), 0, f"phải log khi chunk lỗi sau khi started, thực tế: {self.logs}")
        for dong in self.logs:
            self.assertNotIn("deadbeef", dong)  # nguyên tắc «không token trong log»
            self.assertNotIn("deadbeefcafef00d", dong)
        all_logs = " ".join(self.logs)
        self.assertIn("OSError", all_logs)
        # Đã started nên KHÔNG gửi 502 nữa.
        handler.send_json.assert_not_called()

    def test_chunk_dau_loi_van_tra_502_nhu_cu(self):
        open_upstream = MagicMock(side_effect=OSError("ngay chunk đầu"))
        handler = self.make_handler(open_upstream)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ):
            handler.proxy_stream("deadbeefcafef00d")
        handler.send_json.assert_called_once_with(502, {"error": "stream_unavailable"})
        self.assertEqual([], self.logs)


if __name__ == "__main__":
    unittest.main()
