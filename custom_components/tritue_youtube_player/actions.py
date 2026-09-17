"""Source-to-speaker dispatch shared by Home Assistant service actions."""

from __future__ import annotations

from contextlib import suppress
from typing import Any
from urllib.parse import urlsplit

from .playback import (
    UnsupportedTargetMediaError,
    build_direct_audio_request,
    build_stream_request,
    build_target_call,
    build_target_capabilities,
    is_native_youtube_transport,
    normalize_target_entity_ids,
)


def speaker_base_url(hass: Any, client: Any) -> str | None:
    """Dia chi add-on ma LOA tai duoc luong phat.

    Loa khong o trong mang docker, nen add-on khong tu biet dia chi nay: moi loi
    goi cua integration den no deu qua NAT cua Supervisor (log that 17/09/2026:
    nguon la 172.30.32.1). Nhung Home Assistant thi biet dia chi LAN cua chinh
    no (Cai dat > He thong > Mang > URL Home Assistant), con cong thi lay tu URL
    add-on da cau hinh -- nen doi map cong cung ra dung.

    Thieu bat cu manh nao thi tra None: add-on se bao public_base_url_required
    ro rang, hon la im lang.
    """
    try:
        from homeassistant.helpers.network import get_url
    except Exception:
        return None
    try:
        ha_url = get_url(
            hass,
            allow_internal=True,
            allow_external=False,
            allow_cloud=False,
            allow_ip=True,
            prefer_external=False,
        )
    except Exception:
        # NoURLAvailableError khi chua cau hinh URL noi bo -- khong phai loi.
        return None
    host = urlsplit(str(ha_url or "")).hostname
    if not host:
        return None
    port = None
    with suppress(Exception):
        port = urlsplit(str(getattr(client, "base_url", "") or "")).port
    host_part = f"[{host}]" if ":" in host else host
    return f"http://{host_part}:{port or 8099}"


async def async_play_on_players(
    hass: Any,
    client: Any,
    *,
    source: str,
    target: str,
    entity_ids: Any,
    target_platforms: dict[str, str | None],
    target_device_classes: dict[str, str | None] | None = None,
    target_supported_features: dict[str, int | None] | None = None,
    volume_level: float | None = None,
    media_content_type: str | None = None,
    excluded_entity_ids: set[str] | None = None,
    session_id: str | None = None,
    controller: str | None = None,
    join_entity_ids: list[str] | None = None,
    playlist_id: str | None = None,
) -> dict[str, Any]:
    """Resolve one source item and dispatch it to one or more HA players.

    The speakers become one playback session on the server (a speaker leaves any
    other session). ``join_entity_ids`` are speakers already playing this
    session's song: they stay in the session but are not sent the song again."""
    targets = normalize_target_entity_ids(
        entity_ids, excluded=excluded_entity_ids or set()
    )
    target_device_classes = target_device_classes or {}
    target_supported_features = target_supported_features or {}
    if volume_level is not None and not 0 <= float(volume_level) <= 1:
        raise ValueError("invalid_volume_level")

    def capabilities(entity_id: str) -> dict[str, Any]:
        return build_target_capabilities(
            target_platform=target_platforms.get(entity_id),
            target_device_class=target_device_classes.get(entity_id),
            supported_features=target_supported_features.get(entity_id),
        )

    playable_targets = [
        entity_id
        for entity_id in targets
        if source in capabilities(entity_id)["sources"]
    ]
    skipped_targets = [
        entity_id for entity_id in targets if entity_id not in playable_targets
    ]

    if source not in {"youtube", "zing", "http"}:
        raise ValueError("unsupported_source")
    if not playable_targets:
        raise UnsupportedTargetMediaError("target_source_unsupported")

    direct_request = None
    session_media_content_type = media_content_type
    if source == "http":
        direct_request = build_direct_audio_request(target, media_content_type)
        session_media_content_type = direct_request["media_content_type"]

    requests = {}
    youtube_audio_targets = []
    joined = [
        entity_id for entity_id in (join_entity_ids or []) if entity_id not in playable_targets
    ]
    # Reserve the session first: it validates the target, returns normalized
    # metadata for native YouTube apps, and moves these speakers out of other
    # sessions before they receive the new song.
    recorded = await client.async_update_session(
        source,
        target,
        joined + playable_targets,
        media_content_type=media_content_type,
        volume_level=volume_level,
        session_id=session_id,
        controller=controller,
        **({"playlist_id": playlist_id} if playlist_id else {}),
    )
    session = recorded.get("session") or {}
    session_id = session.get("session_id") or session_id
    session_revision = session.get("revision")
    physical_dispatch_completed = False
    try:
        first_error = None
        if source == "youtube":
            item = session.get("item") or {}
            for entity_id in playable_targets:
                if not is_native_youtube_transport(
                    capabilities(entity_id)["transport"]
                ):
                    youtube_audio_targets.append(entity_id)
                    continue
                try:
                    requests[entity_id] = build_target_call(
                        item,
                        target_platform=target_platforms.get(entity_id),
                        target_device_class=target_device_classes.get(entity_id),
                        requested_media_type="video",
                    )
                except UnsupportedTargetMediaError as error:
                    first_error = first_error or error
                    skipped_targets.append(entity_id)
            playable_targets = list(requests) + youtube_audio_targets
        if not playable_targets:
            if first_error is not None:
                raise first_error
            raise UnsupportedTargetMediaError("target_source_unsupported")

        if volume_level is not None:
            volume_targets = [
                entity_id
                for entity_id in playable_targets
                if target_supported_features.get(entity_id) is None
                or int(target_supported_features[entity_id] or 0) & 4
            ]
            if volume_targets:
                await hass.services.async_call(
                    "media_player",
                    "volume_set",
                    {"volume_level": float(volume_level)},
                    blocking=True,
                    target={"entity_id": volume_targets},
                )

        if source == "zing":
            stream = await client.async_create_stream(
                "zing", target, public_base_url=speaker_base_url(hass, client)
            )
            service_data = build_stream_request(stream)
            session_media_content_type = service_data["media_content_type"]
            await hass.services.async_call(
                "media_player",
                "play_media",
                service_data,
                blocking=True,
                target={"entity_id": playable_targets},
            )
            physical_dispatch_completed = True
        elif source == "http":
            await hass.services.async_call(
                "media_player",
                "play_media",
                direct_request,
                blocking=True,
                target={"entity_id": playable_targets},
            )
            physical_dispatch_completed = True
        else:
            dispatched_targets = []
            first_dispatch_error = None
            for entity_id, (domain, service, service_data) in requests.items():
                try:
                    await hass.services.async_call(
                        domain,
                        service,
                        service_data,
                        blocking=True,
                        target={"entity_id": entity_id},
                    )
                except Exception as error:
                    first_dispatch_error = first_dispatch_error or error
                    skipped_targets.append(entity_id)
                else:
                    dispatched_targets.append(entity_id)
                    physical_dispatch_completed = True
            if youtube_audio_targets:
                try:
                    stream = await client.async_create_stream(
                        "youtube", target, public_base_url=speaker_base_url(hass, client)
                    )
                    audio_request = build_stream_request(stream)
                except Exception as error:
                    first_dispatch_error = first_dispatch_error or error
                    skipped_targets.extend(youtube_audio_targets)
                else:
                    session_media_content_type = audio_request["media_content_type"]
                    for entity_id in youtube_audio_targets:
                        try:
                            await hass.services.async_call(
                                "media_player",
                                "play_media",
                                audio_request,
                                blocking=True,
                                target={"entity_id": entity_id},
                            )
                        except Exception as error:
                            first_dispatch_error = first_dispatch_error or error
                            skipped_targets.append(entity_id)
                        else:
                            dispatched_targets.append(entity_id)
                            physical_dispatch_completed = True
            playable_targets = dispatched_targets
            if not playable_targets and first_dispatch_error is not None:
                raise first_dispatch_error
        outputs = joined + playable_targets
        if outputs != list(session.get("output_entity_ids") or outputs) or (
            session_media_content_type and session_media_content_type != media_content_type
        ):
            # Some speakers refused, or the stream type is now known: record the
            # final outputs in the same session (its queue is kept).
            recorded = await client.async_update_session(
                source,
                target,
                outputs,
                media_content_type=session_media_content_type,
                volume_level=volume_level,
                session_id=session_id,
                controller=controller,
            )
            session = recorded.get("session") or session
    except Exception:
        if not physical_dispatch_completed:
            with suppress(Exception):
                if session_id:
                    await client.async_stop(session_id=session_id)
                elif isinstance(session_revision, int):
                    await client.async_stop(expected_revision=session_revision)
        raise
    return {
        "source": source,
        "selected_count": len(targets),
        "target_count": len(playable_targets),
        "skipped_targets": skipped_targets,
        "session_id": session.get("session_id") or session_id,
    }
