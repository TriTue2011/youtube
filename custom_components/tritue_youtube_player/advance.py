"""Server-side auto-advance: the next song plays even with every browser closed.

Before 0.9 the card advanced the queue, so closing the dashboard stopped the
music after the current song. Home Assistant sees the speakers' states, so the
integration now watches the speaker leading each session it started and, when
that speaker finishes the track, plays the session's next queue item on the
same speakers.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import LOGGER
from .playback import build_target_capabilities, is_native_youtube_transport
from .sessions import active_sessions, is_controlled_by, observe_track, queue_item


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
        if not observe_track(tracker, state, attributes, dt_util.utcnow(), session.get("item")):
            return
        session_id = str(session.get("session_id") or "")
        if session_id in self._advancing or queue_item(session, 1) is None:
            return
        self._advancing.add(session_id)
        self.hass.async_create_task(self._async_advance(session), eager_start=False)

    async def _async_advance(self, session: dict[str, Any]) -> None:
        from .services import async_skip  # noqa: PLC0415 - services imports HA actions lazily

        session_id = str(session.get("session_id") or "")
        try:
            await async_skip(self.hass, self.entry, session.get("session_id"), 1)
        except HomeAssistantError as error:
            LOGGER.warning("Auto-advance of session %s failed: %s", session_id, error)
        finally:
            self._advancing.discard(session_id)
