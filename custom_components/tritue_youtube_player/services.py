"""Home Assistant actions exposed by TriTue YouTube Player."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .actions import async_play_on_players
from .api import InvalidTargetError, YouTubePlayerApiError
from .const import (
    CONF_ENTRY_ID,
    CONF_MEDIA_CONTENT_TYPE,
    CONF_SOURCE,
    CONF_TARGET,
    CONF_VOLUME_LEVEL,
    DOMAIN,
    SERVICE_PLAY_ON_PLAYERS,
    SERVICE_REMOVE_PLAYERS,
    SERVICE_SKIP,
    SERVICE_STOP_SESSION,
)
from .playback import (
    UnsupportedCastMediaError,
    UnsupportedTargetMediaError,
    normalize_target_entity_ids,
)
from .sessions import (
    active_sessions,
    controller_id,
    find_session,
    item_target,
    queue_item,
)

CONF_SESSION_ID = "session_id"
CONF_JOIN = "join"
CONF_PLAYLIST_ID = "playlist_id"
CONF_STEP = "step"
STOP_FEATURE = 4096


PLAY_ON_PLAYERS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTRY_ID): cv.string,
        vol.Required(CONF_SOURCE): vol.In({"youtube", "zing", "http"}),
        vol.Required(CONF_TARGET): cv.string,
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(CONF_MEDIA_CONTENT_TYPE): cv.string,
        vol.Optional(CONF_VOLUME_LEVEL): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=1)
        ),
        vol.Optional(CONF_SESSION_ID): cv.string,
        vol.Optional(CONF_JOIN, default=False): cv.boolean,
        vol.Optional(CONF_PLAYLIST_ID): cv.string,
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
) -> dict:
    """Play one item on physical players as one session controlled by ``entry``.

    Shared by the play/skip actions, server-side auto-advance and Assist."""
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
        )
        await entry.runtime_data.async_refresh()
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
    )


async def async_skip(hass: HomeAssistant, entry, session_id: str | None, step: int) -> dict:
    """Play the next/previous item of a session's own queue on its speakers."""
    session = find_session(entry.runtime_data.data, session_id)
    if session is None:
        raise _validation_error("session_not_found")
    found = queue_item(session, step)
    if found is None:
        raise _validation_error("queue_end")
    _, item = found
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
        await hass.services.async_call(
            "media_player", "media_stop", blocking=True, target={ATTR_ENTITY_ID: outputs}
        )
    try:
        if session and session.get("session_id"):
            await entry.runtime_data.client.async_stop(session_id=session["session_id"])
        elif session is None and session_id:
            raise _validation_error("session_not_found")
        else:
            await entry.runtime_data.client.async_stop()
    except YouTubePlayerApiError as error:
        raise _validation_error("playback_error") from error
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
        await hass.services.async_call(
            "media_player", "media_stop", blocking=True, target={ATTR_ENTITY_ID: stoppable}
        )
    await entry.runtime_data.async_refresh()


def async_register_services(hass: HomeAssistant) -> None:
    """Register integration actions once for all config entries."""
    if hass.services.has_service(DOMAIN, SERVICE_PLAY_ON_PLAYERS):
        return

    async def handle(call: ServiceCall) -> None:
        await _async_handle_play_on_players(hass, call)

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
    hass.services.async_register(DOMAIN, SERVICE_SKIP, handle_skip, schema=SKIP_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_SESSION, handle_stop_session, schema=STOP_SESSION_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_PLAYERS, handle_remove_players, schema=REMOVE_PLAYERS_SCHEMA
    )
