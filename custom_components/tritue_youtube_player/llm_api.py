"""Assist (LLM) API: search music, list speakers, play on one/several/all, control.

Registered as the LLM API "TriTue Music". In a conversation agent's options
(OpenAI, Google, Ollama, local OpenAI-compatible…) tick it next to "Assist";
the model then shows up to 10 numbered songs, asks which speakers (one,
several, or all), plays, and can pause/skip/stop per group of speakers.
"""

from __future__ import annotations

import re
import time
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er, llm
from homeassistant.helpers.storage import Store
from homeassistant.util.json import JsonObjectType

from .api import YouTubePlayerApiError
from .playback import CHON_MODE_HOP_LE
from .code_input import clean_code
from .share_codes import async_playlist_id_from_code
from .assist_tools import (
    PLAYLIST_SOURCES,
    SEARCH_LIMIT,
    extract_item_id,
    fold,
    format_duration,
    format_playlists,
    format_queue,
    is_valid_youtube_playlist,
    match_playlist,
    match_queue_item,
    match_speakers,
    numbered_results,
    parse_safe_integer,
)
from .const import DOMAIN
from .hidden_players import STORAGE_KEY, STORAGE_VERSION, normalize_hidden
from .playback import async_play_queue
from .queue_store import get_queue_store
from .sessions import active_sessions, attach_session_queue, item_target

API_ID = DOMAIN
API_NAME = "TriTue Music"
PLAY_MEDIA_FEATURE = 512
SEARCH_TTL = 1800

API_PROMPT = (
    "TriTue Music plays YouTube / Zing MP3, household playlists, and queues on the home's speakers and TVs. "
    "To play songs: call tim_nhac and show the numbered list (up to 10 songs); then call phat_nhac. "
    "To play playlists: call tim_playlist with nguon_playlist ('kho' for household playlists, 'youtube' for YouTube). "
    "If the user says 'của tôi' / 'trong kho', use 'kho'; if 'trên YouTube', use 'youtube'. If ambiguous, the model may check 'kho' first "
    "(if empty, proceed to YouTube) or ask the user to pick: '1. Của bạn (trong kho)  2. Từ YouTube'. "
    "If the conversation has other music tools/providers (e.g. Music Assistant), list all possible sources as numbered choices for the user "
    "first before invoking any provider's tool, unless the source is already clear. "
    "Then call phat_playlist with the chosen playlist and speakers. "
    "To play queue: call phat_hang_doi to start playback immediately without asking confirmation. If speakers are not specified "
    "and more than one speaker is available, it returns a numbered list of speakers to ask the user which one to use. "
    "Use hang_doi to view, remove or jump queued songs. "
    "Use dieu_khien_nhac to pause, resume, skip, go back, or stop, and dang_phat to say what is playing where. "
    "Playback mode for phat_nhac/phat_playlist/phat_hang_doi: 'audio' for sound only, or 'video' to let a TV open the "
    "YouTube app. Do NOT invent resolution modes (360p, 720p, 1080p, 2k, 4k): the integration cannot choose picture quality. "
    "Answer in the user's language."
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
        "Play a song from the last tim_nhac results (by number) or a YouTube link/id on speakers. "
        "Speakers: names or numbers from danh_sach_loa separated by commas, or 'tất cả' for all. "
        "The chosen speakers play this song together; other speakers keep their own songs."
    )
    parameters = vol.Schema(
        {
            vol.Required("bai", description="Number from tim_nhac, or a YouTube video ID / link"): str,
            vol.Required("loa", description="Speaker names/numbers separated by commas, or 'tất cả'"): str,
            vol.Optional("mode", description="Playback mode: 'audio' (sound only) or 'video' (TV opens the YouTube app); no resolution choice"): vol.In(CHON_MODE_HOP_LE),
        }
    )

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> JsonObjectType:
        from .services import async_dispatch  # noqa: PLC0415 - avoid import cycle at setup

        entry = _entry(hass)
        choice = str(tool_input.tool_args["bai"]).strip()
        remembered = _memory(hass).get("results", {}).get(_user_key(llm_context)) or {}
        items = remembered.get("items") if time.monotonic() - remembered.get("at", 0) < SEARCH_TTL else []
        if choice.isdigit():
            number = int(choice)
            if not items or not 1 <= number <= len(items):
                return {"loi": "Chưa có kết quả tìm kiếm hoặc số bài không hợp lệ — hãy gọi tim_nhac trước."}
            item = items[number - 1]
            source, target = str(item.get("source") or "youtube"), item_target(item)
            title = str(item.get("title") or target)
        else:
            extracted = extract_item_id(choice, "youtube")
            target = extracted or choice
            source, title = "youtube", choice
        speakers = await _speakers(hass, entry)
        entity_ids, missing = match_speakers(tool_input.tool_args["loa"], speakers)
        if missing or not entity_ids:
            return {
                "loi": f"Không nhận ra loa: {', '.join(missing) or tool_input.tool_args['loa']}.",
                "loa_co_the_chon": [s["name"] for s in speakers],
            }
        try:
            result = await async_dispatch(
                hass,
                entry,
                source=source,
                target=target,
                entity_ids=entity_ids,
                mode=tool_input.tool_args.get("mode"),
            )
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


class SearchPlaylistTool(llm.Tool):
    name = "tim_playlist"
    description = (
        "Search or list playlists. nguon_playlist is REQUIRED: 'kho' for household playlists, 'youtube' for YouTube. "
        "The model must decide the source based on user speech ('của tôi'/'trong kho' -> 'kho'; 'trên YouTube' -> 'youtube'; "
        "if ambiguous, inspect 'kho' first or ask the user with a numbered list: 1. Của bạn (trong kho), 2. Từ YouTube). "
        "If other music providers like Music Assistant are available, list all possible sources as numbered choices for the user. "
        "Always returns so_playlist_trong_kho."
    )
    parameters = vol.Schema(
        {
            vol.Required("nguon_playlist", description="Playlist source: 'kho' (household) or 'youtube'"): vol.In(list(PLAYLIST_SOURCES)),
            vol.Optional("tu_khoa", description="Playlist name or YouTube playlist link"): str,
        }
    )

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> JsonObjectType:
        entry = _entry(hass)
        source = tool_input.tool_args.get("nguon_playlist") or "kho"
        query = str(tool_input.tool_args.get("tu_khoa") or "").strip()
        user_key = _user_key(llm_context)

        try:
            playlists_payload = await entry.runtime_data.client.async_playlists()
        except YouTubePlayerApiError:
            return {"loi": "Không đọc được danh sách playlist lúc này."}
        except Exception:
            return {"loi": "Không kết nối được với máy chủ playlist."}

        kho_playlists = [p for p in playlists_payload.get("playlists") or [] if isinstance(p, dict)]
        so_kho = len(kho_playlists)

        if source == "kho":
            mem = _memory(hass)
            if so_kho == 0:
                mem.setdefault("playlist_kho", {})[user_key] = {"items": [], "at": time.monotonic()}
                mem[f"playlist_kho_{user_key}"] = {"items": [], "at": time.monotonic()}
                return {
                    "nguon_playlist": "kho",
                    "so_playlist_trong_kho": 0,
                    "ket_qua": [],
                    "ghi_chu": "Kho gia đình chưa có playlist nào.",
                }
            items = kho_playlists
            if query:
                matched = match_playlist(query, kho_playlists)
                if isinstance(matched, list):
                    mem.setdefault("playlist_kho", {})[user_key] = {"items": matched, "at": time.monotonic()}
                    mem[f"playlist_kho_{user_key}"] = {"items": matched, "at": time.monotonic()}
                    return {
                        "nguon_playlist": "kho",
                        "so_playlist_trong_kho": so_kho,
                        "can_hoi": "Tìm thấy nhiều playlist phù hợp trong kho, bạn muốn chọn số nào?",
                        "ket_qua": format_playlists(matched),
                    }
                items = [matched] if matched else []
                if not items:
                    return {
                        "nguon_playlist": "kho",
                        "so_playlist_trong_kho": so_kho,
                        "ket_qua": [],
                        "ghi_chu": f"Không tìm thấy playlist nào khớp với '{query}'.",
                    }
            mem.setdefault("playlist_kho", {})[user_key] = {"items": items, "at": time.monotonic()}
            mem[f"playlist_kho_{user_key}"] = {"items": items, "at": time.monotonic()}
            return {
                "nguon_playlist": "kho",
                "so_playlist_trong_kho": so_kho,
                "ket_qua": format_playlists(items),
            }

        if source == "youtube":
            mem = _memory(hass)
            if query and is_valid_youtube_playlist(query):
                items = [{"id": query, "name": f"Playlist YouTube ({query})", "source": "youtube", "items": []}]
                mem.setdefault("playlist_youtube", {})[user_key] = {"items": items, "at": time.monotonic()}
                mem[f"playlist_youtube_{user_key}"] = {"items": items, "at": time.monotonic()}
                return {
                    "nguon_playlist": "youtube",
                    "so_playlist_trong_kho": so_kho,
                    "ket_qua": format_playlists(items),
                }
            mem.setdefault("playlist_youtube", {})[user_key] = {"items": [], "at": time.monotonic()}
            mem[f"playlist_youtube_{user_key}"] = {"items": [], "at": time.monotonic()}
            return {
                "loi": "Chưa tìm được playlist YouTube bằng từ khoá. Hãy dán link playlist YouTube hoặc nhập vào kho trước.",
                "nguon_playlist": "youtube",
                "so_playlist_trong_kho": so_kho,
                "ket_qua": [],
                "ghi_chu": "Chưa tìm được playlist YouTube bằng từ khoá. Hãy dán link playlist YouTube hoặc nhập vào kho trước.",
            }

        return {"loi": f"Nguồn playlist không hợp lệ: {source}"}


class PlayPlaylistTool(llm.Tool):
    name = "phat_playlist"
    description = (
        "Play a playlist from the last tim_playlist results (by number) or by 12-char library playlist code on speakers. "
        "Speakers: names or numbers from danh_sach_loa, or 'tất cả'."
    )
    parameters = vol.Schema(
        {
            vol.Required("danh_sach", description="Number from tim_playlist, or 12-char library playlist code"): str,
            vol.Required("loa", description="Speaker names/numbers separated by commas, or 'tất cả'"): str,
            vol.Required("nguon_playlist", description="'kho' or 'youtube'"): vol.In(list(PLAYLIST_SOURCES)),
            vol.Optional("mode", description="Playback mode: 'audio' (sound only) or 'video' (TV opens the YouTube app); no resolution choice"): vol.In(CHON_MODE_HOP_LE),
        }
    )

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> JsonObjectType:
        from .services import async_dispatch

        entry = _entry(hass)
        choice = clean_code(tool_input.tool_args["danh_sach"], "playlist_code")
        user_key = _user_key(llm_context)
        source = tool_input.tool_args["nguon_playlist"]

        playlist_id = None
        title = ""
        if choice.startswith("TTPL1."):
            # Mã chia sẻ chép từ thẻ: nhập vào kho một lần rồi phát (không tạo bản trùng khi hỏi lại).
            try:
                playlist_id = await async_playlist_id_from_code(hass, entry.runtime_data.client, choice)
            except ValueError as err:
                return {"loi": "Playlist trong mã chia sẻ không có bài phát được." if str(err) == "playlist_empty"
                        else "Mã chia sẻ playlist không hợp lệ."}
            except YouTubePlayerApiError:
                return {"loi": "Không nhập được playlist từ mã chia sẻ lúc này (máy phát không trả lời)."}
            title = playlist_id
        elif "list=" in choice or choice.startswith("PL") or source == "youtube":
            return {"loi": "Hãy nhập playlist này vào kho trước."}

        if playlist_id is None:
            mem = _memory(hass)
            sub = mem.get(f"playlist_{source}_{user_key}") or mem.get(f"playlist_{source}", {}).get(user_key) or {}
            items = sub.get("items") or []

            safe_num = parse_safe_integer(choice)
            if safe_num is not None:
                if not items or (time.monotonic() - sub.get("at", 0) >= SEARCH_TTL):
                    return {"loi": "Danh sách tìm kiếm đã hết hạn hoặc chưa tìm, vui lòng tìm lại playlist."}
                if not 1 <= safe_num <= len(items):
                    return {"loi": f"Số thứ tự {safe_num} không hợp lệ trong kết quả tìm kiếm (1-{len(items)})."}
                selected = items[safe_num - 1]
                playlist_id = str(selected.get("id"))
                title = str(selected.get("name") or selected.get("title") or playlist_id)
            elif re.fullmatch(r"^[a-z0-9]{12}$", choice):
                playlist_id = choice
                title = choice
            else:
                return {"loi": f"Mã playlist '{choice}' không hợp lệ. Vui lòng nhập số thứ tự từ tìm kiếm hoặc mã 12 ký tự trong kho."}

        try:
            pl_data = await entry.runtime_data.client.async_playlists()
            kho_pls = pl_data.get("playlists") or []
            matched = next((p for p in kho_pls if p.get("id") == playlist_id), None)
            if not matched:
                return {"loi": f"Không tìm thấy playlist với mã '{playlist_id}' trong kho."}
            title = matched.get("name") or title
            sub_items = matched.get("items") or []
            if not sub_items:
                return {"loi": f"Playlist '{title}' đang rỗng, không có bài hát nào."}
            first = sub_items[0]
            target = item_target(first)
            play_source = str(first.get("source") or "youtube")
        except Exception:
            return {"loi": "Lỗi đọc playlist từ máy chủ."}

        speakers = await _speakers(hass, entry)
        entity_ids, missing = match_speakers(tool_input.tool_args["loa"], speakers)
        if missing or not entity_ids:
            return {
                "loi": f"Không nhận ra loa: {', '.join(missing) or tool_input.tool_args['loa']}.",
                "loa_co_the_chon": [s["name"] for s in speakers],
            }

        try:
            result = await async_dispatch(
                hass,
                entry,
                source=play_source,
                target=target,
                entity_ids=entity_ids,
                playlist_id=playlist_id,
                mode=tool_input.tool_args.get("mode"),
            )
        except HomeAssistantError as error:
            return {"loi": f"Không phát được: {error}"}
        except Exception:
            return {"loi": "Không phát được playlist."}

        names = {s["entity_id"]: s["name"] for s in speakers}
        skipped = [names.get(e, e) for e in result.get("skipped_targets") or []]
        return {
            "da_phat": f"Playlist: {title}",
            "tren_loa": [names.get(e, e) for e in entity_ids if e not in (result.get("skipped_targets") or [])],
            **({"bo_qua": skipped} if skipped else {}),
        }


class PlayQueueTool(llm.Tool):
    name = "phat_hang_doi"
    description = (
        "Play the current queue immediately without asking confirmation. "
        "Speakers: optional speaker names/numbers; default = active speaker or asks if multiple available."
    )
    parameters = vol.Schema(
        {
            vol.Optional("loa", description="Speaker names/numbers separated by commas, or 'tất cả'"): str,
            vol.Optional("mode", description="Playback mode: 'audio' (sound only) or 'video' (TV opens the YouTube app); no resolution choice"): vol.In(CHON_MODE_HOP_LE),
        }
    )

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> JsonObjectType:
        entry = _entry(hass)
        speakers = await _speakers(hass, entry)
        speaker_arg = tool_input.tool_args.get("loa")
        entity_ids = []
        if speaker_arg:
            entity_ids, missing = match_speakers(speaker_arg, speakers)
            if missing or not entity_ids:
                return {
                    "loi": f"Không nhận ra loa: {', '.join(missing) or speaker_arg}.",
                    "loa_co_the_chon": [s["name"] for s in speakers],
                }
        else:
            if not speakers:
                return {"loi": "Không có loa nào khả dụng."}
            if len(speakers) > 1:
                return {
                    "can_hoi": "Bạn muốn phát hàng đợi ra loa nào?",
                    "danh_sach": [f"{idx}. {s['name']}" for idx, s in enumerate(speakers, 1)],
                }
            entity_ids = [speakers[0]["entity_id"]]

        lead_speaker = entity_ids[0]
        store = get_queue_store(hass)
        queue = await store.async_get(lead_speaker)
        items = queue.get("items") or []
        if not items:
            return {"loi": f"Hàng đợi của loa '{lead_speaker}' đang trống. Hãy thêm bài vào hàng đợi trước."}

        try:
            result = await async_play_queue(
                hass,
                entry,
                queue_code=lead_speaker,
                entity_ids=entity_ids,
                mode=tool_input.tool_args.get("mode"),
            )
        except (HomeAssistantError, ServiceValidationError) as error:
            return {"loi": f"Không phát được hàng đợi: {error}"}
        except ValueError as err:
            return {"loi": f"Lỗi hàng đợi: {err}"}
        except Exception:
            return {"loi": "Không phát được hàng đợi."}

        names = {s["entity_id"]: s["name"] for s in speakers}
        skipped = [names.get(e, e) for e in result.get("skipped_targets") or []]
        return {
            "da_phat_hang_doi": True,
            "tong_so_bai": len(items),
            "tren_loa": [names.get(e, e) for e in entity_ids if e not in (result.get("skipped_targets") or [])],
            **({"bo_qua": skipped} if skipped else {}),
        }


class QueueManageTool(llm.Tool):
    name = "hang_doi"
    description = (
        "Manage queue: xem (view items), xoa (remove song by number), nhay (jump to song number), xoa_het (clear all). "
        "Optionally specify loa (speaker name/number); default = active speaker or first speaker."
    )
    parameters = vol.Schema(
        {
            vol.Required("lenh", description="xem, xoa, nhay, xoa_het"): vol.In(["xem", "xoa", "nhay", "xoa_het"]),
            vol.Optional("loa", description="Speaker name/number"): str,
            vol.Optional("so", description="Song number (1..N) to remove or jump to"): str,
        }
    )

    async def async_call(self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext) -> JsonObjectType:
        from .services import async_dispatch

        entry = _entry(hass)
        speakers = await _speakers(hass, entry)
        speaker_arg = tool_input.tool_args.get("loa")
        entity_ids = []
        if speaker_arg:
            entity_ids, missing = match_speakers(speaker_arg, speakers)
            if missing or not entity_ids:
                return {"loi": f"Không nhận ra loa: {', '.join(missing) or speaker_arg}."}
        else:
            sessions = active_sessions(entry.runtime_data.data)
            if sessions and sessions[0].get("output_entity_ids"):
                entity_ids = list(sessions[0]["output_entity_ids"])
            elif speakers:
                entity_ids = [speakers[0]["entity_id"]]
            else:
                return {"loi": "Không có loa nào khả dụng."}

        lead_speaker = entity_ids[0]
        store = get_queue_store(hass)
        command = tool_input.tool_args["lenh"]

        if command == "xem":
            queue = await store.async_get(lead_speaker)
            return {"loa": lead_speaker, "hang_doi": format_queue(queue)}

        if command == "xoa_het":
            await store.async_change({"key": lead_speaker, "action": "clear"})
            return {"da_lam": "xoa_het", "loa": lead_speaker, "ghi_chu": "Đã xoá sạch hàng đợi."}

        so_arg = tool_input.tool_args.get("so")
        if so_arg is None or not str(so_arg).strip():
            return {"loi": f"Lệnh {command} cần cung cấp số thứ tự hoặc tên bài hát (tham số 'so')."}

        queue = await store.async_get(lead_speaker)
        items = queue.get("items") or []
        if not items:
            return {"loi": f"Hàng đợi của loa '{lead_speaker}' đang trống."}

        matched = match_queue_item(so_arg, queue)
        if isinstance(matched, list):
            return {
                "can_hoi": f"Có nhiều bài khớp với '{so_arg}', bạn muốn chọn bài nào?",
                "danh_sach": [f"{idx}. {item.get('title')}" for idx, item in enumerate(matched, 1)],
            }
        if matched is None:
            return {"loi": f"Không tìm thấy bài hát '{so_arg}' trong hàng đợi."}

        target_uid = matched["uid"]

        if command == "xoa":
            try:
                queue, _ = await store.async_change({"key": lead_speaker, "action": "remove", "uid": target_uid})
                return {"da_lam": "xoa", "bai": matched.get("title"), "loa": lead_speaker, "hang_doi": format_queue(queue)}
            except ValueError:
                return {"loi": f"Bài hát '{so_arg}' không còn trong hàng đợi."}

        if command == "nhay":
            try:
                res = await async_dispatch(
                    hass,
                    entry,
                    source=str(matched.get("source") or "youtube"),
                    target=item_target(matched),
                    entity_ids=entity_ids,
                    mode=None,
                )
            except (HomeAssistantError, ServiceValidationError) as error:
                return {"loi": f"Không phát được: {error}"}
            except Exception:
                return {"loi": "Không phát được bài hát."}

            await store.async_change({"key": lead_speaker, "action": "select", "uid": target_uid})
            if isinstance(res, dict) and res.get("session_id"):
                attach_session_queue(res["session_id"], lead_speaker)
            return {"da_lam": "nhay", "bai": matched.get("title"), "loa": lead_speaker}

        return {"loi": f"Lệnh không hỗ trợ: {command}"}


class TriTueMusicAPI(llm.API):
    """LLM API exposing the music tools."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass=hass, id=API_ID, name=API_NAME)

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        return llm.APIInstance(
            api=self,
            api_prompt=API_PROMPT,
            llm_context=llm_context,
            tools=[
                SearchMusicTool(),
                ListSpeakersTool(),
                PlayMusicTool(),
                ControlMusicTool(),
                NowPlayingTool(),
                SearchPlaylistTool(),
                PlayPlaylistTool(),
                PlayQueueTool(),
                QueueManageTool(),
            ],
        )


def async_register_llm_api(hass: HomeAssistant):
    """Register once per Home Assistant instance; returns the unregister callback."""
    return llm.async_register_api(hass, TriTueMusicAPI(hass))
