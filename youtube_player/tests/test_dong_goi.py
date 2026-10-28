"""Đóng gói Docker/add-on: trần tài nguyên và phiên bản khớp (docs/QUY-TAC-TAI-NGUYEN.md)."""
import re
import unittest
from pathlib import Path

import yaml

GOC = Path(__file__).resolve().parents[1]


class DongGoiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = yaml.safe_load((GOC / "docker-compose.yaml").read_text(encoding="utf-8"))["services"]["youtube-player"]
        cls.config = yaml.safe_load((GOC / "config.yaml").read_text(encoding="utf-8"))
        cls.dockerfile = (GOC / "Dockerfile").read_text(encoding="utf-8")

    def test_compose_co_tran_tai_nguyen(self):
        c = self.compose
        self.assertTrue(c.get("init"))
        for khoa in ("mem_limit", "memswap_limit", "cpus", "pids_limit"):
            self.assertIn(khoa, c, f"thiếu {khoa}")
        self.assertEqual(c["mem_limit"], c["memswap_limit"])          # không tràn sang swap
        self.assertIn("no-new-privileges:true", c.get("security_opt", []))

    def test_compose_xoay_vong_nhat_ky(self):
        log = self.compose["logging"]
        self.assertEqual(log["driver"], "json-file")
        self.assertIn("max-size", log["options"])
        self.assertIn("max-file", log["options"])

    def test_phien_ban_khop_giua_dockerfile_compose_va_addon(self):
        v = self.config["version"]
        self.assertTrue(self.compose["image"].endswith(":" + v), f"{self.compose['image']} lệch {v}")
        self.assertRegex(self.dockerfile, rf"ARG BUILD_VERSION={re.escape(v)}\b")

    def test_tuy_chon_trich_xuat_co_trong_addon(self):
        self.assertEqual(self.config["options"]["max_extract"], 2)
        self.assertEqual(self.config["schema"]["max_extract"], "int(1,8)")


if __name__ == "__main__":
    unittest.main()
