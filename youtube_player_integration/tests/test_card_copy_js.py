"""Chạy các test node của thẻ (hàm thuần: chép mã, thanh tua, khôi phục loa) trong bộ test Python."""
import shutil
import subprocess
import unittest
from pathlib import Path

DIR = Path(__file__).resolve().parent


class CardJsTests(unittest.TestCase):
    def _chay(self, ten):
        node = shutil.which("node")
        if node is None:
            self.skipTest("không có node trong môi trường này — test thẻ chưa chạy")
        done = subprocess.run([node, str(DIR / ten)], capture_output=True, text=True, timeout=60)
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)

    def test_ham_chep_ma_cua_the(self):
        self._chay("test-card-copy.js")

    def test_tim_playlist_theo_ten_khong_de_tao_ban_trung(self):
        self._chay("test-card-playlist-name.js")

    def test_ham_thanh_tua_va_khoi_phuc_loa_cua_the(self):
        self._chay("test-card-progress.js")


if __name__ == "__main__":
    unittest.main()
