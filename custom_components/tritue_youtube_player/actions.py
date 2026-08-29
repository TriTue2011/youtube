"""Source-to-speaker dispatch shared by Home Assistant service actions."""

from __future__ import annotations

from contextlib import suppress
from typing import Any

from .playback import (
    UnsupportedTargetMediaError,
    build_direct_audio_request,
    build_stream_request,
    build_target_capabilities,
    build_target_request,
    normalize_target_entity_ids,
)


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
) -> dict[str, Any]:
    """Resolve one source item and dispatch it to one or more HA players."""
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
    youtube_session_started = False
    youtube_session_revision = None
    physical_dispatch_completed = False
    try:
        first_error = None
        if source == "youtube":
            played = await client.async_play(target)
            youtube_session_started = True
            youtube_session_revision = played.get("session_revision")
            item = played.get("item") or {}
            for entity_id in playable_targets:
                try:
                    requests[entity_id] = build_target_request(
                        item,
                        target_platform=target_platforms.get(entity_id),
                        target_device_class=target_device_classes.get(entity_id),
                        requested_media_type="video",
                    )
                except UnsupportedTargetMediaError as error:
                    first_error = first_error or error
                    skipped_targets.append(entity_id)
            playable_targets = list(requests)
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
            stream = await client.async_create_stream("zing", target)
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
            for entity_id, service_data in requests.items():
                try:
                    await hass.services.async_call(
                        "media_player",
                        "play_media",
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
            playable_targets = dispatched_targets
            if not playable_targets and first_dispatch_error is not None:
                raise first_dispatch_error
        await client.async_update_session(
            source,
            target,
            playable_targets,
            media_content_type=session_media_content_type,
            volume_level=volume_level,
        )
    except Exception:
        if (
            youtube_session_started
            and not physical_dispatch_completed
            and isinstance(youtube_session_revision, int)
        ):
            with suppress(Exception):
                await client.async_stop(
                    expected_revision=youtube_session_revision
                )
        raise
    return {
        "source": source,
        "selected_count": len(targets),
        "target_count": len(playable_targets),
        "skipped_targets": skipped_targets,
    }
