"""Kiem thu co che noi lai luong khi bi dut nguon trong PlayerHandler.proxy_stream.

Cac kich ban kiem thu:
- Khong loi: phat het bai 10 MiB binh thuong.
- Cat giua khuc roi noi dung offset: kiem doi so open_upstream, sha256 khop.
- Cat ngay ranh gioi 4 MiB: mo khuc tiep theo loi roi noi lai thanh cong.
- Ba lan cat lien tiep: thu lai nhieu lan voi thoi gian cho tang dan.
- Mo khuc ke het gio roi thanh cong: TimeoutError duoc xu ly dung.
- Qua 5 lan that bai: ngat luong, ghi log luong_that_bai, loa nhan dung so byte da gui.
- Ban noi sai (200 / lech offset / doi tong co): khong gui byte nao cho loa va thu tiep.
- Loa dong giua chung (BrokenPipeError): dung ngay, khong goi them open_upstream.
- end is None khong noi: giu hanh vi cu, khong noi lai, ghi log luong_that_bai.
- Log khong chua token: khong ghi token ke ca 8 ky tu dau.
- time.sleep duoc patch: test khong cho that.
- Dat lai bo dem loi lien tiep: thanh cong thi reset bo dem.
"""

import hashlib
import importlib.util
import io
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "youtube_player" / "app"

TOTAL_SIZE = 10 * 1024 * 1024  # 10 MiB
# Tao du lieu mau xac dinh de kiem tra sha256
FULL_DATA = bytes(i % 251 for i in range(TOTAL_SIZE))
FULL_SHA256 = hashlib.sha256(FULL_DATA).hexdigest()


def load_server_module(app_dir=None):
    env_dir = os.environ.get("SERVER_APP_DIR")
    target_dir = Path(env_dir) if env_dir else (app_dir or APP_DIR)
    sys.path.insert(0, str(target_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "tritue_player_server_test", target_dir / "server.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["tritue_player_server_test"] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if str(target_dir) in sys.path:
            sys.path.remove(str(target_dir))


class FakeResponse:
    def __init__(self, data, status=206, headers=None, cut_after=None, cut_error=None):
        self._data = io.BytesIO(data)
        self.status = status
        self.code = status
        self.headers = headers or {}
        self.cut_after = cut_after
        self.cut_error = cut_error
        self.read_bytes = 0
        self.closed = False

    def read(self, size=-1):
        if self.closed:
            return b""
        if self.cut_after is not None and self.read_bytes >= self.cut_after:
            raise self.cut_error or OSError("stream cut error")
        chunk = self._data.read(size)
        if self.cut_after is not None and self.read_bytes + len(chunk) > self.cut_after:
            allowed = self.cut_after - self.read_bytes
            self.read_bytes += allowed
            raise self.cut_error or OSError("stream cut error")
        self.read_bytes += len(chunk)
        return chunk

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class BrokenPipeWriter(io.BytesIO):
    def __init__(self, fail_after_bytes=0):
        super().__init__()
        self.fail_after_bytes = fail_after_bytes
        self.written_so_far = 0

    def write(self, b):
        if self.written_so_far >= self.fail_after_bytes:
            raise BrokenPipeError("Broken pipe")
        if self.written_so_far + len(b) > self.fail_after_bytes:
            allowed = self.fail_after_bytes - self.written_so_far
            super().write(b[:allowed])
            self.written_so_far += allowed
            raise BrokenPipeError("Broken pipe")
        self.written_so_far += len(b)
        return super().write(b)


class ProxyNoiLaiTests(unittest.TestCase):
    def setUp(self):
        self.server_mod = load_server_module()
        self.logs = []
        self.sleep_calls = []

    def make_handler(self, open_upstream_func, range_header="bytes=0-", wfile=None):
        handler = self.server_mod.PlayerHandler.__new__(self.server_mod.PlayerHandler)
        handler.headers = {"Range": range_header} if range_header is not None else {}
        handler.server = types.SimpleNamespace(
            integration_token="test_integration_token_secret",
            resolve_stream=MagicMock(),
            forget_stream=MagicMock(),
        )
        handler.open_upstream = open_upstream_func
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.send_json = MagicMock()
        handler.wfile = wfile if wfile is not None else io.BytesIO()
        logs = self.logs
        handler.log_message = lambda message, *args: logs.append(message % args)
        return handler

    def make_standard_open_upstream(self, plan=None):
        """Tao open_upstream theo ke hoach (plan) hoac mac dinh tra ve dung Range tu FULL_DATA."""
        call_index = 0
        calls = []

        def open_upstream(source, target, tu, den):
            nonlocal call_index
            calls.append((source, target, tu, den))
            if plan and call_index < len(plan):
                action = plan[call_index]
                call_index += 1
                if isinstance(action, Exception):
                    raise action
                if callable(action):
                    return action(source, target, tu, den)
                return action
            call_index += 1
            # Mac dinh: tra ve FakeResponse dung range
            end_idx = TOTAL_SIZE if den is None else den + 1
            chunk_data = FULL_DATA[tu:end_idx]
            headers = {
                "Content-Type": "audio/mpeg",
                "Content-Range": f"bytes {tu}-{tu + len(chunk_data) - 1}/{TOTAL_SIZE}",
                "Content-Length": str(len(chunk_data)),
            }
            resp = FakeResponse(chunk_data, status=206, headers=headers)
            return resp, {"content_type": "audio/mpeg"}

        return open_upstream, calls

    def test_khong_loi(self):
        """Khong gap loi: phat het bai 10 MiB, sha256 khop, khong log noi lai hay that bai."""
        open_func, calls = self.make_standard_open_upstream()
        handler = self.make_handler(open_func)

        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        self.assertEqual(len(FULL_DATA), len(handler.wfile.getvalue()))
        self.assertEqual(FULL_SHA256, hashlib.sha256(handler.wfile.getvalue()).hexdigest())
        # 10 MiB voi STREAM_CHUNK = 4 MiB -> 3 lan goi open_upstream (0-4M, 4M-8M, 8M-10M)
        self.assertEqual(3, len(calls))
        self.assertEqual(0, calls[0][2])
        self.assertEqual(4 * 1024 * 1024, calls[1][2])
        self.assertEqual(8 * 1024 * 1024, calls[2][2])
        # Khong co bat ky log loi hay noi lai nao
        self.assertEqual([], [log for log in self.logs if "luong_" in log])
        self.assertEqual([], self.sleep_calls)

    def test_cat_giua_khuc_roi_noi_dung_offset(self):
        """Cat giua khuc thu 2: noi lai tu dung byte da gui, sha256 khop."""
        calls = []

        def custom_open(source, target, tu, den):
            calls.append((source, target, tu, den))
            end_idx = TOTAL_SIZE if den is None else den + 1
            chunk_data = FULL_DATA[tu:end_idx]
            headers = {
                "Content-Type": "audio/mpeg",
                "Content-Range": f"bytes {tu}-{tu + len(chunk_data) - 1}/{TOTAL_SIZE}",
                "Content-Length": str(len(chunk_data)),
            }
            # O lan goi thu 2 (khuc 2 tu 4 MiB), cho dut giua chung sau 1 MiB
            if len(calls) == 2:
                resp = FakeResponse(
                    chunk_data,
                    status=206,
                    headers=headers,
                    cut_after=1024 * 1024,
                    cut_error=OSError("network drop midway"),
                )
            else:
                resp = FakeResponse(chunk_data, status=206, headers=headers)
            return resp, {"content_type": "audio/mpeg"}

        handler = self.make_handler(custom_open)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        # Loa phai nhan du 10 MiB voi sha256 khop
        self.assertEqual(len(FULL_DATA), len(handler.wfile.getvalue()))
        self.assertEqual(FULL_SHA256, hashlib.sha256(handler.wfile.getvalue()).hexdigest())

        # Lan goi thu 3 phai bat dau tu dung offset da gui: 4 MiB + 1 MiB = 5242880
        expected_offset = 4 * 1024 * 1024 + 1024 * 1024
        self.assertGreaterEqual(len(calls), 3)
        self.assertEqual(expected_offset, calls[2][2])

        # Kiem tra log
        dut_logs = [m for m in self.logs if "luong_dut_noi_lai" in m]
        self.assertEqual(1, len(dut_logs))
        self.assertIn(f"offset={expected_offset}", dut_logs[0])
        self.assertIn("lan=1", dut_logs[0])
        self.assertIn("OSError", dut_logs[0])
        self.assertIn("youtube", dut_logs[0])

        hoan_tat_logs = [m for m in self.logs if "luong_hoan_tat" in m]
        self.assertEqual(1, len(hoan_tat_logs))
        self.assertIn(f"so_byte={TOTAL_SIZE}", hoan_tat_logs[0])
        self.assertIn("so_lan_noi_lai=1", hoan_tat_logs[0])

        self.assertEqual([0.5], self.sleep_calls)

    def test_cat_ngay_ranh_gioi_4mib(self):
        """Cat ngay ranh gioi 4 MiB khi mo khuc thu 2: thu lai thanh cong."""
        calls = []
        attempt_khuc_2 = 0

        def custom_open(source, target, tu, den):
            nonlocal attempt_khuc_2
            calls.append((source, target, tu, den))
            if tu == 4 * 1024 * 1024:
                attempt_khuc_2 += 1
                if attempt_khuc_2 == 1:
                    raise OSError("connection refused at 4 MiB boundary")
            end_idx = TOTAL_SIZE if den is None else den + 1
            chunk_data = FULL_DATA[tu:end_idx]
            headers = {
                "Content-Type": "audio/mpeg",
                "Content-Range": f"bytes {tu}-{tu + len(chunk_data) - 1}/{TOTAL_SIZE}",
                "Content-Length": str(len(chunk_data)),
            }
            return FakeResponse(chunk_data, status=206, headers=headers), {"content_type": "audio/mpeg"}

        handler = self.make_handler(custom_open)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        self.assertEqual(len(FULL_DATA), len(handler.wfile.getvalue()))
        self.assertEqual(FULL_SHA256, hashlib.sha256(handler.wfile.getvalue()).hexdigest())

        dut_logs = [m for m in self.logs if "luong_dut_noi_lai" in m]
        self.assertEqual(1, len(dut_logs))
        self.assertIn(f"offset={4 * 1024 * 1024}", dut_logs[0])
        self.assertEqual([0.5], self.sleep_calls)

    def test_ba_lan_cat_lien_tiep(self):
        """Bi loi 3 lan lien tiep tai cung mot diem roi thanh cong: sleep 0.5, 1, 2."""
        calls = []
        fail_count = 0

        def custom_open(source, target, tu, den):
            nonlocal fail_count
            calls.append((source, target, tu, den))
            if tu == 4 * 1024 * 1024 and fail_count < 3:
                fail_count += 1
                raise OSError(f"intermittent failure #{fail_count}")
            end_idx = TOTAL_SIZE if den is None else den + 1
            chunk_data = FULL_DATA[tu:end_idx]
            headers = {
                "Content-Type": "audio/mpeg",
                "Content-Range": f"bytes {tu}-{tu + len(chunk_data) - 1}/{TOTAL_SIZE}",
                "Content-Length": str(len(chunk_data)),
            }
            return FakeResponse(chunk_data, status=206, headers=headers), {"content_type": "audio/mpeg"}

        handler = self.make_handler(custom_open)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        self.assertEqual(len(FULL_DATA), len(handler.wfile.getvalue()))
        self.assertEqual(FULL_SHA256, hashlib.sha256(handler.wfile.getvalue()).hexdigest())

        dut_logs = [m for m in self.logs if "luong_dut_noi_lai" in m]
        self.assertEqual(3, len(dut_logs))
        self.assertIn("lan=1", dut_logs[0])
        self.assertIn("lan=2", dut_logs[1])
        self.assertIn("lan=3", dut_logs[2])
        self.assertEqual([0.5, 1.0, 2.0], self.sleep_calls)

    def test_mo_khuc_ke_het_gio_roi_thanh_cong(self):
        """Mo khuc ke tiep bi TimeoutError roi lan sau thanh cong."""
        attempt = 0

        def custom_open(source, target, tu, den):
            nonlocal attempt
            if tu == 4 * 1024 * 1024:
                attempt += 1
                if attempt == 1:
                    raise TimeoutError("timed out waiting for upstream")
            end_idx = TOTAL_SIZE if den is None else den + 1
            chunk_data = FULL_DATA[tu:end_idx]
            headers = {
                "Content-Type": "audio/mpeg",
                "Content-Range": f"bytes {tu}-{tu + len(chunk_data) - 1}/{TOTAL_SIZE}",
                "Content-Length": str(len(chunk_data)),
            }
            return FakeResponse(chunk_data, status=206, headers=headers), {"content_type": "audio/mpeg"}

        handler = self.make_handler(custom_open)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        self.assertEqual(len(FULL_DATA), len(handler.wfile.getvalue()))
        dut_logs = [m for m in self.logs if "luong_dut_noi_lai" in m]
        self.assertEqual(1, len(dut_logs))
        self.assertIn("TimeoutError", dut_logs[0])
        self.assertEqual([0.5], self.sleep_calls)

    def test_qua_5_lan_that_bai(self):
        """Qua 5 lan thu that bai: ngat luong, ghi log luong_that_bai, khong ghi byte rac."""
        def custom_open(source, target, tu, den):
            if tu >= 4 * 1024 * 1024:
                raise OSError("permanent connection failure")
            end_idx = TOTAL_SIZE if den is None else den + 1
            chunk_data = FULL_DATA[tu:end_idx]
            headers = {
                "Content-Type": "audio/mpeg",
                "Content-Range": f"bytes {tu}-{tu + len(chunk_data) - 1}/{TOTAL_SIZE}",
                "Content-Length": str(len(chunk_data)),
            }
            return FakeResponse(chunk_data, status=206, headers=headers), {"content_type": "audio/mpeg"}

        handler = self.make_handler(custom_open)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        # Loa chi nhan dung 4 MiB cua chunk dau
        self.assertEqual(4 * 1024 * 1024, len(handler.wfile.getvalue()))
        self.assertEqual(FULL_DATA[: 4 * 1024 * 1024], handler.wfile.getvalue())

        # Phai co 5 lan luong_dut_noi_lai va 1 lan luong_that_bai
        dut_logs = [m for m in self.logs if "luong_dut_noi_lai" in m]
        self.assertEqual(5, len(dut_logs))
        that_bai_logs = [m for m in self.logs if "luong_that_bai" in m]
        self.assertEqual(1, len(that_bai_logs))
        self.assertIn(f"offset={4 * 1024 * 1024}", that_bai_logs[0])
        # Khong duoc log luong_hoan_tat
        self.assertEqual([], [m for m in self.logs if "luong_hoan_tat" in m])
        self.assertEqual([0.5, 1.0, 2.0, 2.0, 2.0], self.sleep_calls)

    def test_ban_noi_sai_khong_gui_byte_va_thu_tiep(self):
        """Ban noi sai (HTTP 200, sai offset, doi tong co): khong gui byte nao va thu tiep."""
        step = 0

        def custom_open(source, target, tu, den):
            nonlocal step
            end_idx = TOTAL_SIZE if den is None else den + 1
            chunk_data = FULL_DATA[tu:end_idx]
            normal_headers = {
                "Content-Type": "audio/mpeg",
                "Content-Range": f"bytes {tu}-{tu + len(chunk_data) - 1}/{TOTAL_SIZE}",
                "Content-Length": str(len(chunk_data)),
            }
            if tu == 0:
                return FakeResponse(chunk_data, status=206, headers=normal_headers), {"content_type": "audio/mpeg"}

            # Cac lan thu o khuc 2:
            step += 1
            rac_data = b"RAC_DATA_KHONG_DUOC_GUI_CHO_LOA" * 100
            if step == 1:
                # HTTP 200 thay vi 206
                headers = {"Content-Type": "audio/mpeg", "Content-Length": str(len(rac_data))}
                return FakeResponse(rac_data, status=200, headers=headers), {"content_type": "audio/mpeg"}
            elif step == 2:
                # 206 nhung Content-Range bat dau lech offset (0 thay vi 4 MiB)
                headers = {
                    "Content-Type": "audio/mpeg",
                    "Content-Range": f"bytes 0-{len(rac_data) - 1}/{TOTAL_SIZE}",
                    "Content-Length": str(len(rac_data)),
                }
                return FakeResponse(rac_data, status=206, headers=headers), {"content_type": "audio/mpeg"}
            elif step == 3:
                # 206 dung offset nhung doi tong co
                headers = {
                    "Content-Type": "audio/mpeg",
                    "Content-Range": f"bytes {tu}-{tu + len(rac_data) - 1}/999999999",
                    "Content-Length": str(len(rac_data)),
                }
                return FakeResponse(rac_data, status=206, headers=headers), {"content_type": "audio/mpeg"}
            else:
                # Lan 4 thanh cong
                return FakeResponse(chunk_data, status=206, headers=normal_headers), {"content_type": "audio/mpeg"}

        handler = self.make_handler(custom_open)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        # Loa phai nhan dung 10 MiB, khong bi nhiem byte rac nao
        self.assertEqual(len(FULL_DATA), len(handler.wfile.getvalue()))
        self.assertEqual(FULL_SHA256, hashlib.sha256(handler.wfile.getvalue()).hexdigest())
        self.assertNotIn(b"RAC_DATA", handler.wfile.getvalue())

        # Phai co 3 lan bao loi ban noi sai
        dut_logs = [m for m in self.logs if "luong_dut_noi_lai" in m]
        self.assertEqual(3, len(dut_logs))
        self.assertEqual([0.5, 1.0, 2.0], self.sleep_calls)

    def test_loa_dong_giua_chung_khong_goi_them_open_upstream(self):
        """Loa dong giua chung (wfile.write nem BrokenPipeError): dung NGAY, khong goi them open_upstream."""
        open_func, calls = self.make_standard_open_upstream()
        # Cho loa ngat sau khi ghi 1 MiB
        broken_wfile = BrokenPipeWriter(fail_after_bytes=1024 * 1024)
        handler = self.make_handler(open_func, wfile=broken_wfile)

        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        # Chi duoc goi open_upstream dung 1 lan cho chunk dau tien
        self.assertEqual(1, len(calls))
        # Khong duoc log luong_that_bai hay luong_dut_noi_lai
        self.assertEqual([], [m for m in self.logs if "luong_that_bai" in m])
        self.assertEqual([], [m for m in self.logs if "luong_dut_noi_lai" in m])
        self.assertEqual([], self.sleep_calls)

    def test_end_is_none_khong_noi(self):
        """Khong biet tong co (end is None): nguon dut khong noi lai, log luong_that_bai."""
        calls = []

        def custom_open(source, target, tu, den):
            calls.append((source, target, tu, den))
            chunk_data = FULL_DATA[: 1024 * 1024]
            # Headers khong co Content-Range va Content-Length de stream_total_size tra ve 0
            headers = {"Content-Type": "audio/mpeg"}
            resp = FakeResponse(
                chunk_data,
                status=200,
                headers=headers,
                cut_after=512 * 1024,
                cut_error=OSError("cut when size unknown"),
            )
            return resp, {"content_type": "audio/mpeg"}

        # Range header la None de asked_end cung la None
        handler = self.make_handler(custom_open, range_header=None)

        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch.object(
            self.server_mod, "stream_total_size", return_value=0
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        # Chi goi open_upstream dung 1 lan, khong goi lan 2 de noi
        self.assertEqual(1, len(calls))
        # Loa nhan duoc 512 KiB
        self.assertEqual(512 * 1024, len(handler.wfile.getvalue()))
        # Phai log luong_that_bai
        that_bai_logs = [m for m in self.logs if "luong_that_bai" in m]
        self.assertEqual(1, len(that_bai_logs))
        self.assertIn(f"offset={512 * 1024}", that_bai_logs[0])
        self.assertEqual([], self.sleep_calls)

    def test_log_khong_chua_token(self):
        """Tat ca cac log sinh ra KHONG duoc chua token (ke ca 8 ky tu dau)."""
        token = "deadbeefcafef00d12345678"

        def custom_open(source, target, tu, den):
            if tu >= 4 * 1024 * 1024:
                raise OSError("error for logging")
            chunk_data = FULL_DATA[tu : tu + 4 * 1024 * 1024]
            headers = {
                "Content-Type": "audio/mpeg",
                "Content-Range": f"bytes {tu}-{tu + len(chunk_data) - 1}/{TOTAL_SIZE}",
                "Content-Length": str(len(chunk_data)),
            }
            return FakeResponse(chunk_data, status=206, headers=headers), {"content_type": "audio/mpeg"}

        handler = self.make_handler(custom_open)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream(token)

        self.assertGreater(len(self.logs), 0)
        for dong in self.logs:
            self.assertNotIn("deadbeef", dong)
            self.assertNotIn("cafef00d", dong)
            self.assertNotIn(token, dong)

    def test_thanh_cong_dat_lai_bo_dem_loi_lien_tiep(self):
        """Thanh cong o giua luong phai reset bo dem loi lien tiep."""
        calls = []
        fail_at_5m = 0
        fail_at_8m = 0

        def custom_open(source, target, tu, den):
            nonlocal fail_at_5m, fail_at_8m
            calls.append((source, target, tu, den))
            if tu == 4 * 1024 * 1024:
                if fail_at_5m < 3:
                    fail_at_5m += 1
                    raise OSError("failure at 4M")
            if tu == 8 * 1024 * 1024:
                if fail_at_8m < 3:
                    fail_at_8m += 1
                    raise OSError("failure at 8M")
            end_idx = TOTAL_SIZE if den is None else den + 1
            chunk_data = FULL_DATA[tu:end_idx]
            headers = {
                "Content-Type": "audio/mpeg",
                "Content-Range": f"bytes {tu}-{tu + len(chunk_data) - 1}/{TOTAL_SIZE}",
                "Content-Length": str(len(chunk_data)),
            }
            return FakeResponse(chunk_data, status=206, headers=headers), {"content_type": "audio/mpeg"}

        handler = self.make_handler(custom_open)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        # Neu khong reset bo dem thi 3 + 3 = 6 lan loi > 5 se bi fail o 8M.
        # Nho reset bo dem, ca 2 lan deu vuot qua va stream thanh cong!
        self.assertEqual(len(FULL_DATA), len(handler.wfile.getvalue()))
        self.assertEqual(FULL_SHA256, hashlib.sha256(handler.wfile.getvalue()).hexdigest())
        hoan_tat_logs = [m for m in self.logs if "luong_hoan_tat" in m]
        self.assertEqual(1, len(hoan_tat_logs))
        self.assertIn("so_lan_noi_lai=2", hoan_tat_logs[0])

    def test_khuc_hop_le_nhung_rong_khong_lap_vo_han(self):
        """Nguon tra 206 + Content-Range dung nhung than RONG: khong tien duoc byte nao thi phai tinh la that bai, het 5 lan thi ngat."""
        calls = []

        def open_rong(source, target, tu, den):
            calls.append(tu)
            if len(calls) > 60:
                raise RuntimeError("vong lap vo han: nguon rong nhung van mo lai mai")
            if tu == 0:
                data = FULL_DATA[0:4 * 1024 * 1024]
            else:
                data = b""
            end_idx = tu + max(len(data), 1) - 1
            headers = {
                "Content-Type": "audio/mpeg",
                "Content-Range": f"bytes {tu}-{end_idx}/{TOTAL_SIZE}",
            }
            return FakeResponse(data, status=206, headers=headers), {"content_type": "audio/mpeg"}

        handler = self.make_handler(open_rong)
        with patch.object(
            self.server_mod, "verify_stream_token", return_value=("youtube", "dQw4w9WgXcQ")
        ), patch("time.sleep", side_effect=self.sleep_calls.append):
            handler.proxy_stream("test_token_secret_12345678")

        self.assertEqual(4 * 1024 * 1024, len(handler.wfile.getvalue()))
        self.assertEqual(1, len([m for m in self.logs if "luong_that_bai" in m]))
        self.assertLessEqual(len(calls), 1 + 1 + 5)


if __name__ == "__main__":
    unittest.main()
