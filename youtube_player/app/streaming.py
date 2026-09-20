"""Short-lived, signed streaming support for public Zing songs and YouTube audio."""

from __future__ import annotations

import base64
import gzip
import hashlib
import hmac
import io
import json
import re
import shutil
import sys
import time
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)


STREAM_SOURCES = ("zing", "youtube", "youtube_video", "facebook", "facebook_video")
YOUTUBE_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
# Facebook: reel hoặc video thường, mã là một chuỗi số.
#
# Đo 19/09/2026 trên bài chủ máy gửi, CÙNG MỘT MÃ `1807802260572674`:
#   /watch/?v=<mã>   -> đúng video, 148,821 giây
#   /reel/<mã>/      -> đúng video, 148,821 giây
#   /video.php?v=<mã> -> "This video is only available for registered users"
# Nghĩa là câu "chỉ dành cho người dùng đã đăng ký" là lời từ chối cho DẠNG ĐỊA CHỈ
# không đọc được, KHÔNG phải lời nói về quyền xem. Câu ấy đã dẫn tôi kết luận sai ba
# lần liền; ghi lại đây để lần sau không ai (kể cả tôi) suy từ nó ra chuyện quyền xem.
# Dựng địa chỉ dạng "/watch/?v=" vì nó phủ được cả reel lẫn video thường.
FACEBOOK_VIDEO_ID = re.compile(r"^[0-9]{5,25}$")
FACEBOOK_VIDEO_TARGET = re.compile(r"^([0-9]{5,25}):(360|480|720|1080)$")
FACEBOOK_STREAM_HOSTS = ("fbcdn.net",)
# Facebook phục vụ hai tệp GỘP SẴN (hình avc1 + tiếng AAC trong cùng một mp4): "hd"
# và "sd". Đo 19/09/2026: tải 128 KB đầu của cả hai đều thấy "ftyp moov avc1 mp4a",
# máy chủ trả HTTP 206 kiểu video/mp4, từ video-hkg1-2.xx.fbcdn.net.
# QUAN TRỌNG: yt-dlp báo vcodec, acodec và height của hai định dạng này đều là NA,
# nên KHÔNG lọc được theo codec hay chiều cao như bên YouTube — chép khuôn
# `_youtube_video_format` sang đây sẽ lọc sạch mọi ứng viên rồi báo "không có định
# dạng phù hợp". Phải chọn theo MÃ ĐỊNH DẠNG.
FACEBOOK_MUXED_FORMATS = ("hd", "sd")
# The PICTURE only (no sound) of a video, for a browser when YouTube refuses the
# embed: target "ID:max height". The sound plays separately and the picture follows.
YOUTUBE_VIDEO_HEIGHTS = (360, 480, 720, 1080)
YOUTUBE_VIDEO_TARGET = re.compile(r"^([A-Za-z0-9_-]{11}):(360|480|720|1080)$")
# Every browser decodes avc1/mp4 (old Safari included); vp9 then av1 only when missing.
YOUTUBE_VIDEO_CODECS = ("avc1", "vp9", "vp09", "av01")
YOUTUBE_AUDIO_FORMAT = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio"
STREAM_CACHE_DEFAULT_SECONDS = 120
STREAM_CACHE_MAX_SECONDS = 5 * 3600
STREAM_EXPIRY_MARGIN_SECONDS = 600
YOUTUBE_STREAM_HOSTS = ("googlevideo.com",)
ZING_ID = re.compile(r"^[A-Za-z0-9]{8,16}$")
ZING_API_BASE = "https://zingmp3.vn"
ZING_API_PATH = "/api/v2/song/get/streaming"
ZING_API_KEY = "X5BM3w8N7MKozC0B85o4KMlzLZKhV00y"
ZING_API_SECRET = "acOrvUS15XRW2o9JksiK1KgQ6Vbds8ZW"
ZING_WEB_VERSION = "1.20.4"
ZING_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)
CONTENT_TYPES = {
    "aac": "audio/aac",
    # Bài PHÁT TRỰC TIẾP không có tệp nhạc, chỉ có bản kê luồng HLS. Thiếu dòng này
    # thì nó rơi về mặc định "audio/mp4" — một lời khai SAI. Đo 20/09/2026 trên bài
    # trực tiếp thật: máy chủ gốc trả đúng "application/vnd.apple.mpegurl", còn ta
    # thì khai là mp4, khiến bên nhận tưởng phát được rồi mới hỏng.
    "m3u8": "application/vnd.apple.mpegurl",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "opus": "audio/ogg",
    "wav": "audio/wav",
    "webm": "audio/webm",
}
VIDEO_CONTENT_TYPES = {"mp4": "video/mp4", "webm": "video/webm"}
ZING_CDN_HOSTS = ("zmdcdn.me", "zadn.vn", "zing.vn", "zingmp3.vn")


class InvalidStreamTokenError(ValueError):
    """The public stream token is invalid, tampered with, or expired."""


class StreamUnavailableError(RuntimeError):
    """The upstream public stream could not be resolved."""


class _ZingRedirectHandler(HTTPRedirectHandler):
    """Allow page redirects only to another validated public Zing song URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            validate_zing_target(newurl)
        except ValueError as error:
            raise StreamUnavailableError("unsafe_stream_redirect") from error
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def validate_zing_target(target_url: str) -> str:
    """Return a normalized public Zing song URL or raise ``ValueError``."""
    target_url = str(target_url or "").strip()
    parsed = urlsplit(target_url)
    host = (parsed.hostname or "").lower()
    song_id = parsed.path.rsplit("/", 1)[-1].removesuffix(".html")
    if (
        parsed.scheme != "https"
        or not (host == "zingmp3.vn" or host.endswith(".zingmp3.vn"))
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.path.startswith("/bai-hat/")
        or not ZING_ID.fullmatch(song_id)
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("invalid_zing_target")
    return target_url


def normalize_public_base_url(base_url: str) -> str:
    """Validate the LAN URL speakers use to reach this add-on."""
    base_url = str(base_url or "").strip()
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("invalid_public_base_url")
    return base_url.rstrip("/")


def validate_stream_target(source: str, target: str) -> str:
    """Return a normalized target for one supported audio source, or raise."""
    if source == "zing":
        return validate_zing_target(target)
    if source == "youtube":
        video_id = str(target or "").strip()
        if not YOUTUBE_VIDEO_ID.fullmatch(video_id):
            raise ValueError("invalid_youtube_target")
        return video_id
    if source == "youtube_video":
        value = str(target or "").strip()
        if not YOUTUBE_VIDEO_TARGET.fullmatch(value):
            raise ValueError("invalid_youtube_target")
        return value
    if source == "facebook":
        video_id = str(target or "").strip()
        if not FACEBOOK_VIDEO_ID.fullmatch(video_id):
            raise ValueError("invalid_facebook_target")
        return video_id
    if source == "facebook_video":
        value = str(target or "").strip()
        if not FACEBOOK_VIDEO_TARGET.fullmatch(value):
            raise ValueError("invalid_facebook_target")
        return value
    raise ValueError("unsupported_stream_source")


def youtube_video_target(video_id: str, max_height) -> str:
    """Picture target: the nearest standard height not above `max_height` (360–1080)."""
    try:
        wanted = int(max_height)
    except (TypeError, ValueError):
        wanted = 720
    height = max([h for h in YOUTUBE_VIDEO_HEIGHTS if h <= wanted] or [YOUTUBE_VIDEO_HEIGHTS[0]])
    return validate_stream_target("youtube_video", f"{video_id}:{height}")


def create_stream_token(
    target: str,
    secret: str,
    *,
    source: str = "zing",
    now: int | None = None,
    ttl: int = 300,
) -> str:
    """Create a signed, URL-safe token for one Zing song or YouTube video."""
    target = validate_stream_target(source, target)
    secret = str(secret or "")
    if not secret:
        raise ValueError("invalid_stream_secret")
    if not 30 <= int(ttl) <= 7200:
        raise ValueError("invalid_stream_ttl")
    issued_at = int(time.time() if now is None else now)
    payload = _b64encode(
        json.dumps(
            {"exp": issued_at + int(ttl), "source": source, "target": target},
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    )
    signature = _b64encode(
        hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    )
    return f"{payload}.{signature}"


def verify_stream_token(
    token: str, secret: str, *, now: int | None = None
) -> tuple[str, str]:
    """Verify a stream token and return its ``(source, target)`` pair."""
    try:
        payload, provided_signature = str(token).split(".", 1)
        expected_signature = _b64encode(
            hmac.new(str(secret).encode(), payload.encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(provided_signature, expected_signature):
            raise InvalidStreamTokenError("invalid_stream_token")
        value = json.loads(_b64decode(payload))
        current_time = int(time.time() if now is None else now)
        source = value.get("source")
        if source not in STREAM_SOURCES or int(value.get("exp", 0)) < current_time:
            raise InvalidStreamTokenError("expired_stream_token")
        return source, validate_stream_target(source, value.get("target"))
    except InvalidStreamTokenError:
        raise
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise InvalidStreamTokenError("invalid_stream_token") from error


def build_signed_stream_url(
    public_base_url: str,
    target: str,
    secret: str,
    *,
    source: str = "zing",
    now: int | None = None,
    ttl: int = 300,
) -> str:
    """Build the short-lived URL passed to a Home Assistant media player."""
    base_url = normalize_public_base_url(public_base_url)
    token = create_stream_token(target, secret, source=source, now=now, ttl=ttl)
    return f"{base_url}/api/stream/{token}"


def _read_limited_response(response, *, limit=1_000_000) -> bytes:
    body = response.read(limit + 1)
    if len(body) > limit:
        raise StreamUnavailableError("stream_response_too_large")
    if str(response.headers.get("Content-Encoding") or "").lower() == "gzip":
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as compressed:
                body = compressed.read(limit + 1)
        except (OSError, EOFError) as error:
            raise StreamUnavailableError("invalid_stream_response") from error
        if len(body) > limit:
            raise StreamUnavailableError("stream_response_too_large")
    return body


def _cookie_web_version(cookie_jar: CookieJar) -> str:
    for cookie in cookie_jar:
        if cookie.name == "zmp3_app_version.1" and re.fullmatch(
            r"\d+\.\d+\.\d+", str(cookie.value or "")
        ):
            return cookie.value
    return ZING_WEB_VERSION


def _build_zing_api_url(song_id: str, version: str, current_time: int) -> str:
    params = {
        "id": song_id,
        "ctime": str(current_time),
        "version": version,
    }
    canonical = "".join(f"{key}={params[key]}" for key in sorted(params))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    signature = hmac.new(
        ZING_API_SECRET.encode(),
        f"{ZING_API_PATH}{digest}".encode(),
        hashlib.sha512,
    ).hexdigest()
    query = urlencode({**params, "apiKey": ZING_API_KEY, "sig": signature})
    return f"{ZING_API_BASE}{ZING_API_PATH}?{query}"


ZING_PLAYLIST_PATH = "/api/v2/page/get/playlist"


def zing_playlist_id(text: str) -> str | None:
    """Album/playlist id in a Zing MP3 link (/album/…/ID.html, /playlist/…/ID.html)."""
    parsed = urlsplit(str(text or "").strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not (host == "zingmp3.vn" or host.endswith(".zingmp3.vn")):
        return None
    if not parsed.path.startswith(("/album/", "/playlist/")):
        return None
    playlist_id = parsed.path.rsplit("/", 1)[-1].removesuffix(".html")
    return playlist_id if ZING_ID.fullmatch(playlist_id) else None


def fetch_zing_playlist(text: str, *, timeout: int = 20, now: int | None = None) -> tuple[str, list[dict]]:
    """(title, public songs) of a Zing MP3 album/playlist.

    Signed like the song stream API, only the path differs. Measured 14/09/2026 on
    album n1mqFnz65jGl: 28 songs, each with `streamingStatus` (1 playable, 2 VIP — skipped)."""
    playlist_id = zing_playlist_id(text)
    if playlist_id is None:
        raise ValueError("invalid_playlist_link")
    cookie_jar = CookieJar()
    opener = build_opener(_ZingRedirectHandler(), HTTPCookieProcessor(cookie_jar))
    home = f"{ZING_API_BASE}/"
    try:
        with opener.open(Request(home, headers={"User-Agent": ZING_USER_AGENT}), timeout=timeout) as response:
            response.read(1)
        params = {
            "id": playlist_id,
            "ctime": str(int(round(time.time()) if now is None else now)),
            "version": _cookie_web_version(cookie_jar),
        }
        digest = hashlib.sha256("".join(f"{key}={params[key]}" for key in sorted(params)).encode()).hexdigest()
        signature = hmac.new(
            ZING_API_SECRET.encode(), f"{ZING_PLAYLIST_PATH}{digest}".encode(), hashlib.sha512
        ).hexdigest()
        url = f"{ZING_API_BASE}{ZING_PLAYLIST_PATH}?{urlencode({**params, 'apiKey': ZING_API_KEY, 'sig': signature})}"
        with opener.open(
            Request(
                url,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "Referer": home,
                    "User-Agent": ZING_USER_AGENT,
                },
            ),
            timeout=timeout,
        ) as response:
            payload = json.loads(_read_limited_response(response, limit=4_000_000))
    except StreamUnavailableError:
        raise
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise StreamUnavailableError("stream_provider_failed") from error
    data = payload.get("data") if isinstance(payload, dict) and payload.get("err") == 0 else None
    if not isinstance(data, dict):
        raise StreamUnavailableError("stream_provider_failed")
    items = []
    for song in (data.get("song") or {}).get("items") or []:
        if not isinstance(song, dict) or song.get("streamingStatus") != 1:
            continue
        link = str(song.get("link") or "")
        song_id = str(song.get("encodeId") or "")
        if not link.startswith("/bai-hat/") or not ZING_ID.fullmatch(song_id):
            continue
        items.append({
            "source": "zing",
            "kind": "song",
            "id": song_id,
            "url": f"https://zingmp3.vn{link}",
            "title": str(song.get("title") or song_id),
            "channel": str(song.get("artistsNames") or ""),
            "duration": song.get("duration"),
            "thumbnail": str(song.get("thumbnailM") or song.get("thumbnail") or ""),
        })
    return str(data.get("title") or "Album Zing MP3"), items


def resolve_zing_stream(
    target_url: str, *, timeout: int = 30, now: int | None = None
) -> dict:
    """Resolve one browser-playable public Zing song without downloading it."""
    target_url = validate_zing_target(target_url)
    cookie_jar = CookieJar()
    opener = build_opener(_ZingRedirectHandler(), HTTPCookieProcessor(cookie_jar))
    try:
        with opener.open(
            Request(
                target_url,
                headers={
                    "Accept-Encoding": "identity",
                    "User-Agent": ZING_USER_AGENT,
                },
            ),
            timeout=timeout,
        ) as response:
            redirected_target = validate_zing_target(response.geturl())
            response.read(1)

        song_id = urlsplit(redirected_target).path.rsplit("/", 1)[-1].removesuffix(
            ".html"
        )
        api_url = _build_zing_api_url(
            song_id,
            _cookie_web_version(cookie_jar),
            int(round(time.time()) if now is None else now),
        )
        with opener.open(
            Request(
                api_url,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Encoding": "gzip",
                    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
                    "Referer": redirected_target,
                    "User-Agent": ZING_USER_AGENT,
                },
            ),
            timeout=timeout,
        ) as response:
            payload = json.loads(_read_limited_response(response))
    except StreamUnavailableError:
        raise
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise StreamUnavailableError("stream_provider_failed") from error

    if (
        not isinstance(payload, dict)
        or payload.get("err") != 0
        or not isinstance(payload.get("data"), dict)
    ):
        raise StreamUnavailableError("stream_provider_failed")

    streams = payload["data"]
    stream_url = next(
        (
            str(streams.get(quality) or "")
            for quality in ("320", "128")
            if str(streams.get(quality) or "").startswith(("http://", "https://"))
        ),
        "",
    )
    parsed_stream = urlsplit(stream_url)
    stream_host = (parsed_stream.hostname or "").lower()
    if (
        parsed_stream.scheme not in {"http", "https"}
        or not any(
            stream_host == suffix or stream_host.endswith(f".{suffix}")
            for suffix in ZING_CDN_HOSTS
        )
    ):
        raise StreamUnavailableError("unsupported_stream_format")
    extension = parsed_stream.path.rsplit(".", 1)[-1].lower()
    return {
        "url": stream_url,
        "headers": {
            "Referer": redirected_target,
            "User-Agent": ZING_USER_AGENT,
        },
        "content_type": CONTENT_TYPES.get(extension, "audio/mpeg"),
    }


def _youtube_audio_format(info: dict) -> dict:
    """Pick the concrete audio format yt-dlp selected from its JSON output."""
    if info.get("url"):
        return info
    requested = info.get("requested_downloads")
    if isinstance(requested, list) and requested and isinstance(requested[0], dict):
        return requested[0]
    formats = info.get("formats")
    if isinstance(formats, list):
        audio_only = [
            item
            for item in formats
            if isinstance(item, dict)
            and item.get("url")
            and item.get("acodec") not in (None, "none")
            and item.get("vcodec") in (None, "none")
        ]
        if audio_only:
            return audio_only[-1]
    raise StreamUnavailableError("stream_provider_failed")


def extract_with_yt_dlp(watch_url: str, timeout: int) -> dict:
    """Run yt-dlp inside this process and return what ``--dump-single-json`` prints.

    Measured 14/09/2026: a fresh ``yt-dlp`` process took 4.8-7.1 s per song, 2.2 s
    of it only importing yt_dlp; the same extraction in a long-lived process took
    1.1-1.8 s. That wait is the delay before a speaker starts and on every "next".
    """
    import yt_dlp  # imported on first use, then cached by Python

    options = {
        "format": YOUTUBE_AUDIO_FORMAT,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "socket_timeout": timeout,
        "extractor_retries": 1,
    }
    if deno := deno_path():
        options["js_runtimes"] = {"deno": {"path": deno}}
    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.sanitize_info(ydl.extract_info(watch_url, download=False))


def deno_path() -> str:
    """Deno for yt-dlp to solve YouTube's JavaScript challenges.

    Without one yt-dlp 2026.8 warns "YouTube extraction without a JS runtime has been
    deprecated, and some formats may be missing". The image installs Alpine's deno."""
    beside = Path(sys.executable).with_name("deno")
    if beside.is_file():
        return str(beside)
    return shutil.which("deno") or ""


def stream_cache_seconds(stream_url: str, *, now: float | None = None) -> int:
    """How long a resolved stream URL may be reused.

    googlevideo URLs carry their own ``expire`` (about six hours ahead); reusing
    them until shortly before that keeps replays, seeks and range requests from
    resolving the song again. URLs without an expiry keep the old two minutes."""
    try:
        expire = int(parse_qs(urlsplit(str(stream_url)).query).get("expire", [""])[0])
    except ValueError:
        return STREAM_CACHE_DEFAULT_SECONDS
    remaining = expire - int(time.time() if now is None else now) - STREAM_EXPIRY_MARGIN_SECONDS
    return max(0, min(remaining, STREAM_CACHE_MAX_SECONDS))


def _youtube_video_format(info: dict, max_height: int) -> dict:
    """The highest direct (https, not m3u8) picture-only stream not above `max_height`."""
    candidates = []
    for item in info.get("formats") or []:
        if not isinstance(item, dict) or not item.get("url") or item.get("protocol") not in ("https", "http"):
            continue
        codec = str(item.get("vcodec") or "none").lower()
        height = item.get("height")
        if codec == "none" or not isinstance(height, int) or height > max_height:
            continue
        if str(item.get("ext") or "").lower() not in VIDEO_CONTENT_TYPES:
            continue
        rank = next((len(YOUTUBE_VIDEO_CODECS) - i for i, name in enumerate(YOUTUBE_VIDEO_CODECS) if codec.startswith(name)), 0)
        # Highest first; at equal height the easier codec; picture-only before muxed.
        candidates.append((height, rank, item.get("acodec") in (None, "none"), float(item.get("tbr") or 0), item))
    if not candidates:
        raise StreamUnavailableError("unsupported_stream_format")
    return max(candidates, key=lambda c: c[:4])[4]


def resolve_youtube_video(target: str, *, timeout: int = 20, extractor=extract_with_yt_dlp) -> dict:
    """The picture (no sound) of a YouTube video for a browser <video> element.

    Used when YouTube refuses the embed (record-label videos when the page is opened by
    IP address). Measured 14/09/2026 in Chrome: avc1/vp9/av1 1080p picture-only streams
    play straight in <video> (1920×1080, ~30 fps)."""
    video_id, max_height = validate_stream_target("youtube_video", target).split(":")
    try:
        info = extractor(f"https://www.youtube.com/watch?v={video_id}", timeout)
    except Exception as error:  # yt-dlp raises many types for the same failure
        raise StreamUnavailableError("stream_provider_failed") from error
    if not isinstance(info, dict):
        raise StreamUnavailableError("invalid_stream_response")
    selected = _youtube_video_format(info, int(max_height))
    stream_url = str(selected["url"])
    stream_host = (urlsplit(stream_url).hostname or "").lower()
    if not any(stream_host == suffix or stream_host.endswith(f".{suffix}") for suffix in YOUTUBE_STREAM_HOSTS):
        raise StreamUnavailableError("unsupported_stream_format")
    headers = {"User-Agent": ZING_USER_AGENT}
    upstream_headers = selected.get("http_headers") or info.get("http_headers")
    if isinstance(upstream_headers, dict):
        headers = {str(key): str(value) for key, value in upstream_headers.items() if key and value} or headers
    return {
        "url": stream_url,
        "headers": headers,
        "content_type": VIDEO_CONTENT_TYPES[str(selected.get("ext")).lower()],
        "height": selected.get("height"),
        "bitrate_kbps": round(float(selected.get("tbr") or 0)),
    }


def resolve_youtube_audio(
    video_id: str, *, timeout: int = 20, extractor=extract_with_yt_dlp
) -> dict:
    """Resolve one browser-free direct audio stream for a public YouTube video.

    yt-dlp extracts a short-lived, IP-bound ``googlevideo.com`` URL; the caller
    relays it through the add-on so speakers never fetch YouTube directly.
    """
    video_id = validate_stream_target("youtube", video_id)
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        info = extractor(watch_url, timeout)
    except Exception as error:  # yt-dlp raises many unrelated types for one failure
        raise StreamUnavailableError("stream_provider_failed") from error
    if not isinstance(info, dict):
        raise StreamUnavailableError("invalid_stream_response")

    selected = _youtube_audio_format(info)
    stream_url = str(selected.get("url") or "")
    parsed_stream = urlsplit(stream_url)
    stream_host = (parsed_stream.hostname or "").lower()
    if parsed_stream.scheme not in {"http", "https"} or not any(
        stream_host == suffix or stream_host.endswith(f".{suffix}")
        for suffix in YOUTUBE_STREAM_HOSTS
    ):
        raise StreamUnavailableError("unsupported_stream_format")

    extension = str(selected.get("ext") or "").lower()
    headers = {"User-Agent": ZING_USER_AGENT}
    upstream_headers = selected.get("http_headers") or info.get("http_headers")
    if isinstance(upstream_headers, dict):
        headers = {
            str(key): str(value)
            for key, value in upstream_headers.items()
            if key and value
        } or headers
    return {
        "url": stream_url,
        "headers": headers,
        "content_type": CONTENT_TYPES.get(extension, "audio/mp4"),
    }


def _la_luong_chi_tieng(item: dict) -> bool:
    """Đúng khi mục này là luồng CHỈ CÓ TIẾNG.

    Bắt buộc `acodec` phải có thật, chứ không chỉ xét `vcodec` rỗng. Hai tệp gộp sẵn
    "hd"/"sd" của Facebook KHÔNG khai codec nào (yt-dlp báo NA cả hai), nên điều kiện
    chỉ dựa vào `vcodec` sẽ nhận nhầm chúng là luồng tiếng. Phép kiểm
    `test_audio_resolver_falls_back_to_the_muxed_file` đã bắt đúng lỗi đó: tệp sd bị
    gắn kiểu "audio/mp4" thay vì "video/mp4".

    Dùng CHUNG cho cả chỗ chọn định dạng lẫn chỗ quyết kiểu nội dung — hai nơi cùng
    một câu hỏi thì phải cùng một câu trả lời, tách ra là mầm lệch về sau."""
    return item.get("acodec") not in (None, "none") and item.get("vcodec") in (None, "none")


def _facebook_muxed_format(info: dict, *, want_hd: bool) -> dict:
    """Tệp mp4 gộp sẵn của Facebook: "hd" trước, "sd" dự phòng (hoặc ngược lại).

    Chọn theo MÃ ĐỊNH DẠNG chứ không theo codec/chiều cao — xem chú thích ở
    `FACEBOOK_MUXED_FORMATS`: yt-dlp báo ba trường đó là NA cho hai định dạng này."""
    found: dict[str, dict] = {}
    for item in info.get("formats") or []:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        name = str(item.get("format_id") or "").lower()
        if name in FACEBOOK_MUXED_FORMATS and str(item.get("ext") or "").lower() == "mp4":
            found.setdefault(name, item)
    for name in (("hd", "sd") if want_hd else ("sd", "hd")):
        if name in found:
            return found[name]
    # yt-dlp rút gọn về một luồng duy nhất khi người gọi đã chọn sẵn định dạng.
    if info.get("url") and str(info.get("ext") or "").lower() == "mp4":
        return info
    raise StreamUnavailableError("unsupported_stream_format")


def _facebook_audio_format(info: dict) -> dict:
    """Luồng CHỈ CÓ TIẾNG nếu Facebook có (đo được: m4a, mp4a.40.5, ~73 kbps, 48 kHz);
    không có thì dùng tệp gộp sẵn nhỏ hơn — loa vẫn phát ra tiếng từ mp4."""
    audio_only = [
        item
        for item in info.get("formats") or []
        if isinstance(item, dict) and item.get("url") and _la_luong_chi_tieng(item)
    ]
    if audio_only:
        return audio_only[-1]
    return _facebook_muxed_format(info, want_hd=False)


def _facebook_stream(video_id: str, selected: dict, info: dict) -> dict:
    """Kiểm máy chủ phát rồi dựng bản ghi luồng, đúng hình dạng của các nguồn khác."""
    stream_url = str(selected.get("url") or "")
    parsed_stream = urlsplit(stream_url)
    stream_host = (parsed_stream.hostname or "").lower()
    if parsed_stream.scheme not in {"http", "https"} or not any(
        stream_host == suffix or stream_host.endswith(f".{suffix}")
        for suffix in FACEBOOK_STREAM_HOSTS
    ):
        raise StreamUnavailableError("unsupported_stream_format")
    headers = {"User-Agent": ZING_USER_AGENT}
    upstream_headers = selected.get("http_headers") or info.get("http_headers")
    if isinstance(upstream_headers, dict):
        headers = {
            str(key): str(value)
            for key, value in upstream_headers.items()
            if key and value
        } or headers
    return {"url": stream_url, "headers": headers}


def _facebook_info(video_id: str, timeout: int, extractor) -> dict:
    try:
        info = extractor(f"https://www.facebook.com/watch/?v={video_id}", timeout)
    except Exception as error:  # yt-dlp ném nhiều loại cho cùng một kiểu hỏng
        raise StreamUnavailableError("stream_provider_failed") from error
    if not isinstance(info, dict):
        raise StreamUnavailableError("invalid_stream_response")
    return info


def resolve_facebook_audio(
    target: str, *, timeout: int = 20, extractor=extract_with_yt_dlp
) -> dict:
    """TIẾNG của một video Facebook, cho loa — tách riêng khỏi phần hình, đúng như
    cặp `youtube` / `youtube_video` đang làm."""
    video_id = validate_stream_target("facebook", target)
    info = _facebook_info(video_id, timeout, extractor)
    selected = _facebook_audio_format(info)
    stream = _facebook_stream(video_id, selected, info)
    extension = str(selected.get("ext") or "").lower()
    stream["content_type"] = (
        CONTENT_TYPES.get(extension, "audio/mp4")
        if _la_luong_chi_tieng(selected)
        else "video/mp4"
    )
    return stream


def resolve_facebook_video(
    target: str, *, timeout: int = 20, extractor=extract_with_yt_dlp
) -> dict:
    """HÌNH của một video Facebook cho thẻ <video> của trình duyệt.

    Khác bên YouTube ở một điểm đã đo: Facebook chỉ có tệp gộp sẵn, nên luồng này
    mang theo cả tiếng. Thẻ tự tắt tiếng khi đang phát ra loa, giống cách nó làm với
    video YouTube đi kèm loa."""
    video_id, max_height = validate_stream_target("facebook_video", target).split(":")
    info = _facebook_info(video_id, timeout, extractor)
    selected = _facebook_muxed_format(info, want_hd=int(max_height) >= 720)
    stream = _facebook_stream(video_id, selected, info)
    stream["content_type"] = VIDEO_CONTENT_TYPES.get(
        str(selected.get("ext") or "").lower(), "video/mp4"
    )
    if isinstance(selected.get("height"), int):
        stream["height"] = selected["height"]
    if selected.get("tbr"):
        stream["bitrate_kbps"] = round(float(selected["tbr"]))
    return stream
