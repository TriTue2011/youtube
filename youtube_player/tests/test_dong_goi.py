"""Đóng gói Docker/add-on: trần tài nguyên và phiên bản khớp (docs/QUY-TAC-TAI-NGUYEN.md).

Chỉ dùng thư viện chuẩn: workflow CI chạy bước này trên Python trơn (không có PyYAML); thiếu thư viện làm bước kiểm thử hỏng và
ảnh add-on KHÔNG được dựng (đã xảy ra 28/10/2026: add-on 0.9.9 không cập nhật được vì ảnh không tồn tại)."""
import re
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]


def doc(ten: str) -> str:
    return (GOC / ten).read_text(encoding="utf-8")


def gia_tri(van_ban: str, khoa: str) -> str:
    m = re.search(rf"^\s*{re.escape(khoa)}:\s*[\"']?([^\"'\n#]+?)[\"']?\s*(?:#.*)?$", van_ban, re.M)
    assert m, f"thiếu {khoa}"
    return m.group(1).strip()


class DongGoiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = doc("docker-compose.yaml")
        cls.config = doc("config.yaml")
        cls.dockerfile = doc("Dockerfile")

    def test_compose_co_tran_tai_nguyen(self):
        self.assertRegex(self.compose, r"(?m)^\s*init:\s*true")
        for khoa in ("mem_limit", "memswap_limit", "cpus", "pids_limit"):
            gia_tri(self.compose, khoa)
        self.assertEqual(gia_tri(self.compose, "mem_limit"), gia_tri(self.compose, "memswap_limit"))   # không tràn sang swap
        self.assertIn("no-new-privileges:true", self.compose)

    def test_compose_xoay_vong_nhat_ky(self):
        self.assertEqual(gia_tri(self.compose, "driver"), "json-file")
        gia_tri(self.compose, "max-size")
        gia_tri(self.compose, "max-file")

    def test_phien_ban_khop_giua_dockerfile_compose_va_addon(self):
        v = gia_tri(self.config, "version")
        self.assertTrue(gia_tri(self.compose, "image").endswith(":" + v), f"image lệch {v}")
        self.assertRegex(self.dockerfile, rf"ARG BUILD_VERSION={re.escape(v)}\b")

    def test_tuy_chon_trich_xuat_co_trong_addon(self):
        self.assertEqual(gia_tri(self.config, "max_extract"), "2")
        self.assertEqual(gia_tri(self.config, "max_extract").isdigit(), True)
        self.assertRegex(self.config, r'max_extract:\s*"int\(1,8\)"')


if __name__ == "__main__":
    unittest.main()
