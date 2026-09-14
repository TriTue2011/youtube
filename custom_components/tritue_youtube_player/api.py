"""Async client for the TriTue YouTube Player integration API."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class YouTubePlayerApiError(Exception):
    """Base error returned by the player API."""


class AuthenticationError(YouTubePlayerApiError):
    """The configured bearer token was rejected."""


class CannotConnectError(YouTubePlayerApiError):
    """The player server could not be reached."""


class InvalidTargetError(YouTubePlayerApiError):
    """The requested YouTube target is not supported."""


class YouTubePlayerClient:
    """Small client around the stable integration API contract."""

    def __init__(
        self, base_url: str, token: str, session: aiohttp.ClientSession
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._session = session

    async def async_health(self) -> dict[str, Any]:
        """Validate authentication and return server capabilities."""
        return await self._async_request("GET", "/api/integration/health")

    async def async_status(self) -> dict[str, Any]:
        """Return current playback and history state."""
        return await self._async_request("GET", "/api/integration/status")

    async def async_history(self) -> dict[str, Any]:
        """Return the bounded server-side playback history."""
        return await self._async_request("GET", "/api/integration/history")

    async def async_search(
        self, query: str, *, source: str = "youtube", limit: int = 20
    ) -> dict[str, Any]:
        """Search metadata from one add-on source."""
        return await self._async_request(
            "GET",
            "/api/integration/search",
            params={"source": source, "q": query, "limit": limit},
            request_timeout=35,
        )

    async def async_create_stream(
        self, source: str, target: str, *, max_height: int | None = None
    ) -> dict[str, Any]:
        """Create a short-lived public URL for a supported source.

        ``youtube_video`` is the picture only, up to ``max_height``, for the card."""
        payload: dict[str, Any] = {"source": source, "target": target}
        if max_height:
            payload["max_height"] = max_height
        return await self._async_request(
            "POST",
            "/api/integration/stream",
            json=payload,
            request_timeout=35,
        )

    async def async_playlists(self) -> dict[str, Any]:
        """The household playlists kept by the player server."""
        return await self._async_request("GET", "/api/integration/playlists")

    async def async_playlist_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        """One playlist command (create, add, import a link or share code, …).

        Importing a long YouTube playlist runs yt-dlp on the server for a while."""
        return await self._async_request(
            "POST", "/api/integration/playlists", json=payload, request_timeout=150
        )

    async def async_play(self, target: str) -> dict[str, Any]:
        """Send a YouTube URL or identifier to the web player."""
        return await self._async_request(
            "POST", "/api/integration/play", json={"target": target}
        )

    async def async_update_session(
        self,
        source: str,
        target: str,
        output_entity_ids: list[str],
        *,
        media_content_type: str | None = None,
        volume_level: float | None = None,
        session_id: str | None = None,
        controller: str | None = None,
        playlist_id: str | None = None,
    ) -> dict[str, Any]:
        """Share now-playing metadata and physical outputs with all HA clients.

        ``session_id`` keeps a group of speakers in its own session (and queue);
        omitted, the server finds or creates the session for these speakers."""
        payload: dict[str, Any] = {
            "source": source,
            "target": target,
            "output_entity_ids": output_entity_ids,
            "media_content_type": media_content_type,
            "volume_level": volume_level,
        }
        if session_id:
            payload["session_id"] = session_id
        if controller:
            payload["controller"] = controller
        if playlist_id:
            # The session's queue becomes this saved playlist.
            payload["playlist_id"] = playlist_id
        return await self._async_request(
            "POST", "/api/integration/session", json=payload
        )

    async def async_set_session_outputs(
        self, session_id: str, output_entity_ids: list[str]
    ) -> dict[str, Any]:
        """Change a session's speakers without restarting its song."""
        return await self._async_request(
            "POST",
            "/api/integration/session/outputs",
            json={"session_id": session_id, "output_entity_ids": output_entity_ids},
        )

    async def async_stop(
        self,
        *,
        expected_revision: int | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Stop one session (by id or revision), or everything."""
        body: dict[str, Any] = {}
        if expected_revision is not None:
            body["expected_revision"] = expected_revision
        if session_id:
            body["session_id"] = session_id
        kwargs = {"json": body} if body else {}
        return await self._async_request(
            "POST", "/api/integration/stop", **kwargs
        )

    async def _async_request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._token}"}
        request_timeout = kwargs.pop("request_timeout", 10)
        try:
            async with self._session.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=request_timeout),
                **kwargs,
            ) as response:
                try:
                    payload = await response.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError) as error:
                    raise YouTubePlayerApiError("invalid_response") from error

                error_code = (
                    payload.get("error", "request_failed")
                    if isinstance(payload, dict)
                    else "invalid_response"
                )
                if response.status == 401:
                    raise AuthenticationError(error_code)
                if response.status == 400 and error_code == "invalid_youtube_target":
                    raise InvalidTargetError(error_code)
                if response.status >= 400:
                    raise YouTubePlayerApiError(error_code)
                if not isinstance(payload, dict):
                    raise YouTubePlayerApiError("invalid_response")
                return payload
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            raise CannotConnectError("cannot_connect") from error
