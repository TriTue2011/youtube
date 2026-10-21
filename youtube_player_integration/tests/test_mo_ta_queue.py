"""Soát 0.27.18 (NV186): mô tả ô `queue_code` của action `play_queue` vẫn viết theo kiểu CŨ
(hàng đợi riêng từng loa: «Leave empty to use the queue saved under the first selected speaker»,
ví dụ `media_player.living_room`) dù 0.27.18 đã đổi thành MỘT hàng đợi duy nhất mã 12 ký tự.

Test thuần (chỉ đọc services.yaml / strings.json / translations/vi.json, không cần Home Assistant):
mô tả phải nói hàng đợi duy nhất + mã 12 ký tự, không còn nhắc «loa đầu tiên được chọn».
"""

import json
import re
import unittest
from pathlib import Path

import yaml

COMPONENT_DIR = Path(__file__).resolve().parents[2] / "custom_components" / "tritue_youtube_player"
MA_12 = re.compile(r"^[a-z0-9]{12}$")
CU = ("first selected speaker", "loa đầu tiên", "loa đầu tiên được chọn")


class MoTaQueueCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.yaml = yaml.safe_load((COMPONENT_DIR / "services.yaml").read_text(encoding="utf-8"))
        cls.en = json.loads((COMPONENT_DIR / "strings.json").read_text(encoding="utf-8"))
        cls.vi = json.loads((COMPONENT_DIR / "translations" / "vi.json").read_text(encoding="utf-8"))

    def test_services_yaml_noi_hang_doi_duy_nhat(self):
        truong = self.yaml["play_queue"]["fields"]["queue_code"]
        mo_ta = truong["description"]
        for cum in CU:
            self.assertNotIn(cum, mo_ta, f"mô tả services.yaml còn kiểu cũ ({cum!r})")
        self.assertIn("12", mo_ta)
        self.assertTrue(MA_12.fullmatch(str(truong.get("example") or "")),
                        f"ví dụ phải là mã 12 ký tự, đang là {truong.get('example')!r}")

    def test_strings_json_noi_hang_doi_duy_nhat(self):
        mo_ta = self.en["services"]["play_queue"]["fields"]["queue_code"]["description"]
        for cum in CU:
            self.assertNotIn(cum, mo_ta, f"mô tả strings.json còn kiểu cũ ({cum!r})")
        self.assertIn("12", mo_ta)

    def test_vi_json_noi_hang_doi_duy_nhat(self):
        mo_ta = self.vi["services"]["play_queue"]["fields"]["queue_code"]["description"]
        for cum in CU:
            self.assertNotIn(cum, mo_ta, f"mô tả vi.json còn kiểu cũ ({cum!r})")
        self.assertIn("12", mo_ta)


if __name__ == "__main__":
    unittest.main()
