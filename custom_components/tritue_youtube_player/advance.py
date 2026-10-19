"""Server-side auto-advance: the next song plays even with every browser closed.

Before 0.9 the card advanced the queue, so closing the dashboard stopped the
music after the current song. Home Assistant sees the speakers' states, so the
integration now watches the speaker leading each session it started and, when
that speaker finishes the track, plays the session's next queue item on the
same speakers.
"""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import LOGGER
from .queue_store import get_queue_store
from .playback import build_target_capabilities, is_native_youtube_transport
from .sessions import active_sessions, is_controlled_by, observe_interruption, observe_track, queue_item, session_queue_key

#: Chờ giữa các lần thử lại lỗi tạm thời khi tự chuyển bài (giây): 2s, 5s, 10s.
CHO_GIUA_CAC_LAN_THU_GIAY = (2, 5, 10)
#: Bỏ qua tối đa N bài lỗi vĩnh viễn liên tiếp trước khi dừng và báo người dùng.
BO_QUA_VINH_VIEN_TOI_DA = 5


def _loai_loi_tu_dong_chuyen(error: BaseException) -> str:
    """Phân loại lỗi tự chuyển bài: 'tam_thoi' | 'vinh_vien' | 'het'.

    - 'tam_thoi': 429/throttle/timeout/mất mạng → thử lại với chờ tăng dần.
    - 'vinh_vien': video bị xoá/không tồn tại/target không hợp lệ → bỏ qua bài, chuyển bài kế.
    - 'het': hết hàng đợi/phiên không còn → không phải lỗi, dừng êm.
    """
    from .api import CannotConnectError, InvalidTargetError  # noqa: PLC0415

    da_thay: set[int] = set()
    xau: BaseException | None = error
    while xau is not None and id(xau) not in da_thay:
        da_thay.add(id(xau))
        if isinstance(xau, CannotConnectError):
            return "tam_thoi"
        if isinstance(xau, InvalidTargetError):
            return "vinh_vien"
        xau = xau.__cause__ or xau.__context__
    khoa = getattr(error, "translation_key", None)
    if khoa in ("queue_end", "session_not_found"):
        return "het"
    if khoa == "invalid_target":
        return "vinh_vien"
    # playback_error và các lỗi HA khác: mặc định coi là tạm thời vì throttle
    # lúc yt-dlp extract là ca phổ biến nhất của tự dừng sau 2-3 bài.
    return "tam_thoi"


class SessionAutoAdvance:
    """Watch each session's lead speaker and play its next track at the end."""

    def __init__(self, hass: HomeAssistant, entry: Any) -> None:
        self.hass = hass
        self.entry = entry
        self._trackers: dict[tuple, dict[str, Any]] = {}
        self._watched: frozenset[str] = frozenset()
        self._unsub_states = None
        self._advancing: set[str] = set()

    @callback
    def async_start(self):
        unsub_coordinator = self.entry.runtime_data.async_add_listener(self._async_sessions_changed)
        self._async_sessions_changed()

        @callback
        def stop() -> None:
            unsub_coordinator()
            if self._unsub_states:
                self._unsub_states()
                self._unsub_states = None

        return stop

    def _sessions(self) -> list[dict[str, Any]]:
        # Máy phát không trả lời: coordinator vẫn giữ dữ liệu LẦN CUỐI → phiên «ma» — TTS dứt là tự phát lại bài của
        # một máy phát đã dừng (chủ máy 06/10/2026). Không trả lời = không điều khiển phiên nào.
        if not self.entry.runtime_data.last_update_success:
            return []
        return [
            session
            for session in active_sessions(self.entry.runtime_data.data)
            if is_controlled_by(session, self.entry.entry_id)
            and session.get("auto_advance", True) is not False
        ]

    def _lead_speaker(self, session: dict[str, Any]) -> str | None:
        """First speaker that plays the stream itself: native YouTube apps on
        TVs keep playing inside the app and never report the end."""
        source = str((session.get("item") or {}).get("source") or "")
        registry = er.async_get(self.hass)
        for entity_id in session.get("output_entity_ids") or []:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            registry_entry = registry.async_get(entity_id)
            capability = build_target_capabilities(
                target_platform=registry_entry.platform if registry_entry else None,
                target_device_class=state.attributes.get("device_class"),
                supported_features=int(state.attributes.get("supported_features") or 0),
            )
            if source == "youtube" and is_native_youtube_transport(capability["transport"]):
                continue
            return entity_id
        return None

    @staticmethod
    def _track_key(session: dict[str, Any], entity_id: str) -> tuple:
        item = session.get("item") or {}
        queue = session.get("queue") or {}
        return (session.get("session_id"), item.get("id"), queue.get("index"), entity_id)

    @callback
    def _async_sessions_changed(self) -> None:
        leads = {lead for session in self._sessions() if (lead := self._lead_speaker(session))}
        watched = frozenset(leads)
        if watched != self._watched:
            if self._unsub_states:
                self._unsub_states()
                self._unsub_states = None
            if watched:
                self._unsub_states = async_track_state_change_event(
                    self.hass, list(watched), self._async_state_changed
                )
            self._watched = watched
        live = {self._track_key(s, lead) for s in self._sessions() if (lead := self._lead_speaker(s))}
        self._trackers = {key: value for key, value in self._trackers.items() if key in live}
        for session in self._sessions():
            lead = self._lead_speaker(session)
            if lead and (state := self.hass.states.get(lead)):
                self._observe(session, lead, state.state, dict(state.attributes))

    @callback
    def _async_state_changed(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        if new_state is None:
            return
        for session in self._sessions():
            if self._lead_speaker(session) == new_state.entity_id:
                self._observe(session, new_state.entity_id, new_state.state, dict(new_state.attributes))

    @callback
    def _observe(self, session: dict[str, Any], entity_id: str, state: str, attributes: dict[str, Any]) -> None:
        tracker = self._trackers.setdefault(self._track_key(session, entity_id), {})
        now = dt_util.utcnow()
        # TTS / thông báo chen giữa bài: đọc xong thì phát tiếp đúng chỗ, và KHÔNG coi TTS dứt là hết bài.
        tiep = observe_interruption(tracker, state, attributes, now, session.get("item"))
        if tiep is not None:
            session_id = str(session.get("session_id") or "")
            if session_id not in self._advancing:
                self._advancing.add(session_id)
                self.hass.async_create_task(self._async_resume(session, entity_id, tiep), eager_start=False)
            return
        if "chen_tu" in tracker:
            return
        if not observe_track(tracker, state, attributes, now, session.get("item")):
            if tracker.pop("dung_som", False):
                # Stop pressed on the speaker (idle well before the end): take that speaker out of the session instead
                # of skipping to the next song (issue #3). A one-speaker session ends.
                self.hass.async_create_task(self._async_remove_speaker(session, entity_id), eager_start=False)
            return
        session_id = str(session.get("session_id") or "")
        if session_id in self._advancing or self._next_from(session) is None:
            return
        self._advancing.add(session_id)
        self.hass.async_create_task(self._async_advance(session), eager_start=False)

    def _next_from(self, session: dict[str, Any]) -> str | None:
        """Where the next song comes from: the bound Queue of the session
        or first speaker while it has songs left, then the session's own queue."""
        queue_key = session_queue_key(session)
        if not queue_key:
            outputs = session.get("output_entity_ids") or []
            if outputs:
                queue_key = outputs[0]
        if queue_key and get_queue_store(self.hass).has_next(queue_key):
            return "queue"
        if queue_item(session, 1) is not None:
            return "session"
        return None

    async def _async_remove_speaker(self, session: dict[str, Any], entity_id: str) -> None:
        from .services import async_remove_players  # noqa: PLC0415

        try:
            LOGGER.info("Session %s: %s stopped before the end of the song — removing it from the session",
                        session.get("session_id"), entity_id)
            await async_remove_players(self.hass, self.entry, [entity_id])
        except HomeAssistantError as error:
            LOGGER.warning("Removing %s from session %s failed: %s", entity_id, session.get("session_id"), error)

    async def _async_resume(self, session: dict[str, Any], lead: str, position: float) -> None:
        """Phát lại bài của phiên trên các loa của nó rồi tua tới ``position`` (loa nào có SEEK)."""
        from .services import _async_play_session_item  # noqa: PLC0415

        session_id = str(session.get("session_id") or "")
        item = session.get("item") or {}
        try:
            LOGGER.info("Session %s interrupted on %s (TTS/announcement) — resuming at %.0f s",
                        session_id, lead, position)
            await _async_play_session_item(self.hass, self.entry, session, item)
            await self._async_seek_when_playing(session, lead, position)
        except HomeAssistantError as error:
            LOGGER.warning("Resuming session %s after an interruption failed: %s", session_id, error)
        finally:
            self._advancing.discard(session_id)

    async def _async_seek_when_playing(self, session: dict[str, Any], lead: str, position: float) -> None:
        """Chờ loa dẫn phát lại (theo SỰ KIỆN đổi trạng thái, tối đa 15 s) rồi tua mọi loa của phiên có SEEK tới
        ``position``."""
        import asyncio  # noqa: PLC0415

        from .sessions import PLAYING_STATES  # noqa: PLC0415

        if position < 3:
            return
        state = self.hass.states.get(lead)
        if state is None or state.state not in PLAYING_STATES:
            da_phat: asyncio.Future = self.hass.loop.create_future()

            @callback
            def _doi(event: Event[EventStateChangedData]) -> None:
                new_state = event.data["new_state"]
                if new_state is not None and new_state.state in PLAYING_STATES and not da_phat.done():
                    da_phat.set_result(None)

            unsub = async_track_state_change_event(self.hass, [lead], _doi)
            try:
                await asyncio.wait_for(da_phat, 15)
            except TimeoutError:
                LOGGER.debug("Resume: %s did not start playing again, not seeking", lead)
                return
            finally:
                unsub()
        seek = [
            entity_id for entity_id in session.get("output_entity_ids") or []
            if (st := self.hass.states.get(entity_id)) is not None
            and int(st.attributes.get("supported_features") or 0) & 2
        ]
        LOGGER.debug("Resume: %s playing again, seeking %s to %.0f s", lead, seek, position)
        if seek:
            await self.hass.services.async_call(
                "media_player", "media_seek", {"entity_id": seek, "seek_position": round(position)}, blocking=True)

    async def _async_advance(self, session: dict[str, Any]) -> None:
        # services imports HA actions lazily
        from .services import async_play_queue_next, async_skip  # noqa: PLC0415

        session_id = str(session.get("session_id") or "")
        try:
            await self._async_chuyen_bai_co_thu_lai(session, async_play_queue_next, async_skip)
        finally:
            self._advancing.discard(session_id)

    async def _async_chuyen_bai(self, session: dict[str, Any], fn_queue_next, fn_skip) -> None:
        """Chuyển sang bài kế một lần (không thử lại)."""
        if self._next_from(session) == "queue":
            await fn_queue_next(self.hass, self.entry, session)
        else:
            await fn_skip(self.hass, self.entry, session.get("session_id"), 1)

    async def _async_chuyen_bai_co_thu_lai(
        self, session: dict[str, Any], fn_queue_next, fn_skip
    ) -> None:
        """Tự chuyển bài có phân loại lỗi (sửa bug tự dừng sau 2-3 bài).

        - Lỗi tạm thời (YouTube throttle/429 lúc extract, mất mạng): thử lại với
          chờ tăng dần. Lưu ý đường queue đã pop bài trước khi phát nên "thử lại"
          thực chất là thử bài kế — vẫn tốt hơn dừng hẳn.
        - Lỗi vĩnh viễn (video bị xoá/không tồn tại): bỏ qua bài ngay, chuyển bài kế.
        - Hết hàng đợi: dừng êm, không báo.
        Hết retry hoặc quá nhiều bài lỗi vĩnh viễn liên tiếp → báo người dùng qua
        persistent_notification thay vì im lặng như trước.
        """
        session_id = str(session.get("session_id") or "")
        bo_qua_vinh_vien = 0
        loi_cho_xu_ly: HomeAssistantError | None = None
        while True:
            try:
                if loi_cho_xu_ly is not None:
                    raise loi_cho_xu_ly
                await self._async_chuyen_bai(session, fn_queue_next, fn_skip)
                return
            except HomeAssistantError as error:
                loi_cho_xu_ly = None
                loai = _loai_loi_tu_dong_chuyen(error)
                if loai == "het":
                    LOGGER.debug("Auto-advance of session %s: hết hàng đợi, dừng êm", session_id)
                    return
                if loai == "vinh_vien":
                    bo_qua_vinh_vien += 1
                    if bo_qua_vinh_vien >= BO_QUA_VINH_VIEN_TOI_DA:
                        LOGGER.error(
                            "Auto-advance of session %s: %d bài lỗi vĩnh viễn liên tiếp — dừng",
                            session_id, bo_qua_vinh_vien)
                        await self._async_bao_loi_nguoi_dung(
                            session_id,
                            f"Tự chuyển bài dừng: {bo_qua_vinh_vien} bài liên tiếp không phát được "
                            "(video có thể đã bị xoá hoặc không tồn tại).")
                        return
                    LOGGER.warning(
                        "Auto-advance of session %s: bỏ qua bài lỗi vĩnh viễn (%s), chuyển bài kế (%d/%d)",
                        session_id, error, bo_qua_vinh_vien, BO_QUA_VINH_VIEN_TOI_DA)
                    continue
                # loai == "tam_thoi"
                loi_cuoi = await self._async_thu_lai_tam_thoi(
                    session, fn_queue_next, fn_skip, session_id, error)
                if loi_cuoi is None:
                    return
                if _loai_loi_tu_dong_chuyen(loi_cuoi) == "tam_thoi":
                    LOGGER.error(
                        "Auto-advance of session %s: vẫn lỗi sau %d lần thử (%s) — dừng",
                        session_id, len(CHO_GIUA_CAC_LAN_THU_GIAY), loi_cuoi)
                    await self._async_bao_loi_nguoi_dung(
                        session_id,
                        "Tự chuyển bài dừng: máy phát nhạc không trả lời sau nhiều lần thử "
                        f"({loi_cuoi}). Hãy thử phát lại.")
                    return
                # Lỗi đổi loại trong lúc thử lại → vòng lặp phân loại lại từ đầu.
                loi_cho_xu_ly = loi_cuoi

    async def _async_thu_lai_tam_thoi(
        self, session: dict[str, Any], fn_queue_next, fn_skip,
        session_id: str, loi_dau: HomeAssistantError,
    ) -> HomeAssistantError | None:
        """Thử lại lỗi tạm thời với chờ tăng dần.

        Trả None nếu một lần thử thành công; ngược lại trả lỗi cuối cùng
        (có thể đã đổi loại — để vòng ngoài phân loại lại).
        """
        loi = loi_dau
        for lan, cho_giay in enumerate(CHO_GIUA_CAC_LAN_THU_GIAY, start=1):
            LOGGER.warning(
                "Auto-advance of session %s thất bại (lần thử %d/%d): %s — thử lại sau %d giây",
                session_id, lan, len(CHO_GIUA_CAC_LAN_THU_GIAY), loi, cho_giay)
            await asyncio.sleep(cho_giay)
            try:
                await self._async_chuyen_bai(session, fn_queue_next, fn_skip)
            except HomeAssistantError as loi_moi:
                if _loai_loi_tu_dong_chuyen(loi_moi) != "tam_thoi":
                    return loi_moi
                loi = loi_moi
            else:
                LOGGER.info(
                    "Auto-advance of session %s: thử lại lần %d thành công", session_id, lan)
                return None
        return loi

    async def _async_bao_loi_nguoi_dung(self, session_id: str, thong_bao: str) -> None:
        """Báo cho người dùng qua persistent notification (không im lặng như trước)."""
        try:
            await self.hass.services.async_call(
                "persistent_notification", "create",
                {"title": "TriTue YouTube Player",
                 "message": thong_bao,
                 "notification_id": f"tritue_youtube_advance_{session_id}"},
                blocking=False,
            )
        except Exception as error:  # noqa: BLE001 — báo lỗi không được làm hỏng luồng chính
            LOGGER.warning(
                "Không gửi được thông báo tự chuyển bài cho phiên %s: %s", session_id, error)
