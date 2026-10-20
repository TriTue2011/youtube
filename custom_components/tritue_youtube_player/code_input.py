"""Làm sạch mã người dùng dán vào ô action (``playlist_code`` / ``queue_code``).

Nút sao chép trên thẻ chép nguyên MỘT DÒNG YAML (``queue_code: media_player.loa``) để dán vào trình soạn YAML; dán cả dòng đó vào
ô «Mã hàng đợi» của giao diện action thì giá trị thành ``queue_code: media_player.loa`` và bị từ chối («Mã hàng đợi không hợp lệ»).
Hàm thuần (không import Home Assistant) nên chạy được trong test đơn vị.
"""

from __future__ import annotations

from typing import Any

_QUOTES = "\"'`“”‘’"


def clean_code(value: Any, *labels: str) -> str:
    """Bỏ khoảng trắng, dấu nháy bao quanh và nhãn ``<label>:`` ở đầu (không phân biệt hoa/thường).

    Chỉ gỡ NHÃN ĐÚNG TÊN trường được truyền vào (``labels``), không đoán nhãn khác; còn lại giữ nguyên để lớp kiểm khuôn phía sau
    quyết định hợp lệ hay không. Lặp tới khi ổn định để chịu được ``'queue_code: "media_player.x"'``.
    """
    text = str(value or "").strip()
    wanted = tuple(f"{label.lower()}:" for label in labels)
    while True:
        before = text
        text = text.strip().strip(_QUOTES).strip()
        lowered = text.lower()
        for label in wanted:
            if lowered.startswith(label):
                text = text[len(label):]
                break
        if text == before:
            return text
