"""Chạy test node của các hàm chép mã trên thẻ (`test-card-copy.js`) trong bộ test Python."""
import shutil
import subprocess
import unittest
from pathlib import Path

JS = Path(__file__).resolve().parent / "test-card-copy.js"


class CardCopyJsTests(unittest.TestCase):
    def test_ham_chep_ma_cua_the(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("không có node trong môi trường này — test thẻ chưa chạy")
        done = subprocess.run([node, str(JS)], capture_output=True, text=True, timeout=60)
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
