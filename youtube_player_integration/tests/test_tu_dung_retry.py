"""Bug tự dừng sau 2-3 bài / 10-15 phút: _async_advance phải retry lỗi tạm thời.

Trước sửa: bắt HomeAssistantError chỉ log warning rồi bỏ cuộc → nhạc dừng vĩnh viễn
khi YouTube throttle/429 lúc yt-dlp extract bài kế.
Sau sửa: lỗi tạm thời → thử lại với chờ tăng dần; lỗi vĩnh viễn (video bị xoá)
→ bỏ qua bài, chuyển bài kế; hết retry → báo người dùng qua persistent_notification.
"""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

import custom_components.tritue_youtube_player.advance as advance_mod
from custom_components.tritue_youtube_player.api import (
    CannotConnectError,
    InvalidTargetError,
    YouTubePlayerApiError,
)


def loi_tam_thoi():
    err = ServiceValidationError("playback_error")
    err.__cause__ = YouTubePlayerApiError("stream_unavailable")
    return err


def loi_vinh_vien():
    err = ServiceValidationError("invalid_target")
    err.__cause__ = InvalidTargetError("invalid_youtube_target")
    return err


class PhanLoaiLoiTests(unittest.TestCase):
    def test_mat_mang_la_tam_thoi(self):
        self.assertEqual("tam_thoi", advance_mod._loai_loi_tu_dong_chuyen(CannotConnectError("cannot_connect")))

    def test_throttle_502_la_tam_thoi(self):
        self.assertEqual("tam_thoi", advance_mod._loai_loi_tu_dong_chuyen(loi_tam_thoi()))

    def test_video_khong_ton_tai_la_vinh_vien(self):
        self.assertEqual("vinh_vien", advance_mod._loai_loi_tu_dong_chuyen(loi_vinh_vien()))

    def test_het_hang_doi_la_het(self):
        err = ServiceValidationError(translation_domain="tritue_youtube_player", translation_key="queue_end")
        self.assertEqual("het", advance_mod._loai_loi_tu_dong_chuyen(err))

    def test_loi_khong_ro_nguyen_nhan_mac_dinh_tam_thoi(self):
        # Throttle lúc extract là ca phổ biến nhất của tự dừng → mặc định thử lại.
        self.assertEqual("tam_thoi", advance_mod._loai_loi_tu_dong_chuyen(HomeAssistantError("playback_error")))


class TuDongChuyenRetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass = types.SimpleNamespace(
            services=types.SimpleNamespace(async_call=AsyncMock()),
            data={},
        )
        self.entry = types.SimpleNamespace(
            entry_id="entry_1",
            runtime_data=types.SimpleNamespace(data={}),
        )
        self.adv = advance_mod.SessionAutoAdvance(self.hass, self.entry)
        self.session = {"session_id": "s1", "output_entity_ids": ["media_player.a"]}
        # Ép đi đường session để gọi async_skip (đường queue pop bài trước khi phát).
        self.patch_next = patch.object(self.adv, "_next_from", return_value="session")
        self.patch_next.start()
        self.addCleanup(self.patch_next.stop)
        # Không chờ thật giữa các lần thử.
        self.patch_wait = patch.object(advance_mod, "CHO_GIUA_CAC_LAN_THU_GIAY", (0, 0, 0))
        self.patch_wait.start()
        self.addCleanup(self.patch_wait.stop)

    async def test_loi_tam_thoi_thu_lai_den_khi_thanh_cong(self):
        skip = AsyncMock(side_effect=[loi_tam_thoi(), loi_tam_thoi(), None])
        with patch("custom_components.tritue_youtube_player.services.async_skip", skip):
            await self.adv._async_advance(self.session)
        self.assertEqual(3, skip.await_count)
        # Tự phục hồi thì không làm phiền người dùng.
        self.hass.services.async_call.assert_not_called()
        self.assertNotIn("s1", self.adv._advancing)

    async def test_loi_tam_thoi_het_retry_thi_bao_nguoi_dung(self):
        skip = AsyncMock(side_effect=loi_tam_thoi())
        with patch("custom_components.tritue_youtube_player.services.async_skip", skip):
            await self.adv._async_advance(self.session)
        # 1 lần đầu + 3 lần thử lại.
        self.assertEqual(4, skip.await_count)
        self.hass.services.async_call.assert_awaited_once()
        args = self.hass.services.async_call.await_args
        self.assertEqual(("persistent_notification", "create"), args[0][:2])
        self.assertIn("s1", args[0][2]["notification_id"])
        self.assertNotIn("s1", self.adv._advancing)

    async def test_loi_vinh_vien_bo_qua_khong_thu_lai(self):
        skip = AsyncMock(side_effect=[loi_vinh_vien(), loi_vinh_vien(), None])
        with patch("custom_components.tritue_youtube_player.services.async_skip", skip):
            await self.adv._async_advance(self.session)
        # Không chờ giữa các lần (bỏ qua ngay), không báo user khi tự qua được.
        self.assertEqual(3, skip.await_count)
        self.hass.services.async_call.assert_not_called()

    async def test_loi_vinh_vien_lien_tuc_thi_bao_va_dung(self):
        skip = AsyncMock(side_effect=loi_vinh_vien())
        with patch("custom_components.tritue_youtube_player.services.async_skip", skip):
            await self.adv._async_advance(self.session)
        self.assertEqual(advance_mod.BO_QUA_VINH_VIEN_TOI_DA, skip.await_count)
        self.hass.services.async_call.assert_awaited_once()
        args = self.hass.services.async_call.await_args
        self.assertEqual(("persistent_notification", "create"), args[0][:2])

    async def test_het_hang_doi_khong_retry_khong_bao(self):
        err = ServiceValidationError(translation_domain="tritue_youtube_player", translation_key="queue_end")
        skip = AsyncMock(side_effect=err)
        with patch("custom_components.tritue_youtube_player.services.async_skip", skip):
            await self.adv._async_advance(self.session)
        self.assertEqual(1, skip.await_count)
        self.hass.services.async_call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
