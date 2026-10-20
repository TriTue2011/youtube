"""Test Queue — danh sách bài phát kế tiếp, mỗi máy / mỗi loa một danh sách.

`queue.py` nhập khuôn mã từ `suggestions.py` bằng import tương đối, nên hai tệp
được nạp như một gói tối giản (không kéo Home Assistant vào).
"""

import importlib
import random
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"
GOI = "tritue_youtube_player_queue_test"

#: Mã thật của từng nguồn — không bịa chuỗi cho vừa khuôn.
MA_YOUTUBE = "kJQP7kiw5Fk"
MA_FACEBOOK = "1964113577722801"
MA_ZING = "Z6ABWEDF"
LOA = "media_player.phong_khach"
MAY = "device:3f2a9c1e-77b0"


def load_queue_module():
    if GOI not in sys.modules:
        package = types.ModuleType(GOI)
        package.__path__ = [str(COMPONENT_DIR)]
        sys.modules[GOI] = package
    return importlib.import_module(f"{GOI}.queue")


def bai(i, source="youtube"):
    ma = {"youtube": MA_YOUTUBE[:-1] + "abcdefghijk"[i], "facebook": MA_FACEBOOK, "zing": MA_ZING}[source]
    return {"source": source, "id": ma, "title": f"Bài {i}", "thumbnail": "https://i.ytimg.com/vi/x/0.jpg"}


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.q = load_queue_module()
        self.dem = 0

    def uid(self):
        self.dem += 1
        return f"{self.dem:08x}"

    def lam(self, doc, **payload):
        return self.q.apply_queue_change(doc, payload, self.uid)

    def them(self, doc, key, n):
        doc, _ = self.lam(doc, key=key, action="add", items=[bai(i) for i in range(n)])
        return doc

    def test_khoa_chi_nhan_loa_hoac_may(self):
        doc = self.q.normalize_document(None)
        for xau in ["", "light.den", "media_player.Phong", "device:ab", "device:../../x", None]:
            with self.assertRaises(ValueError):
                self.lam(doc, key=xau, action="clear")
        for tot in [LOA, MAY]:
            self.assertEqual(self.q.queue_key(tot), tot)

    def test_moi_nguon_mot_khuon_ma(self):
        doc = self.q.normalize_document(None)
        doc, _ = self.lam(doc, key=LOA, action="add",
                          items=[bai(0), bai(1, "facebook"), bai(2, "zing")])
        self.assertEqual([i["source"] for i in self.q.get_queue(doc, LOA)["items"]],
                         ["youtube", "facebook", "zing"])
        with self.assertRaises(ValueError):
            self.lam(doc, key=LOA, action="add", items=[{"source": "youtube", "id": MA_FACEBOOK, "title": "x"}])
        with self.assertRaises(ValueError):
            self.lam(doc, key=LOA, action="add", items=[{"source": "http", "id": "abc", "title": "x"}])

    def test_cung_mot_bai_them_hai_lan_la_hai_muc(self):
        doc = self.q.normalize_document(None)
        doc, _ = self.lam(doc, key=MAY, action="add", items=[bai(0)])
        doc, _ = self.lam(doc, key=MAY, action="add", items=[bai(0)])
        items = self.q.get_queue(doc, MAY)["items"]
        self.assertEqual(len(items), 2)
        self.assertNotEqual(items[0]["uid"], items[1]["uid"])

    def test_moi_khoa_deu_tro_ve_mot_hang_doi_duy_nhat(self):
        """Chủ máy 20/10/2026: «queue trên card chỉ có một ... chọn được loa để phát nên queue chỉ cần mã random 12 ký tự»."""
        doc = self.them(self.q.normalize_document(None), LOA, 3)
        doc = self.them(doc, MAY, 1)
        self.assertEqual(len(doc["queues"]), 1)
        self.assertEqual(list(doc["queues"]), [doc["id"]])
        for khoa in (LOA, MAY, "media_player.bep", doc["id"]):
            self.assertEqual(len(self.q.get_queue(doc, khoa)["items"]), 4, khoa)

    def test_ma_hang_doi_la_12_ky_tu_ngau_nhien_va_on_dinh(self):
        a = self.q.normalize_document(None)
        b = self.q.normalize_document(None)
        self.assertRegex(a["id"], r"^[a-z0-9]{12}$")
        self.assertNotEqual(a["id"], b["id"])                       # ngẫu nhiên giữa các nhà
        self.assertEqual(self.q.normalize_document(a)["id"], a["id"])   # nạp lại không đổi mã
        doc = self.them(a, LOA, 1)
        self.assertEqual(self.q.normalize_document(doc)["id"], a["id"])
        self.assertEqual(self.q.queue_key(a["id"]), a["id"])         # mã 12 ký tự là khoá hợp lệ

    def test_tai_lieu_cu_theo_loa_duoc_gop_thanh_mot(self):
        cu = {"queues": {
            LOA: {"items": [{**bai(0), "uid": "0000000a"}, {**bai(1), "uid": "0000000b"}], "current": "0000000b",
                  "mode": "audio", "order": "shuffle", "played": ["0000000b"]},
            MAY: {"items": [{**bai(1), "uid": "0000000c"}, {**bai(2), "uid": "0000000d"}], "current": None,
                  "mode": "video", "order": "sequential", "played": []},
            "media_player.rong": {"items": []},
        }}
        doc = self.q.normalize_document(cu)
        self.assertEqual(list(doc["queues"]), [doc["id"]])
        queue = doc["queues"][doc["id"]]
        # bài có «bài hiện tại» làm gốc; bài trùng (cùng nguồn + id) bỏ; không mất bài nào khác
        self.assertEqual([it["uid"] for it in queue["items"]], ["0000000a", "0000000b", "0000000d"])
        self.assertEqual((queue["current"], queue["mode"], queue["order"], queue["played"]), ("0000000b", "audio", "shuffle", ["0000000b"]))
        # gộp là idempotent
        self.assertEqual(self.q.normalize_document(doc), doc)

    def test_lan_luot_tu_dau_toi_het_roi_dung(self):
        doc = self.them(self.q.normalize_document(None), LOA, 3)
        tieu_de = []
        while True:
            doc, item = self.q.advance_queue(doc, LOA)
            if item is None:
                break
            tieu_de.append(item["title"])
        self.assertEqual(tieu_de, ["Bài 0", "Bài 1", "Bài 2"])

    def test_bam_mot_bai_thi_bai_ke_la_bai_dung_sau_no(self):
        doc = self.them(self.q.normalize_document(None), LOA, 4)
        uid = self.q.get_queue(doc, LOA)["items"][1]["uid"]
        doc, item = self.lam(doc, key=LOA, action="select", uid=uid)
        self.assertEqual(item["title"], "Bài 1")
        self.assertEqual(self.q.get_queue(doc, LOA)["current"], uid)
        _, ke = self.q.advance_queue(doc, LOA)
        self.assertEqual(ke["title"], "Bài 2")

    def test_xoa_bai_dang_phat_thi_van_sang_bai_dung_sau(self):
        doc = self.them(self.q.normalize_document(None), LOA, 3)
        items = self.q.get_queue(doc, LOA)["items"]
        doc, _ = self.lam(doc, key=LOA, action="select", uid=items[1]["uid"])
        doc, _ = self.lam(doc, key=LOA, action="remove", uid=items[1]["uid"])
        _, ke = self.q.advance_queue(doc, LOA)
        self.assertEqual(ke["title"], "Bài 2")

    def test_tron_phat_moi_bai_dung_mot_lan(self):
        doc = self.them(self.q.normalize_document(None), LOA, 6)
        doc, _ = self.lam(doc, key=LOA, action="set", order="shuffle")
        rng = random.Random(7)
        thay = []
        while True:
            doc, item = self.q.advance_queue(doc, LOA, rng)
            if item is None:
                break
            thay.append(item["title"])
        self.assertEqual(sorted(thay), [f"Bài {i}" for i in range(6)])
        self.assertNotEqual(thay, sorted(thay))

    def test_xoa_tat_ca_giu_che_do(self):
        doc = self.them(self.q.normalize_document(None), MAY, 2)
        doc, _ = self.lam(doc, key=MAY, action="set", mode="audio", order="shuffle")
        doc, _ = self.lam(doc, key=MAY, action="clear")
        queue = self.q.get_queue(doc, MAY)
        self.assertEqual((queue["items"], queue["mode"], queue["order"]), ([], "audio", "shuffle"))
        _, item = self.q.advance_queue(doc, MAY)
        self.assertIsNone(item)

    def test_danh_sach_rong_mac_dinh_khong_de_lai_ban_ghi(self):
        doc = self.them(self.q.normalize_document(None), LOA, 1)
        doc, _ = self.lam(doc, key=LOA, action="clear")
        self.assertEqual(doc["queues"], {})

    def test_kho_hong_duoc_lam_sach(self):
        doc = self.q.normalize_document({"queues": {
            LOA: {"items": [{**bai(0), "uid": "0000000a"}, {"id": "rac"}], "current": "khong_co",
                  "mode": "tivi", "order": "shuffle", "played": ["0000000a", "zz"]},
            "light.den": {"items": []},
        }})
        self.assertEqual(list(doc["queues"]), [doc["id"]])
        queue = doc["queues"][doc["id"]]
        self.assertEqual(len(queue["items"]), 1)
        self.assertIsNone(queue["current"])
        self.assertEqual((queue["mode"], queue["order"], queue["played"]), ("video", "shuffle", ["0000000a"]))

    def test_gioi_han_so_bai(self):
        doc = self.q.normalize_document(None)
        doc, _ = self.lam(doc, key=MAY, action="add", items=[bai(0)] * self.q.MAX_ITEMS)
        with self.assertRaises(ValueError) as loi:
            self.lam(doc, key=MAY, action="add", items=[bai(1)])
        self.assertEqual(str(loi.exception), "queue_full")



class QueuePrevTests(unittest.TestCase):
    """Nút lùi bài trong Queue (chủ máy 24/09/2026: "Queue không next hay lùi được bài")."""

    def setUp(self):
        self.q = load_queue_module()
        self.dem = 0

    def uid(self):
        self.dem += 1
        return f"{self.dem:08x}"

    def lam(self, doc, **payload):
        return self.q.apply_queue_change(doc, payload, self.uid)

    def test_lan_luot_lui_ve_bai_dung_truoc_roi_dung_o_dau(self):
        doc, _ = self.lam(self.q.normalize_document(None), key=LOA, action="add", items=[bai(i) for i in range(3)])
        uids = [i["uid"] for i in self.q.get_queue(doc, LOA)["items"]]
        doc, _ = self.lam(doc, key=LOA, action="select", uid=uids[2])
        doc, item = self.lam(doc, key=LOA, action="prev")
        self.assertEqual(item["title"], "Bài 1")
        doc, item = self.lam(doc, key=LOA, action="prev")
        self.assertEqual(item["title"], "Bài 0")
        doc, item = self.lam(doc, key=LOA, action="prev")
        self.assertIsNone(item)                       # đã ở đầu
        _doc, ke = self.lam(doc, key=LOA, action="next")
        self.assertEqual(ke["title"], "Bài 1")        # tiến lại đúng thứ tự

    def test_tron_lui_theo_lich_su_va_tra_bai_cho_luot_boc_sau(self):
        doc, _ = self.lam(self.q.normalize_document(None), key=LOA, action="add", items=[bai(i) for i in range(4)])
        doc, _ = self.lam(doc, key=LOA, action="set", order="shuffle")
        doc, a = self.q.advance_queue(doc, LOA, random.Random(1))
        doc, b = self.q.advance_queue(doc, LOA, random.Random(2))
        doc, item = self.lam(doc, key=LOA, action="prev")
        self.assertEqual(item["uid"], a["uid"])
        q = self.q.get_queue(doc, LOA)
        self.assertNotIn(b["uid"], q["played"])        # bài vừa rời được bốc lại sau
        self.assertEqual(q["current"], a["uid"])

    def test_chua_phat_bai_nao_trong_queue_thi_khong_lui(self):
        doc, _ = self.lam(self.q.normalize_document(None), key=MAY, action="add", items=[bai(0), bai(1)])
        _doc, item = self.lam(doc, key=MAY, action="prev")
        self.assertIsNone(item)


class QueueIndexTests(unittest.TestCase):
    """Test thao tac theo chi so (index) trong Queue."""

    def setUp(self):
        self.q = load_queue_module()
        self.dem = 0

    def uid(self):
        self.dem += 1
        return f"{self.dem:08x}"

    def lam(self, doc, **payload):
        return self.q.apply_queue_change(doc, payload, self.uid)

    def test_remove_va_select_bang_index(self):
        doc, _ = self.lam(self.q.normalize_document(None), key=LOA, action="add", items=[bai(0), bai(1), bai(2)])
        # Select bai index 1
        doc, item = self.lam(doc, key=LOA, action="select", index=1)
        self.assertEqual(item["title"], "Bài 1")
        # Remove bai index 0 (Bai 0)
        doc, _ = self.lam(doc, key=LOA, action="remove", index=0)
        items = self.q.get_queue(doc, LOA)["items"]
        self.assertEqual([i["title"] for i in items], ["Bài 1", "Bài 2"])

    def test_remove_index_am_nem_loi_item_not_found(self):
        doc, _ = self.lam(self.q.normalize_document(None), key=LOA, action="add", items=[bai(0)])
        with self.assertRaises(ValueError) as cm:
            self.lam(doc, key=LOA, action="remove", index=-1)
        self.assertEqual("item_not_found", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
