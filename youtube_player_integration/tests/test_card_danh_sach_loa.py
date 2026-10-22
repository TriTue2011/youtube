"""Danh sách loa của thẻ trong Chrome thật: chỉ loại loa «không khả dụng», KHÔNG loại loa idle/off; khung không cắt loa.

Lỗi 23/10/2026: khung chip loa cố định cao 132 px (≈ 3 chip). Nhà có 6 loa thì loa thứ 4 trở đi (ví dụ Phicomm R1) nằm dưới, phải
vuốt trong khung; thanh cuộn mảnh nên trên điện thoại người dùng tưởng loa «không có». Khung nay tự cao theo số loa."""
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

CARD = Path(__file__).resolve().parents[2] / "custom_components" / "tritue_youtube_player" / "www" / "tritue-youtube-player-card.js"
CHROME = (shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chromium")
          or shutil.which("chromium-browser") or os.environ.get("CHROME_BIN"))

PAGE = """<!doctype html><meta charset="utf-8"><body><pre id="out">chưa chạy</pre>
<script src="@CARD@"></script>
<script>(async () => {
const ENT = "media_player.tritue_youtube_player_x";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const mk = (id, ten, trangThai) => ({ entity_id: id, state: trangThai, attributes: { friendly_name: ten, supported_features: 1048576 | 512 | 4096 } });
async function dung(danhSach) {
  localStorage.clear();
  const states = { [ENT]: { entity_id: ENT, state: "idle", attributes: { friendly_name: "YT", supported_features: 4346625, sessions: [],
    session_revision: 1, config_entry_id: "E1", output_entity_ids: [] } } };
  const entities = { [ENT]: { entity_id: ENT, platform: "tritue_youtube_player" } };
  danhSach.forEach(([id, ten, tt]) => { states[id] = mk(id, ten, tt); entities[id] = { entity_id: id, platform: "x" }; });
  const hass = { states, entities, config: { language: "vi" }, user: { is_admin: true }, language: "vi",
    callService: async () => ({}), callApi: async () => ({}), callWS: async () => ({}), connection: { subscribeEvents: async () => () => {} } };
  const c = document.createElement("tritue-youtube-player-card"); document.body.appendChild(c);
  c.style.display = "block"; c.style.width = "420px";
  c.setConfig({ entity: ENT }); c.hass = hass; await sleep(300);
  c.hass = { ...hass, states: { ...states } }; await sleep(300);
  const sr = c.shadowRoot, ds = sr.querySelector(".players-audio");
  sr.querySelector(".spk-list").hidden = false;                  // «Đổi loa» mở khung danh sách
  await sleep(150);
  const r = { chips: [...sr.querySelectorAll(".player-chip")].map((x) => x.dataset.entity),
    cao: ds.clientHeight, noi: ds.scrollHeight };
  c.remove();
  return r;
}
const sau = [["media_player.bluetooth", "Bluetooth Speaker", "off"], ["media_player.cam", "Cam phong khach Loa", "idle"],
  ["media_player.d50s", "D50s", "off"], ["media_player.r1_loa", "Phicomm R1 Loa", "idle"],
  ["media_player.r1_dlna", "Phicomm_R1_912F", "idle"], ["media_player.googlehome", "Phòng khách", "off"],
  ["media_player.tv_hong", "Ti vi hỏng", "unavailable"]];
const nhieu = []; for (let i = 0; i < 40; i++) nhieu.push(["media_player.loa_" + i, "Loa so " + i, "idle"]);
const kq = { sau: await dung(sau), nhieu: await dung(nhieu) };
document.getElementById("out").textContent = JSON.stringify({ kq });
})();</script>"""


@unittest.skipUnless(CHROME, "không có Chrome trong môi trường này — test thẻ trong trình duyệt chưa chạy")
class DanhSachLoaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "dsloa.html"
            page.write_text(PAGE.replace("@CARD@", CARD.as_uri()), encoding="utf-8")
            done = subprocess.run(
                [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--allow-file-access-from-files",
                 f"--user-data-dir={tmp}/hs", "--virtual-time-budget=20000", "--dump-dom", page.as_uri()],
                capture_output=True, text=True, timeout=120)
        m = re.search(r'<pre id="out">(.*?)</pre>', done.stdout, re.S)
        if not m:
            raise AssertionError("trang thử không in kết quả:\n" + done.stdout[:600] + done.stderr[-400:])
        cls.kq = json.loads(html.unescape(m.group(1)))["kq"]

    def test_chi_loai_khong_kha_dung_khong_loai_idle_hay_off(self):
        chips = self.kq["sau"]["chips"]
        self.assertEqual(6, len(chips), chips)
        for e in ("media_player.bluetooth", "media_player.cam", "media_player.d50s", "media_player.r1_loa",
                  "media_player.r1_dlna", "media_player.googlehome"):
            self.assertIn(e, chips)
        self.assertNotIn("media_player.tv_hong", chips)             # unavailable thì ẩn

    def test_khung_loa_khong_cat_chip_khi_vua_du_loa(self):
        r = self.kq["sau"]
        self.assertGreaterEqual(r["cao"], r["noi"] - 1, "6 loa phải hiện hết, không phải vuốt trong khung (trước đây cứng 132px)")
        self.assertGreater(r["cao"], 132)

    def test_khung_loa_co_tran_tren_khi_qua_nhieu_loa(self):
        r = self.kq["nhieu"]
        self.assertEqual(40, len(r["chips"]))
        self.assertLessEqual(r["cao"], 420)                            # trần: không đẩy cả thẻ ra khỏi màn hình
        self.assertGreater(r["noi"], r["cao"])                         # quá dài thì mới cuộn trong khung


if __name__ == "__main__":
    unittest.main()
