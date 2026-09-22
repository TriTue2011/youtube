"""Mục lục MP4 cắt mảnh và danh sách khúc.

Tệp YouTube có ``moov`` rỗng và mục lục thật nằm ở hộp ``sidx``. Trình nào
nhận cả tệp thì hoặc chờ theo độ dài bài (WebKit), hoặc tải hết trong nền
(Chrome, Android) và kéo theo cả hình. Đọc ``sidx`` rồi trả từng mảnh khoảng
10 giây để phát sau mảnh đầu, không phụ thuộc độ dài bài.
"""

from __future__ import annotations

import math


#: Đủ cho mục lục của một bài rất dài. Bài 3 giờ đo 22/09/2026 chiếm khoảng 14 KB.
DAU_MUC_LUC = 256 * 1024


def kem_danh_sach(source: str) -> bool:
    """Tiếng và hình YouTube có kèm danh sách khúc.

    Hai nguồn này là MP4 cắt mảnh, đo 22/09/2026. Zing, Facebook và loa giữ
    tệp liền. Không có ``sidx`` thì đường danh sách trả lỗi, người gọi dùng
    lại tệp — không đoán thêm nguồn nào khác.
    """
    return source in {"youtube", "youtube_video"}


def url_khuc_tuong_doi(token: str, signed_path: str) -> str:
    """Địa chỉ mảnh, tương đối so với đường ``…/{token}.m3u8``.

    Giữ nguyên chữ ký của đường tệp liền (không có ``.m3u8``) và thêm ``khoi=1``
    để lời xin mảnh không bị hiểu thành một danh sách mới.
    """
    query = signed_path.split("?", 1)[1]
    return f"{token}?{query}&khoi=1"


def doc_muc_luc_mp4(buf: bytes) -> tuple[int, list[tuple[int, int, float]]] | None:
    """(độ dài đoạn mở đầu, các khúc ``(offset, độ dài, giây)``) hoặc None.

    None khi không có ``sidx`` đủ trong ``buf``, hoặc một mảnh trỏ tới mục lục
    khác chứ không phải tiếng.
    """
    i = 0
    sidx: tuple[int, int] | None = None
    while i + 8 <= len(buf):
        size = int.from_bytes(buf[i:i + 4], "big")
        typ = buf[i + 4:i + 8]
        hdr = 8
        if size == 1:
            if i + 16 > len(buf):
                return None
            size = int.from_bytes(buf[i + 8:i + 16], "big")
            hdr = 16
        if size < hdr or i + size > len(buf):
            return None
        if typ == b"sidx":
            sidx = (i, size)
            break
        i += size
    if sidx is None:
        return None
    dau, size = sidx
    p = dau + (16 if int.from_bytes(buf[dau:dau + 4], "big") == 1 else 8)
    if p + 4 > dau + size:
        return None
    ver = buf[p]
    p += 4  # version + flags
    if p + 8 > dau + size:
        return None
    p += 4  # reference_ID
    timescale = int.from_bytes(buf[p:p + 4], "big")
    p += 4
    if timescale <= 0:
        return None
    if ver == 0:
        if p + 8 > dau + size:
            return None
        p += 4  # earliest_presentation_time
        first_offset = int.from_bytes(buf[p:p + 4], "big")
        p += 4
    else:
        if p + 16 > dau + size:
            return None
        p += 8
        first_offset = int.from_bytes(buf[p:p + 8], "big")
        p += 8
    if p + 4 > dau + size:
        return None
    p += 2  # reserved
    count = int.from_bytes(buf[p:p + 2], "big")
    p += 2
    if count <= 0 or p + count * 12 > dau + size:
        return None
    khuc: list[tuple[int, int, float]] = []
    vi_tri = dau + size + first_offset
    for _ in range(count):
        tu = int.from_bytes(buf[p:p + 4], "big")
        dai = tu & 0x7FFFFFFF
        if tu >> 31:
            return None
        giay_don = int.from_bytes(buf[p + 4:p + 8], "big")
        p += 12
        if dai <= 0:
            return None
        khuc.append((vi_tri, dai, giay_don / timescale))
        vi_tri += dai
    return dau, khuc


def danh_sach_hls(khoi_dai: int, khuc: list[tuple[int, int, float]], url_khuc: str) -> str:
    """Danh sách HLS: đoạn mở đầu một lần, rồi từng khúc theo byte."""
    if khoi_dai < 8 or not khuc or not url_khuc:
        raise ValueError("danh_sach_hls_rong")
    muc = max(1, math.ceil(max(giay for _, _, giay in khuc) - 1e-6))
    dong = [
        "#EXTM3U",
        "#EXT-X-VERSION:7",
        f"#EXT-X-TARGETDURATION:{muc}",
        "#EXT-X-PLAYLIST-TYPE:VOD",
        "#EXT-X-MEDIA-SEQUENCE:0",
        f'#EXT-X-MAP:URI="{url_khuc}",BYTERANGE="{khoi_dai}@0"',
    ]
    for bat_dau, dai, giay in khuc:
        dong.append(f"#EXTINF:{giay:.3f},")
        dong.append(f"#EXT-X-BYTERANGE:{dai}@{bat_dau}")
        dong.append(url_khuc)
    dong.append("#EXT-X-ENDLIST")
    return "\n".join(dong) + "\n"
