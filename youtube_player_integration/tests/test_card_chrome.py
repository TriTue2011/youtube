"""Thẻ THẬT trong Chrome với Home Assistant giả: thanh tua dưới hàng nút + khôi phục loa khi vào lại.

Chủ máy 19/10/2026: (1) «có chỗ tua nhạc ngay trong hộp dưới các nút điều khiển»; (2) «thoát vào lại HA thì phải giữ trình phát ở loa nào,
đang phát bài nào đến đâu; nhiều bài trên nhiều loa thì giữ ở loa cuối cùng thoát app». Test hàm thuần ở test-card-progress.js; test này
chạy cả thẻ để biết phần NỐI vào thẻ không ném lỗi và cho đúng kết quả trên màn hình. Không có Chrome thì bỏ qua (có báo rõ).
"""
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent / "card_harness.html"
CHROME = (
    shutil.which("google-chrome")
    or shutil.which("google-chrome-stable")
    or shutil.which("chromium")
    or shutil.which("chromium-browser")
    or os.environ.get("CHROME_BIN")        # NV186: VM có Chromium ở /opt/meta-chromium/chrome, không nằm trong PATH
)


def giay(text):
    phut, s = text.split(":")
    return int(phut) * 60 + int(s)


@unittest.skipUnless(CHROME, "không có Chrome trong môi trường này — test thẻ trong trình duyệt chưa chạy")
class TheTrongChromeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as profile:
            done = subprocess.run(
                [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--allow-file-access-from-files",
                 f"--user-data-dir={profile}", "--virtual-time-budget=60000", "--dump-dom", HARNESS.as_uri()],
                capture_output=True, text=True, timeout=420)
        match = re.search(r'<pre id="out">(.*?)</pre>', done.stdout, re.S)
        if not match:
            raise AssertionError("trang thử không in kết quả:\n" + done.stdout[:800] + done.stderr[-500:])
        data = json.loads(html.unescape(match.group(1)))
        cls.loi = data["loi"]
        cls.kq = {r["ten"]: r for r in data["kq"]}

    def test_khong_co_loi_javascript(self):
        self.assertEqual([], self.loi)
        self.assertEqual(12, len(self.kq))

    def test_hang_doi_duy_nhat_mot_khoi_va_ma_12_ky_tu(self):
        """NV186 (0.27.18): thẻ chỉ còn MỘT khối «Hàng đợi», mã 12 ký tự; nút chép ra `queue_code: <12 ký tự>`."""
        r = self.kq["Q_hang_doi_duy_nhat"]
        self.assertEqual("Hàng đợi", r["tieuDe"])
        self.assertIn("2 bài", r["dem"])
        self.assertRegex(r["ma"], r"^[a-z0-9]{12}$")
        self.assertEqual(r["ma"], r["khoa"])
        self.assertEqual(f"queue_code: {r['ma']}", r["chep"])
        self.assertEqual(2, r["soMuc"])

    def test_loa_khong_bao_vi_tri_van_co_thanh_tua_va_gio_uoc(self):
        r = self.kq["A_d50s_khong_bao_vi_tri"]
        self.assertFalse(r["thanhAn"], "thanh tua phải hiện dưới hàng nút")
        self.assertAlmostEqual(75, giay(r["troi"]), delta=5)
        self.assertEqual("3:37", r["tong"])

    def test_tua_tren_loa_khong_co_seek_bao_ro_ly_do(self):
        self.assertIn("không hỗ trợ tua", self.kq["A_d50s_khong_bao_vi_tri"]["trangThai"])

    def test_tua_tren_loa_co_seek_gui_media_seek_dung_giay_va_dong_ho_theo(self):
        r = self.kq["B_cam_co_SEEK"]
        self.assertEqual(1, len(r["goi"]))
        self.assertEqual(["media_player.cam"], r["goi"][0]["entity_id"])
        self.assertAlmostEqual(108.5, r["goi"][0]["seek_position"], delta=1)
        self.assertGreaterEqual(giay(r["troiSauTua"]), 108)

    def test_nhieu_phien_giu_loa_cuoi_cung_thoat_app(self):
        r = self.kq["C_nhieu_phien_giu_loa_cuoi"]
        self.assertEqual(["media_player.cam"], r["chon"])
        self.assertEqual("media_player.cam", r["cuoi"])

    def test_khong_luu_thi_theo_phien_moi_nhat(self):
        self.assertEqual(["media_player.d50s"], self.kq["D_nhieu_phien_khong_luu_thi_moi_nhat"]["chon"])

    def test_khong_phat_gi_van_giu_loa_da_chon(self):
        r = self.kq["E_khong_phat_giu_loa_da_chon"]
        self.assertEqual(["media_player.cam"], r["chon"])
        self.assertEqual("media_player.cam", r["cuoi"])

    def test_vao_lai_giu_giay_da_luu_khong_ve_lai_tu_dau(self):
        self.assertGreaterEqual(giay(self.kq["G_vao_lai_giu_giay_da_luu"]["troi"]), 98)   # đã lưu 100 s, máy phát chỉ nói 75 s

    def test_vao_lai_o_bai_khac_thi_tinh_lai_gio(self):
        self.assertAlmostEqual(75, giay(self.kq["H_vao_lai_bai_khac_tinh_lai_giay"]["troi"]), delta=5)

    def test_trang_thai_duoc_luu_dinh_ky(self):
        luu = json.loads(self.kq["F_luu_dinh_ky"]["luu"])
        self.assertEqual(["media_player.d50s"], luu["chon"])
        self.assertEqual("media_player.d50s", luu["cuoi"])
        self.assertTrue(luu["uoc"] and luu["uoc"]["key"].startswith("s1|"))

    def test_facebook_action_roi_mo_the_co_thanh_tua_va_tua_duoc(self):
        """NV203 (f): bài Facebook bắt đầu bằng action rồi mới mở thẻ."""
        r = self.kq["FB_f_action_roi_mo_the"]
        self.assertFalse(r["thanhAn"], "thanh tua phải hiện cho bài Facebook")
        self.assertEqual("3:07", r["tong"])
        self.assertEqual(1, len(r["goi"]))
        self.assertEqual(["media_player.cam"], r["goi"][0]["entity_id"])
        self.assertAlmostEqual(93.5, r["goi"][0]["seek_position"], delta=1)

    def test_facebook_doi_bai_khi_the_dang_mo(self):
        """NV203 (g): thẻ đang mở, action đổi sang bài Facebook."""
        r = self.kq["FB_g_doi_bai_khi_the_dang_mo"]
        self.assertFalse(r["thanhAn"])
        self.assertEqual("3:07", r["tong"])

    def test_facebook_youtube_facebook_theo_dung_bai(self):
        """NV203 (h): action chuyển FB → YouTube → FB, thanh tua theo từng bài."""
        r = self.kq["FB_h_fb_youtube_fb"]
        self.assertEqual(["3:07", "3:37", "3:07"], r["tong"])


if __name__ == "__main__":
    unittest.main()
