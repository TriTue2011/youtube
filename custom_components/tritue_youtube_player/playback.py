"""Build playback requests for physical Home Assistant media players."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit


MEDIA_PLAYER_ENTITY_ID = re.compile(r"^media_player\.[a-z0-9_]+$")
PLAY_MEDIA_FEATURE = 512
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
DIRECT_AUDIO_TYPES = {
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".m3u8": "application/vnd.apple.mpegurl",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
}
ALLOWED_DIRECT_CONTENT_TYPES = {
    *DIRECT_AUDIO_TYPES.values(),
    "application/x-mpegurl",
}


class UnsupportedTargetMediaError(ValueError):
    """The source cannot be dispatched to this kind of HA media player."""


class UnsupportedCastMediaError(UnsupportedTargetMediaError):
    """The normalized item cannot be started by the YouTube Cast app."""


def normalize_target_entity_ids(
    value: Any, *, excluded: set[str] | None = None
) -> list[str]:
    """Validate, deduplicate and bound physical media player targets."""
    candidates = [value] if isinstance(value, str) else list(value or [])
    normalized = []
    for candidate in candidates:
        entity_id = str(candidate or "").strip()
        if (
            not MEDIA_PLAYER_ENTITY_ID.fullmatch(entity_id)
            or entity_id in (excluded or set())
        ):
            raise ValueError("invalid_target_entity")
        if entity_id not in normalized:
            normalized.append(entity_id)
    if not 1 <= len(normalized) <= 16:
        raise ValueError("invalid_target_entities")
    return normalized


def build_stream_request(payload: dict[str, Any]) -> dict[str, str]:
    """Build generic Home Assistant audio media from an add-on stream response."""
    stream_url = str(payload.get("stream_url") or "")
    parsed = urlsplit(stream_url)
    content_type = str(payload.get("media_content_type") or "audio/mpeg")
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or (
            not content_type.startswith("audio/")
            and content_type
            not in {"application/vnd.apple.mpegurl", "application/x-mpegurl"}
        )
    ):
        raise ValueError("invalid_stream_response")
    return {
        "media_content_id": stream_url,
        "media_content_type": content_type,
    }


def build_direct_audio_request(
    stream_url: str, media_content_type: str | None = None
) -> dict[str, str]:
    """Normalize direct HTTP audio before any physical player is mutated."""
    stream_url = str(stream_url or "")
    if len(stream_url) > 2048:
        raise ValueError("invalid_http_audio_target")
    parsed = urlsplit(stream_url)
    hostname = (parsed.hostname or "").lower()
    if hostname in YOUTUBE_HOSTS or hostname.endswith(".youtube.com"):
        raise ValueError("invalid_http_audio_target")
    path = parsed.path.lower()
    inferred_type = next(
        (
            content_type
            for extension, content_type in DIRECT_AUDIO_TYPES.items()
            if path.endswith(extension)
        ),
        "audio/mpeg",
    )
    content_type = str(media_content_type or inferred_type)
    if content_type not in ALLOWED_DIRECT_CONTENT_TYPES:
        raise ValueError("invalid_http_audio_target")
    try:
        return build_stream_request(
            {
                "stream_url": stream_url,
                "media_content_type": content_type,
            }
        )
    except ValueError as error:
        raise ValueError("invalid_http_audio_target") from error


def _media_type_value(value: Any, fallback: str) -> str:
    """Return a Home Assistant media type as a plain string."""
    normalized = getattr(value, "value", value)
    return str(normalized or fallback)


def canonical_youtube_url(item: dict[str, Any]) -> str:
    """Build a canonical public YouTube URL from a normalized server item."""
    identifier = str(item.get("id") or "")
    if item.get("kind") == "video":
        url = f"https://www.youtube.com/watch?v={identifier}"
        if playlist_id := str(item.get("playlist_id") or ""):
            url = f"{url}&list={playlist_id}"
        return url
    return f"https://www.youtube.com/playlist?list={identifier}"


def build_target_capabilities(
    *,
    target_platform: str | None,
    target_device_class: str | None,
    supported_features: int | None,
) -> dict[str, Any]:
    """Describe which sources can be sent to one physical media player."""
    platform = str(target_platform or "").lower()
    device_class = str(target_device_class or "").lower()
    supports_play_media = supported_features is None or bool(
        int(supported_features) & PLAY_MEDIA_FEATURE
    )

    if platform == "cast":
        if device_class == "speaker":
            transport = "google_cast_audio"
        elif device_class == "tv":
            transport = "google_cast_video"
        else:
            transport = "google_cast_unknown"
    elif platform in {"androidtv", "androidtv_remote"}:
        transport = "android_tv"
    elif platform == "dlna_dmr":
        transport = "dlna"
    elif supports_play_media:
        transport = "generic_audio"
    else:
        transport = "unsupported"

    # TVs and Android boxes run the native YouTube app (with video); every other
    # play_media-capable speaker (Cast audio, DLNA, ESPHome, generic) receives
    # YouTube as a relayed audio stream, exactly like Zing.
    sources = ["youtube", "zing", "http"] if supports_play_media else []
    return {
        "transport": transport,
        "sources": sources,
        "supports_play_media": supports_play_media,
        "youtube_transport": (
            "native"
            if transport in {"google_cast_video", "android_tv"}
            else "audio"
        ),
    }


NATIVE_YOUTUBE_TRANSPORTS = {"google_cast_video", "android_tv"}


def is_native_youtube_transport(transport: str | None) -> bool:
    """Return whether a transport plays YouTube through the native Cast app."""
    return transport in NATIVE_YOUTUBE_TRANSPORTS


def build_target_request(
    item: dict[str, Any],
    *,
    target_platform: str | None,
    requested_media_type: Any,
    target_device_class: str | None = None,
) -> dict[str, str]:
    """Build ``media_player.play_media`` data for the selected output entity."""
    if target_platform == "cast":
        if target_device_class == "speaker":
            raise UnsupportedTargetMediaError(
                "youtube_page_is_not_an_audio_stream"
            )
        if item.get("kind") != "video" or not item.get("id"):
            raise UnsupportedCastMediaError("cast_playlist_requires_video")
        payload = {
            "app_name": "youtube",
            "media_id": str(item["id"]),
        }
        if playlist_id := str(item.get("playlist_id") or ""):
            payload["playlist_id"] = playlist_id
        return {
            "media_content_type": "cast",
            "media_content_id": json.dumps(payload, separators=(",", ":")),
        }

    if target_platform in {"androidtv", "androidtv_remote"}:
        return {
            "media_content_type": "url",
            "media_content_id": canonical_youtube_url(item),
        }

    raise UnsupportedTargetMediaError("youtube_transport_unsupported")
