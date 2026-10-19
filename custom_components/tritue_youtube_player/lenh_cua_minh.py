"""Ghi lại các lệnh phát do CHÍNH tích hợp gửi cho từng loa, để không nhầm hậu quả của chúng với Stop hay luồng cắt.

Chủ máy 19/10/2026 23:37: bấm Next ở giây thứ 9 của bài đầu playlist → loa d50s thoáng về `idle` rồi mới phát bài mới; bộ theo dõi
thấy `idle` sớm và gỡ loa khỏi phiên → phiên chết sau 11 giây. Loa nào cũng có thể có khoảng `idle` ngắn giữa hai bài khi nhận lệnh
phát mới, nên `idle` của một loa trong KHOANG_GIAY giây sau lệnh của tích hợp là chuyển bài, không phải ai đó dừng nhạc.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util

#: Sau lệnh phát cuối cùng gửi cho một loa, `idle` của loa đó (giây) được coi là chuyển bài. Loa chậm (nạp luồng, đổi nguồn) cần chừng này.
KHOANG_GIAY = 20
#: Số loa tối đa được nhớ cùng lúc; đầy thì bỏ mục cũ nhất để bản đồ không phình theo thời gian.
TOI_DA = 256

_HET_HAN: dict[str, datetime] = {}


def danh_dau(entity_ids: Iterable[str], now: datetime | None = None) -> None:
    """Ghi rằng tích hợp vừa (đang) gửi lệnh phát cho các loa này."""
    now = now or dt_util.utcnow()
    han = now + timedelta(seconds=KHOANG_GIAY)
    for entity_id in entity_ids:
        _HET_HAN[str(entity_id)] = han
    for entity_id in [e for e, h in _HET_HAN.items() if h <= now]:
        del _HET_HAN[entity_id]
    while len(_HET_HAN) > TOI_DA:
        del _HET_HAN[min(_HET_HAN, key=_HET_HAN.get)]


def con_lai_giay(entity_id: str, now: datetime | None = None) -> float:
    """Số giây còn lại của khoảng «vừa nhận lệnh phát» của loa; 0 nếu không còn."""
    now = now or dt_util.utcnow()
    han = _HET_HAN.get(str(entity_id))
    return max(0.0, (han - now).total_seconds()) if han else 0.0


def so_muc() -> int:
    return len(_HET_HAN)


def xoa() -> None:
    _HET_HAN.clear()
