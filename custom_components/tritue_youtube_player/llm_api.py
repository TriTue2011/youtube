"""Assist (LLM) API: search music, list speakers, play on one/several/all, control.

Registered as the LLM API "TriTue Music". In a conversation agent's options
(OpenAI, Google, Ollama, local OpenAI-compatible…) tick it next to "Assist";
the model then shows up to 10 numbered songs, asks which speakers (one,
several, or all), plays, and can pause/skip/stop per group of speakers.
"""

from __future__ import annotations

import time
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er, llm
from homeassistant.helpers.storage import Store
from homeassistant.util.json import JsonObjectType

from .api import YouTubePlayerApiError
from .assist_tools import SEARCH_LIMIT, format_duration, match_speakers, numbered_results
from .const import DOMAIN
from .hidden_players import STORAGE_KEY, STORAGE_VERSION, normalize_hidden
from .sessions import active_sessions

API_ID = DOMAIN
API_NAME = "TriTue Music"
PLAY_MEDIA_FEATURE = 512
SEARCH_TTL = 1800

API_PROMPT = (
    "TriTue Music plays YouTube / Zing MP3 on the home's speakers and TVs. "
    "To play music: call tim_nhac and show the user the numbered list (up to 10 songs) to choose from. "
    "If the user has not said where, call danh_sach_loa and ask which speakers: one, several, or all. "
    "Then call phat_nhac with the chosen number and speakers. If the user already named the song and "
    "speakers, do it straight away. Different speakers can play different songs. Use dieu_khien_nhac to "
    "pause, resume, skip, go back or stop (optionally only some speakers) and dang_phat to say what is "
    "playing where. Answer in the user's language."
)


def _entry(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry
    raise HomeAssistantError("TriTue YouTube Player is not loaded")


def _memory(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data.setdefault(f"{DOMAIN}_llm", {"results": {}})


def _user_key(llm_context: llm.LLMContext) -> str:
    context = llm_context.context
    return str((context.user_id if context else None) or llm_context.device_id or "")


async def _speakers(hass: HomeAssistant, entry) -> list[dict[str, Any]]:
    """Physical media players the card would show (not hidden, not our virtual player)."""
    registry = er.async_get(hass)
    virtual = {
        item.entity_id
        for item in registry.entities.values()
        if item.config_entry_id == entry.entry_id and item.domain == "media_player"
    }
    hidden = set(normalize_hidden(await Store(hass, STORAGE_VERSION, STORAGE_KEY).async_load()))
    sessions = active_sessions(entry.runtime_data.data)
    speakers = []
    for state in sorted(hass.states.async_all("media_player"), key=lambda s: str(s.name).lower()):
        if (
            state.entity_id in virtual
            or state.entity_id in hidden
            or state.state == STATE_UNAVAILABLE
            or not int(state.attributes.get("supported_features") or 0) & PLAY_MEDIA_FEATURE
        ):
            continue
        session = next((s for s in sessions if state.entity_id in s.get("output_entity_ids", [])), None)
        speakers.append(
            {
                "entity_id": state.entity_id,
                "name": str(state.name),
                "state": state.state,
                "song": ((session or {}).get("item") or {}).get("title") or "",
            }
        )
    return speakers


def _describe_sessions(hass: HomeAssistant, entry) -> list[dict[str, Any]]:
    out = []
    for session in active_sessions(entry.runtime_data.data):
        item = session.get("item") or {}
        outputs = session.get("output_entity_ids") or []
        lead = next((hass.states.get(e) for e in outputs if hass.states.get(e)), None)
        out.append(
            {
                "bai": item.get("title") or item.get("id"),
                "kenh": item.get("artist") or "",
                "loa": [hass.states.get(e).name if hass.states.get(e) else e for e in outputs],
                "trang_thai": lead.state if lead else "",
                "vi_tri": format_duration(lead.attributes.get("media_position")) if lead else "",
                "thoi_luong": format_duration(item.get("duration")),
            }
        )
    return out


def _sessions_for(entry, entity_ids: list[str]) -> list[dict[str, Any]]:
    sessions = active_sessions(entry.runtime_data.data)
    if not entity_ids:
        return sessions[:1]
    return [s for s in sessions if set(entity_ids) & set(s.get("output_entity_ids") or [])]


class SearchMusicTool(llm.Tool):
    name = "tim_nhac"
    description = (
        "Search YouTube (default) or Zing MP3 for songs. Returns up to 10 numbered results to show the "
        "user; a pasted YouTube link returns exactly that video."
    )
    parameters = vol.Schema(
        {
            vol.Required("tu_khoa", description="Song name, artist, or a YouTube link"): str,
            vol.Optional("nguon", description="youtube or zing"): vol.In(["youtube", "zing"]),
        }
    )

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> JsonObjectType:
        entry = _entry(hass)
        source = tool_input.tool_args.get("nguon") or "youtube"
        try:
            payload = await entry.runtime_data.client.async_search(
                str(tool_input.tool_args["tu_khoa"]), source=source, limit=SEARCH_LIMIT
            )
        except YouTubePlayerApiError as error:
            return {"loi": f"Không tìm được lúc này ({error})."}
        items = [item for item in payload.get("items") or [] if isinstance(item, dict)][:SEARCH_LIMIT]
        _memory(hass)["results"][_user_key(llm_context)] = {"items": items, "at": time.monotonic()}
        if not items:
            return {"ket_qua": [], "ghi_chu": "Không tìm thấy bài phù hợp."}
        return {"nguon": source, "ket_qua": numbered_results(items)}


class ListSpeakersTool(llm.Tool):
    name = "danh_sach_loa"
    description = "List the speakers and TVs music can play on, numbered, with what each is playing."
    parameters = vol.Schema({})

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> JsonObjectType:
        speakers = await _speakers(hass, _entry(hass))
        return {
            "loa": [
                {"so": number, "ten": s["name"], "trang_thai": s["state"], "dang_phat": s["song"]}
                for number, s in enumerate(speakers, 1)
            ],
            "ghi_chu": "Người dùng có thể chọn một loa, nhiều loa, hoặc 'tất cả'.",
        }


class PlayMusicTool(llm.Tool):
    name = "phat_nhac"
    description = (
        "Play a song from the last tim_nhac results (by number) or a YouTube link on speakers. "
        "Speakers: names or numbers from danh_sach_loa separated by commas, or 'tất cả' for all. "
        "The chosen speakers play this song together; other speakers keep their own songs."
    )
    parameters = vol.Schema(
        {
            vol.Required("bai", description="Number from tim_nhac, or a YouTube link"): str,
            vol.Required("loa", description="Speaker names/numbers separated by commas, or 'tất cả'"): str,
        }
    )

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> JsonObjectType:
        from .services import async_dispatch  # noqa: PLC0415 - avoid import cycle at setup

        entry = _entry(hass)
        choice = str(tool_input.tool_args["bai"]).strip()
        remembered = _memory(hass)["results"].get(_user_key(llm_context)) or {}
        items = remembered.get("items") if time.monotonic() - remembered.get("at", 0) < SEARCH_TTL else []
        if choice.isdigit():
            number = int(choice)
            if not items or not 1 <= number <= len(items):
                return {"loi": "Chưa có kết quả tìm kiếm hoặc số bài không hợp lệ — hãy gọi tim_nhac trước."}
            item = items[number - 1]
            source, target = str(item.get("source") or "youtube"), str(item.get("url") or item.get("id"))
            title = str(item.get("title") or target)
        else:
            source, target, title = "youtube", choice, choice
        speakers = await _speakers(hass, entry)
        entity_ids, missing = match_speakers(tool_input.tool_args["loa"], speakers)
        if missing or not entity_ids:
            return {
                "loi": f"Không nhận ra loa: {', '.join(missing) or tool_input.tool_args['loa']}.",
                "loa_co_the_chon": [s["name"] for s in speakers],
            }
        try:
            result = await async_dispatch(hass, entry, source=source, target=target, entity_ids=entity_ids)
        except HomeAssistantError as error:
            return {"loi": f"Không phát được: {error}"}
        names = {s["entity_id"]: s["name"] for s in speakers}
        skipped = [names.get(e, e) for e in result.get("skipped_targets") or []]
        return {
            "da_phat": title,
            "tren_loa": [names.get(e, e) for e in entity_ids if e not in (result.get("skipped_targets") or [])],
            **({"bo_qua": skipped} if skipped else {}),
        }


class ControlMusicTool(llm.Tool):
    name = "dieu_khien_nhac"
    description = (
        "Control music: tam_dung (pause), tiep_tuc (resume), bai_ke (next), bai_truoc (previous), dung (stop). "
        "Optionally only on some speakers (names/numbers, or 'tất cả'); default = the latest group playing."
    )
    parameters = vol.Schema(
        {
            vol.Required("lenh"): vol.In(["tam_dung", "tiep_tuc", "bai_ke", "bai_truoc", "dung"]),
            vol.Optional("loa", description="Speaker names/numbers, or 'tất cả'"): str,
        }
    )

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> JsonObjectType:
        from .services import async_remove_players, async_skip, async_stop_session  # noqa: PLC0415

        entry = _entry(hass)
        command = tool_input.tool_args["lenh"]
        entity_ids: list[str] = []
        if tool_input.tool_args.get("loa"):
            entity_ids, missing = match_speakers(tool_input.tool_args["loa"], await _speakers(hass, entry))
            if missing:
                return {"loi": f"Không nhận ra loa: {', '.join(missing)}."}
        sessions = _sessions_for(entry, entity_ids)
        if not sessions:
            return {"loi": "Không có nhạc nào đang phát ở đó."}
        try:
            for session in sessions:
                outputs = list(session.get("output_entity_ids") or [])
                if command in {"tam_dung", "tiep_tuc"}:
                    targets = [e for e in outputs if not entity_ids or e in entity_ids]
                    await hass.services.async_call(
                        "media_player",
                        "media_pause" if command == "tam_dung" else "media_play",
                        blocking=True,
                        target={"entity_id": targets},
                    )
                elif command in {"bai_ke", "bai_truoc"}:
                    await async_skip(hass, entry, session.get("session_id"), 1 if command == "bai_ke" else -1)
                elif entity_ids and set(outputs) - set(entity_ids):
                    await async_remove_players(hass, entry, [e for e in outputs if e in entity_ids])
                else:
                    await async_stop_session(hass, entry, session.get("session_id"))
        except HomeAssistantError as error:
            return {"loi": str(error)}
        return {"da_lam": command, "dang_phat": _describe_sessions(hass, entry)}


class NowPlayingTool(llm.Tool):
    name = "dang_phat"
    description = "What is playing on which speakers right now, with position."
    parameters = vol.Schema({})

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> JsonObjectType:
        return {"dang_phat": _describe_sessions(hass, _entry(hass))}


class TriTueMusicAPI(llm.API):
    """LLM API exposing the music tools."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass=hass, id=API_ID, name=API_NAME)

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        return llm.APIInstance(
            api=self,
            api_prompt=API_PROMPT,
            llm_context=llm_context,
            tools=[SearchMusicTool(), ListSpeakersTool(), PlayMusicTool(), ControlMusicTool(), NowPlayingTool()],
        )


def async_register_llm_api(hass: HomeAssistant):
    """Register once per Home Assistant instance; returns the unregister callback."""
    return llm.async_register_api(hass, TriTueMusicAPI(hass))
