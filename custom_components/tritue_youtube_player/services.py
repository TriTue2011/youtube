"""Home Assistant actions exposed by TriTue YouTube Player."""

from __future__ import annotations

import asyncio
import re
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .actions import async_play_on_players
from .dung_loa import async_dung_chac, async_dung_loa_luong
from .api import InvalidTargetError, YouTubePlayerApiError
from . import dong_bo, lenh_cua_minh
from .queue_store import get_queue_store
from .const import (
    CONF_ENTRY_ID,
    CONF_MEDIA_CONTENT_TYPE,
    CONF_SOURCE,
    CONF_TARGET,
    CONF_VOLUME_LEVEL,
    DOMAIN,
    SERVICE_PLAY_ON_PLAYERS,
    SERVICE_PLAY_PLAYLIST,
    SERVICE_PLAY_QUEUE,
    SERVICE_REMOVE_PLAYERS,
    SERVICE_SET_SYNC_ADJUST,
    SERVICE_SKIP,
    SERVICE_STOP_SESSION,
    LOGGER,
)
from .playback import (
    CHON_MODE_HOP_LE,
    UnsupportedCastMediaError,
    UnsupportedTargetMediaError,
    async_play_queue,
    normalize_target_entity_ids,
)
from .queue import QUEUE_KEY
from .code_input import clean_code
from .share_codes import async_playlist_id_from_code
from .sessions import (
    active_sessions,
    attach_session_queue,
    controller_id,
    detach_session_queue,
    find_session,
    item_target,
    queue_item,
    session_queue_key,
)

CONF_SESSION_ID = "session_id"
CONF_JOIN = "join"
CONF_PLAYLIST_ID = "playlist_id"
CONF_STEP = "step"
STOP_FEATURE = 4096


PLAY_ON_PLAYERS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTRY_ID): cv.string,
        vol.Required(CONF_SOURCE): vol.In({"youtube", "zing", "facebook", "http"}),
        vol.Required(CONF_TARGET): cv.string,
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(CONF_MEDIA_CONTENT_TYPE): cv.string,
        vol.Optional(CONF_VOLUME_LEVEL): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=1)
        ),
        vol.Optional(CONF_SESSION_ID): cv.string,
        vol.Optional(CONF_JOIN, default=False): cv.boolean,
        vol.Optional(CONF_PLAYLIST_ID): cv.string,
        vol.Optional("mode"): vol.In(CHON_MODE_HOP_LE),
    }
)
PLAY_PLAYLIST_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTRY_ID): cv.string,
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required("playlist_code"): cv.string,
        vol.Optional(CONF_VOLUME_LEVEL): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=1)
        ),
        vol.Optional("mode"): vol.In(CHON_MODE_HOP_LE),
    }
)
PLAY_QUEUE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTRY_ID): cv.string,
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional("queue_code"): cv.string,
        vol.Optional(CONF_VOLUME_LEVEL): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=1)
        ),
        vol.Optional("mode"): vol.In(CHON_MODE_HOP_LE),
    }
)
SKIP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTRY_ID): cv.string,
        vol.Optional(CONF_SESSION_ID): cv.string,
        vol.Optional(CONF_STEP, default=1): vol.All(vol.Coerce(int), vol.In([-1, 1])),
    }
)
STOP_SESSION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTRY_ID): cv.string,
        vol.Optional(CONF_SESSION_ID): cv.string,
    }
)
REMOVE_PLAYERS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTRY_ID): cv.string,
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    }
)


SET_SYNC_ADJUST_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTRY_ID): cv.string,
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required("adjust_ms"): vol.All(vol.Coerce(int), vol.Range(min=-10000, max=10000)),
    }
)


def _validation_error(key: str) -> ServiceValidationError:
    return ServiceValidationError(translation_domain=DOMAIN, translation_key=key)


def _loaded_entry_or_raise(hass: HomeAssistant, entry_id: str):
    entry = hass.config_entries.async_get_entry(entry_id)
    if (
        entry is None
        or entry.domain != DOMAIN
        or entry.state is not ConfigEntryState.LOADED
    ):
        raise _validation_error("entry_unavailable")
    return entry


def _virtual_players(hass: HomeAssistant, entry) -> set[str]:
    registry = er.async_get(hass)
    return {
        registry_entry.entity_id
        for registry_entry in registry.entities.values()
        if registry_entry.config_entry_id == entry.entry_id
        and registry_entry.domain == "media_player"
    }


def _dong_bo_nen(hass: HomeAssistant, entry, entity_ids: list[str], join_entity_ids: list[str] | None,
                 item: dict | None = None) -> None:
    """Nhiều loa cùng phát (hoặc loa mới vào phiên đang phát): kéo các loa về CÙNG VỊ TRÍ của loa chuẩn (xem dong_bo.py).
    Tắt bằng tuỳ chọn ``dong_bo: false`` của mục cấu hình; chỉnh tay từng loa bằng ``dong_bo_adjust_ms`` {entity_id: ms};
    ``dong_bo_chu_ky_s`` (mặc định 90, 0 = chỉ căn một lần) là chu kỳ kiểm trôi khi đang phát."""
    tuy_chon = getattr(entry, "options", None) or {}
    if not tuy_chon.get("dong_bo", True):
        return
    if join_entity_ids:                      # loa mới vào: loa chuẩn là loa ĐANG phát trong phiên
        followers = [e for e in entity_ids if e not in join_entity_ids]
        master = next((e for e in join_entity_ids if e not in followers), None)
    elif len(entity_ids) > 1:
        master, followers = entity_ids[0], list(entity_ids[1:])
    else:
        return
    if master is None or not followers:
        return
    adjust = {str(k): int(v) for k, v in (tuy_chon.get("dong_bo_adjust_ms") or {}).items()
              if isinstance(v, (int, float)) and not isinstance(v, bool)}
    try:
        chu_ky = float(tuy_chon.get("dong_bo_chu_ky_s", dong_bo.CHU_KY_DINH_KY_MAC_DINH_S))
    except (TypeError, ValueError):
        chu_ky = dong_bo.CHU_KY_DINH_KY_MAC_DINH_S
    dong_bo.len_lich(entry, hass, master, followers, adjust_ms=adjust, chu_ky_s=chu_ky, item=item)


async def async_dispatch(
    hass: HomeAssistant,
    entry,
    *,
    source: str,
    target: str,
    entity_ids: list[str],
    volume_level: float | None = None,
    media_content_type: str | None = None,
    session_id: str | None = None,
    join_entity_ids: list[str] | None = None,
    playlist_id: str | None = None,
    mode: str | None = None,
    giu_phien_khi_loi: bool = False,
) -> dict:
    """Play one item on physical players as one session controlled by ``entry``.

    Shared by the play/skip actions, server-side auto-advance and Assist.
    ``giu_phien_khi_loi`` (NV202): tự chuyển bài thất bại thì giữ phiên để
    thử bài kế, không dọn phiên như đường phát trực tiếp."""
    excluded = _virtual_players(hass, entry)
    try:
        entity_ids = normalize_target_entity_ids(entity_ids, excluded=excluded)
    except ValueError as error:
        raise _validation_error("invalid_target_entities") from error

    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        if state is None or state.state == STATE_UNAVAILABLE:
            raise _validation_error("target_unavailable")

    registry = er.async_get(hass)
    platforms = {}
    device_classes = {}
    supported_features = {}
    for entity_id in entity_ids:
        registry_entry = registry.async_get(entity_id)
        platforms[entity_id] = registry_entry.platform if registry_entry else None
        state = hass.states.get(entity_id)
        device_classes[entity_id] = (
            state.attributes.get("device_class") if state else None
        )
        supported_features[entity_id] = (
            int(state.attributes.get("supported_features") or 0)
            if state
            else 0
        )

    # Ghi TRƯỚC khi gửi lệnh: loa có thể về idle thoáng qua ngay khi nhận lệnh phát mới (xem lenh_cua_minh).
    lenh_cua_minh.danh_dau(entity_ids)
    try:
        result = await async_play_on_players(
            hass,
            entry.runtime_data.client,
            source=source,
            target=target,
            entity_ids=entity_ids,
            target_platforms=platforms,
            target_device_classes=device_classes,
            target_supported_features=supported_features,
            volume_level=volume_level,
            media_content_type=media_content_type,
            excluded_entity_ids=excluded,
            session_id=session_id,
            controller=controller_id(entry.entry_id),
            join_entity_ids=join_entity_ids,
            playlist_id=playlist_id,
            mode=mode,
            giu_phien_khi_loi=giu_phien_khi_loi,
        )
        await entry.runtime_data.async_refresh()
        lenh_cua_minh.danh_dau(entity_ids)          # tính lại từ lúc lệnh XONG: loa chậm chỉ idle sau khi nhận lệnh
        phien_moi = find_session(getattr(entry.runtime_data, "data", None), (result or {}).get("session_id") or session_id)
        _dong_bo_nen(hass, entry, entity_ids, join_entity_ids, (phien_moi or {}).get("item"))
    except InvalidTargetError as error:
        raise _validation_error("invalid_target") from error
    except UnsupportedCastMediaError as error:
        raise _validation_error("cast_playlist_requires_video") from error
    except UnsupportedTargetMediaError as error:
        raise _validation_error("target_source_unsupported") from error
    except (YouTubePlayerApiError, ValueError) as error:
        raise _validation_error("playback_error") from error
    return result


async def _async_handle_play_on_players(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Resolve a selected result and play it on all requested entities."""
    entry = _loaded_entry_or_raise(hass, call.data[CONF_ENTRY_ID])
    session_id = call.data.get(CONF_SESSION_ID) or None
    join = None
    if call.data.get(CONF_JOIN) and session_id:
        # Ticking a speaker while a session plays: the new speaker gets the song,
        # the speakers already in the session keep playing undisturbed.
        session = find_session(entry.runtime_data.data, session_id)
        join = list((session or {}).get("output_entity_ids") or [])
    await async_dispatch(
        hass,
        entry,
        source=call.data[CONF_SOURCE],
        target=call.data[CONF_TARGET],
        entity_ids=call.data[ATTR_ENTITY_ID],
        volume_level=call.data.get(CONF_VOLUME_LEVEL),
        media_content_type=call.data.get(CONF_MEDIA_CONTENT_TYPE),
        session_id=session_id,
        join_entity_ids=join,
        playlist_id=call.data.get(CONF_PLAYLIST_ID) or None,
        mode=call.data.get("mode"),
    )


async def _async_handle_play_playlist(hass: HomeAssistant, call: ServiceCall) -> None:
    """Resolve a playlist by code and play it."""
    entry = _loaded_entry_or_raise(hass, call.data[CONF_ENTRY_ID])
    code = clean_code(call.data["playlist_code"], "playlist_code")
    if not code:
        raise _validation_error("invalid_playlist_code")

    # 0. Tên playlist (ngắn, dễ nhớ): `playlist_code: home`. Khớp đúng tên (không phân biệt hoa/thường); trùng tên thì bắt chọn lại
    #    bằng id 12 ký tự thay vì đoán; không khớp tên nào thì rơi xuống các nhánh bên dưới như cũ.
    if not (code.startswith("TTPL1.") or re.fullmatch(r"^[a-z0-9]{12}$", code)) and "://" not in code and "list=" not in code:
        try:
            tim = await entry.runtime_data.client.async_playlists()
            khop = [
                p for p in (tim.get("playlists") or [])
                if isinstance(p, dict) and " ".join(str(p.get("name") or "").split()).casefold() == " ".join(code.split()).casefold()
            ]
        except Exception:  # noqa: BLE001 — không tra được tên thì để các nhánh sau báo lỗi đúng như trước
            khop = []
        if len(khop) > 1:
            raise _validation_error("playlist_name_ambiguous")
        if khop:
            code = str(khop[0].get("id") or "")

    # 1. Id trong kho (12 ký tự a-z0-9) hoặc mã chia sẻ TTPL1. của nút chia sẻ trên thẻ. Mã chia sẻ được nhập vào
    #    kho MỘT lần (nhớ ánh xạ mã -> id) nên automation chạy lặp không đẻ bản trùng.
    if code.startswith("TTPL1.") or re.fullmatch(r"^[a-z0-9]{12}$", code):
        try:
            playlist_id = await async_playlist_id_from_code(hass, entry.runtime_data.client, code)
        except ValueError as err:
            key = str(err)
            raise _validation_error(
                key if key in {"invalid_playlist_code", "playlist_empty", "playlist_import_failed"} else "invalid_playlist_code"
            ) from err
        except YouTubePlayerApiError as err:
            raise _validation_error("communication_error") from err
        try:
            data = await entry.runtime_data.client.async_playlists()
        except Exception as err:
            raise _validation_error("communication_error") from err
        playlists = data.get("playlists") or []
        found = next((p for p in playlists if p.get("id") == playlist_id), None)
        if not found:
            raise _validation_error("playlist_not_found")
        items = found.get("items") or []
        if not items:
            raise _validation_error("playlist_empty")
        first = items[0]
        target = item_target(first)
        source = str(first.get("source") or "youtube")
        await async_dispatch(
            hass,
            entry,
            source=source,
            target=target,
            entity_ids=call.data[ATTR_ENTITY_ID],
            volume_level=call.data.get(CONF_VOLUME_LEVEL),
            playlist_id=playlist_id,
            mode=call.data.get("mode"),
        )
        return

    # 2. Link / id playlist YouTube: phải nhập vào kho trước (thẻ làm được, action thì không tạo bản trùng).
    if "list=" in code or code.startswith("PL"):
        raise _validation_error("youtube_playlist_not_imported")

    raise _validation_error("invalid_playlist_code")


async def _async_handle_play_queue(hass: HomeAssistant, call: ServiceCall) -> None:
    """Play the queue immediately on requested players."""
    entry = _loaded_entry_or_raise(hass, call.data[CONF_ENTRY_ID])
    # Hàng đợi DUY NHẤT cho cả nhà (0.27.19): bỏ trống = hàng đợi duy nhất; mã 12 ký tự
    # hay khoá cũ (media_player.x, device:…) đều trỏ về đúng hàng đợi đó. Loa PHÁT chọn riêng.
    raw = clean_code(call.data.get("queue_code") or "", "queue_code")
    if raw:
        queue_code = raw
    else:
        store = get_queue_store(hass)
        await store.async_load()
        queue_code = store.code
    try:
        await async_play_queue(
            hass,
            entry,
            queue_code=queue_code,
            entity_ids=call.data[ATTR_ENTITY_ID],
            volume_level=call.data.get(CONF_VOLUME_LEVEL),
            mode=call.data.get("mode"),
            dispatch_fn=async_dispatch,
        )
    except ValueError as err:
        err_msg = str(err)
        if err_msg in {"invalid_queue_code", "queue_empty"}:
            raise _validation_error(err_msg) from err
        raise


def _khoa_chuyen_bai(hass: HomeAssistant, entry) -> asyncio.Lock:
    """Một khoá cho mỗi tích hợp: Next / Previous / tự chuyển bài chạy TUẦN TỰ.

    Chủ máy 19/10/2026: «next thủ công không lỗi kể cả next 3, 4 lần liên tiếp». Hai lần bấm sát nhau mà cùng đọc ảnh chụp phiên cũ
    thì cùng tính ra «bài kế của bài hiện tại» (một lần bấm thành vô nghĩa), còn hai lệnh phát chạy chồng lên nhau làm loa nhận lệnh
    lộn xộn. Chờ khoá rồi MỚI đọc phiên: `async_dispatch` đã làm mới coordinator ở cuối mỗi lần phát nên lần sau thấy đúng bài hiện tại.
    """
    khoa = hass.data.setdefault(f"{DOMAIN}_khoa_chuyen_bai", {})
    return khoa.setdefault(entry.entry_id, asyncio.Lock())


async def async_skip(
    hass: HomeAssistant, entry, session_id: str | None, step: int,
    giu_phien_khi_loi: bool = False,
) -> dict:
    """Play the next/previous item of a session's own queue on its speakers."""
    async with _khoa_chuyen_bai(hass, entry):
        session = find_session(entry.runtime_data.data, session_id)
        if session is None:
            raise _validation_error("session_not_found")
        found = queue_item(session, step)
        if found is None:
            raise _validation_error("queue_end")
        _, item = found
        return await _async_play_session_item(
            hass, entry, session, item, giu_phien_khi_loi=giu_phien_khi_loi)


async def async_play_queue_next(hass: HomeAssistant, entry, session: dict) -> dict:
    """Play the next song of the Queue on its speakers."""
    async with _khoa_chuyen_bai(hass, entry):
        queue_key = session_queue_key(session)
        if not queue_key:
            outputs = list(session.get("output_entity_ids") or [])
            if outputs:
                queue_key = outputs[0]
        if not queue_key:
            raise _validation_error("queue_end")
        item = await get_queue_store(hass).async_advance(queue_key)
        if item is None:
            raise _validation_error("queue_end")
        res = await _async_play_session_item(hass, entry, session, item)
        if res and res.get("session_id"):
            attach_session_queue(res["session_id"], queue_key)
        return res


async def _async_play_session_item(
    hass: HomeAssistant, entry, session: dict, item: dict,
    giu_phien_khi_loi: bool = False,
) -> dict:
    outputs = [
        entity_id
        for entity_id in session.get("output_entity_ids") or []
        if (state := hass.states.get(entity_id)) is not None and state.state != STATE_UNAVAILABLE
    ]
    if not outputs:
        raise _validation_error("target_unavailable")
    return await async_dispatch(
        hass,
        entry,
        source=str(item.get("source") or "youtube"),
        target=item_target(item),
        entity_ids=outputs,
        media_content_type=item.get("media_content_type"),
        session_id=session.get("session_id"),
        giu_phien_khi_loi=giu_phien_khi_loi,
    )


async def async_stop_session(hass: HomeAssistant, entry, session_id: str | None) -> None:
    """Stop a session's speakers and end the session on the player server."""
    session = find_session(entry.runtime_data.data, session_id)
    outputs = [
        entity_id
        for entity_id in (session or {}).get("output_entity_ids") or []
        if (state := hass.states.get(entity_id)) is not None
        and state.state != STATE_UNAVAILABLE
        and int(state.attributes.get("supported_features") or 0) & STOP_FEATURE
    ]
    if outputs:
        await asyncio.gather(*(async_dung_chac(hass, e, "media_stop", "Stop phiên") for e in outputs))
    da_dung = list(outputs)
    if session is None and not session_id:
        # Máy phát không còn phiên (add-on dừng / khởi động lại giữa bài) mà loa vẫn phát luồng của nó.
        da_dung += await async_dung_loa_luong(hass, ly_do="Stop: máy phát không còn phiên")
    try:
        if session and session.get("session_id"):
            await entry.runtime_data.client.async_stop(session_id=session["session_id"])
        elif session is None and session_id:
            raise _validation_error("session_not_found")
        else:
            await entry.runtime_data.client.async_stop()
    except YouTubePlayerApiError as error:
        if not da_dung:
            raise _validation_error("playback_error") from error
        LOGGER.warning("Stop: đã dừng %s nhưng máy phát không nhận lệnh dừng: %s", ", ".join(da_dung), error)
    detach_session_queue((session or {}).get("session_id") or session_id)
    await entry.runtime_data.async_refresh()


async def async_remove_players(hass: HomeAssistant, entry, entity_ids: list[str]) -> None:
    """Take speakers out of their sessions (the rest keep playing) and stop them."""
    removing = set(entity_ids)
    client = entry.runtime_data.client
    try:
        for session in active_sessions(entry.runtime_data.data):
            outputs = list(session.get("output_entity_ids") or [])
            if not removing.intersection(outputs) or not session.get("session_id"):
                continue
            await client.async_set_session_outputs(
                session["session_id"], [e for e in outputs if e not in removing]
            )
    except YouTubePlayerApiError as error:
        raise _validation_error("playback_error") from error
    stoppable = [
        entity_id
        for entity_id in entity_ids
        if (state := hass.states.get(entity_id)) is not None
        and state.state in {"playing", "paused", "buffering"}
        and int(state.attributes.get("supported_features") or 0) & STOP_FEATURE
    ]
    if stoppable:
        await asyncio.gather(*(async_dung_chac(hass, e, "media_stop", "Gỡ loa khỏi phiên") for e in stoppable))
    await entry.runtime_data.async_refresh()


def async_register_services(hass: HomeAssistant) -> None:
    """Register integration actions once for all config entries."""
    if hass.services.has_service(DOMAIN, SERVICE_PLAY_ON_PLAYERS):
        return

    async def handle(call: ServiceCall) -> None:
        await _async_handle_play_on_players(hass, call)

    async def handle_play_playlist(call: ServiceCall) -> None:
        await _async_handle_play_playlist(hass, call)

    async def handle_play_queue(call: ServiceCall) -> None:
        await _async_handle_play_queue(hass, call)

    async def handle_skip(call: ServiceCall) -> None:
        entry = _loaded_entry_or_raise(hass, call.data[CONF_ENTRY_ID])
        await async_skip(hass, entry, call.data.get(CONF_SESSION_ID), call.data[CONF_STEP])

    async def handle_stop_session(call: ServiceCall) -> None:
        entry = _loaded_entry_or_raise(hass, call.data[CONF_ENTRY_ID])
        await async_stop_session(hass, entry, call.data.get(CONF_SESSION_ID))

    async def handle_remove_players(call: ServiceCall) -> None:
        entry = _loaded_entry_or_raise(hass, call.data[CONF_ENTRY_ID])
        await async_remove_players(hass, entry, call.data[ATTR_ENTITY_ID])

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_ON_PLAYERS,
        handle,
        schema=PLAY_ON_PLAYERS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_PLAYLIST,
        handle_play_playlist,
        schema=PLAY_PLAYLIST_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_QUEUE,
        handle_play_queue,
        schema=PLAY_QUEUE_SCHEMA,
    )
    hass.services.async_register(DOMAIN, SERVICE_SKIP, handle_skip, schema=SKIP_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_SESSION, handle_stop_session, schema=STOP_SESSION_SCHEMA
    )
    async def handle_set_sync_adjust(call: ServiceCall) -> None:
        """Độ lệch (ms) của MỘT loa so với loa chuẩn khi đồng bộ: ÂM = phát sớm hơn, DƯƠNG = muộn hơn, 0 = xoá."""
        entry = _loaded_entry_or_raise(hass, call.data[CONF_ENTRY_ID])
        cu = dict(entry.options.get("dong_bo_adjust_ms") or {})
        ms = int(call.data["adjust_ms"])
        if ms:
            cu[call.data[ATTR_ENTITY_ID]] = ms
        else:
            cu.pop(call.data[ATTR_ENTITY_ID], None)
        hass.config_entries.async_update_entry(entry, options={**entry.options, "dong_bo_adjust_ms": cu})

    hass.services.async_register(
        DOMAIN, SERVICE_SET_SYNC_ADJUST, handle_set_sync_adjust, schema=SET_SYNC_ADJUST_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_PLAYERS, handle_remove_players, schema=REMOVE_PLAYERS_SCHEMA
    )
