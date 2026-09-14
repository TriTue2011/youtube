"""Config flow: a player served under a path prefix (c2a serves the player API at /yt)."""

from __future__ import annotations

import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "youtube_player" / "app"))
sys.path.insert(0, str(ROOT))

import server as addon  # noqa: E402
from custom_components.tritue_youtube_player.config_flow import (  # noqa: E402
    InvalidUrlError,
    normalize_base_url,
)

TOKEN = "t" * 40


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def prefixed_player(socket_enabled):
    """The real add-on server behind a reverse proxy that only answers under /yt."""
    player = addon.create_server(host="127.0.0.1", port=0, data_dir=tempfile.mkdtemp(), app_title="Thu",
                                 max_history=5, integration_token=TOKEN)
    threading.Thread(target=player.serve_forever, daemon=True).start()
    upstream = f"http://127.0.0.1:{player.server_address[1]}"

    class Proxy(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            import urllib.error
            import urllib.request

            if not self.path.startswith("/yt/"):
                body = b"<html>c2a web</html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            request = urllib.request.Request(upstream + self.path[3:], headers={"Authorization": self.headers.get("Authorization", "")})
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    status, body, kind = response.status, response.read(), response.headers.get("Content-Type", "")
            except urllib.error.HTTPError as error:
                status, body, kind = error.code, error.read(), error.headers.get("Content-Type", "")
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    proxy = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{proxy.server_address[1]}"
    proxy.shutdown()
    player.shutdown()


def test_base_url_keeps_a_path_prefix():
    assert normalize_base_url(" http://172.16.10.38:3030/yt/ ") == "http://172.16.10.38:3030/yt"
    assert normalize_base_url("http://172.16.10.200:8099/") == "http://172.16.10.200:8099"
    for bad in ("ftp://host/yt", "http://host/yt?x=1", "http://user:pw@host/yt", "http://host/yt#a", "http://host/a b"):
        with pytest.raises(InvalidUrlError):
            normalize_base_url(bad)


async def test_user_flow_accepts_the_c2a_style_url(hass, prefixed_player):
    result = await hass.config_entries.flow.async_init("tritue_youtube_player", context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url": f"{prefixed_player}/yt/", "token": TOKEN})
    assert result["type"] == "create_entry", result
    assert result["data"]["url"] == f"{prefixed_player}/yt"
