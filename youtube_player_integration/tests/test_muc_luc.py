"""Mục lục MP4 và quyết định đường khúc — không cần Home Assistant.

Nạp thẳng file, không qua ``__init__`` của tích hợp (file đó kéo Home Assistant).
"""

import importlib.util
import unittest
from pathlib import Path
from urllib.parse import urljoin


_PATH = Path(__file__).resolve().parents[2] / "custom_components" / "tritue_youtube_player" / "muc_luc.py"
_spec = importlib.util.spec_from_file_location("muc_luc_thu", _PATH)
_muc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_muc)
danh_sach_hls = _muc.danh_sach_hls
doc_muc_luc_mp4 = _muc.doc_muc_luc_mp4
kem_danh_sach = _muc.kem_danh_sach
url_khuc_tuong_doi = _muc.url_khuc_tuong_doi


def _hop(typ: bytes, payload: bytes) -> bytes:
    return (8 + len(payload)).to_bytes(4, "big") + typ + payload


def _sidx(timescale: int, refs: list[tuple[int, int]]) -> bytes:
    body = bytearray()
    body += bytes((0, 0, 0, 0))
    body += (1).to_bytes(4, "big")
    body += timescale.to_bytes(4, "big")
    body += (0).to_bytes(4, "big")
    body += (0).to_bytes(4, "big")
    body += (0).to_bytes(2, "big")
    body += len(refs).to_bytes(2, "big")
    for dai, giay_don in refs:
        body += dai.to_bytes(4, "big")
        body += giay_don.to_bytes(4, "big")
        body += (0).to_bytes(4, "big")
    return _hop(b"sidx", bytes(body))


class MucLucTest(unittest.TestCase):
    def test_hai_khuc_va_dia_chi_tuong_doi(self):
        ftyp = _hop(b"ftyp", b"dash" + b"\x00" * 12)
        moov = _hop(b"moov", b"\x00" * 20)
        sx = _sidx(1000, [(100, 10000), (40, 5000)])
        tep = ftyp + moov + sx + b"\x00" * 140
        muc = doc_muc_luc_mp4(tep)
        self.assertIsNotNone(muc)
        khoi, khuc = muc
        self.assertEqual(len(ftyp) + len(moov), khoi)
        self.assertEqual(
            [(khoi + len(sx), 100, 10.0), (khoi + len(sx) + 100, 40, 5.0)],
            khuc,
        )
        tuong_doi = url_khuc_tuong_doi("tok", "/api/tritue_youtube_player/proxy/tok?authSig=abc%3A1")
        text = danh_sach_hls(khoi, khuc, tuong_doi)
        self.assertIn("#EXT-X-PLAYLIST-TYPE:VOD", text)
        self.assertIn(f'BYTERANGE="{khoi}@0"', text)
        self.assertIn("#EXT-X-BYTERANGE:100@", text)
        self.assertEqual(2, text.count("#EXTINF:"))
        # Khúc đầu khoảng 10 giây, không phải cả bài.
        self.assertIn("#EXTINF:10.000,", text)
        goc = "https://ha.example/api/tritue_youtube_player/proxy/tok.m3u8?authSig=cu"
        tuyet = urljoin(goc, tuong_doi)
        self.assertEqual(
            "https://ha.example/api/tritue_youtube_player/proxy/tok?authSig=abc%3A1",
            tuyet,
        )
        # Byte khúc đầu đúng là tiếng, không phải mục lục.
        bat_dau, dai, _giay = khuc[0]
        self.assertEqual(tep[bat_dau:bat_dau + dai], b"\x00" * 100)

    def test_sidx_chi_toi_muc_luc_khac_thi_bo(self):
        sx = _sidx(1000, [(100 | 0x80000000, 1000)])
        self.assertIsNone(doc_muc_luc_mp4(_hop(b"ftyp", b"x" * 8) + sx))

    def test_khong_co_sidx_thi_bo(self):
        self.assertIsNone(doc_muc_luc_mp4(_hop(b"ftyp", b"dash" + b"\x00" * 8) + _hop(b"moov", b"\x00" * 12)))

    def test_youtube_co_danh_sach_nguon_khac_thi_khong(self):
        self.assertTrue(kem_danh_sach("youtube"))
        self.assertTrue(kem_danh_sach("youtube_video"))
        self.assertFalse(kem_danh_sach("zing"))
        self.assertFalse(kem_danh_sach("facebook"))
        self.assertFalse(kem_danh_sach("facebook_video"))


if __name__ == "__main__":
    unittest.main()
