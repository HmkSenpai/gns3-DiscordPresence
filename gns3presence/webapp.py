"""Local web interface used to customise the presence graphically.

The server listens on 127.0.0.1 only, serves a single page and a small JSON
API. Nothing leaves the machine: the settings are written to the local
configuration file.

Launch it with::

    gns3-presence --web
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import socket
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .config import Config
from .editor import (
    CHOICES,
    TEXT_FIELDS,
    TOGGLES,
    UiSettings,
    reset_settings,
    save_settings,
    settings_from_config,
)
from .render import Renderer
from .state import Gns3Watcher

log = logging.getLogger(__name__)

DEFAULT_PORT = 8765
MAX_PORT_ATTEMPTS = 20


def find_free_port(start: int = DEFAULT_PORT, attempts: int = MAX_PORT_ATTEMPTS) -> int:
    """Return the first free TCP port, starting at ``start``."""
    for offset in range(attempts):
        port = start + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise OSError(f"Aucun port libre entre {start} et {start + attempts - 1}")


def build_state(config: Config, watcher: Optional[Gns3Watcher]) -> Dict[str, Any]:
    """Current state of the lab, used by the preview."""
    if watcher is None:
        watcher = Gns3Watcher(config)
    state = watcher.poll()
    return {
        "state": state.state_name,
        "project": state.project_name,
        "running": state.running,
        "total": state.total,
        "links": state.link_count,
        "source": state.source,
        "server_version": state.server_version,
    }


def build_preview(config: Config, settings: Optional[UiSettings], watcher: Gns3Watcher) -> Dict[str, Any]:
    """Render the activity as it would be published, with the given settings."""
    if settings is not None:
        from .editor import changes_from_settings

        merged = config.data
        changes = changes_from_settings(settings, settings)
        for key, value in changes.items():
            node = merged
            parts = key.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value
        from .config import Config

        config = Config(merged, config.path, config.mtime, config.user_data)
    activity = Renderer(config).render(watcher.poll())
    return activity.as_dict()


class WebApp:
    """Holds the state shared by the HTTP handlers."""

    def __init__(
        self,
        config: Config,
        config_path: Path,
        watcher: Optional[Gns3Watcher] = None,
        on_saved: Optional[Callable[[], None]] = None,
    ):
        self.config = config
        self.config_path = config_path
        self.watcher = watcher or Gns3Watcher(config)
        self.on_saved = on_saved
        self.token = secrets.token_urlsafe(16)
        self.lock = threading.Lock()


def make_handler(app: WebApp):
    class Handler(BaseHTTPRequestHandler):
        server_version = "GNS3Presence"
        protocol_version = "HTTP/1.1"

        # -- helpers -------------------------------------------------------
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            log.debug("web %s", format % args)

        def handle_one_request(self) -> None:
            """Handle a request without crashing on a client that disconnects."""
            try:
                super().handle_one_request()
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                self.close_connection = True

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionAbortedError):
                pass

        def _json(self, payload: Dict[str, Any], code: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(code, body, "application/json; charset=utf-8")

        def _html(self, body: str) -> None:
            self._send(200, body.encode("utf-8"), "text/html; charset=utf-8")

        def _authorised(self, query: Dict[str, list]) -> bool:
            token = (query.get("token") or [""])[0]
            header = self.headers.get("X-Preset-Token", "")
            return secrets.compare_digest(token or header, app.token)

        # -- routes -------------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            path = parsed.path

            if path in ("/", "/index.html"):
                if not self._authorised(query):
                    self._send(403, b"Token invalide", "text/plain; charset=utf-8")
                    return
                self._html(render_page(app.token))
                return

            if path == "/api/state":
                if not self._authorised(query):
                    self._json({"error": "unauthorized"}, 403)
                    return
                with app.lock:
                    config = app.config
                    settings = settings_from_config(config)
                    state = build_state(config, app.watcher)
                    preview = build_preview(config, None, app.watcher)
                self._json(
                    {
                        "settings": settings.to_dict(),
                        "toggles": TOGGLES,
                        "choices": CHOICES,
                        "texts": TEXT_FIELDS,
                        "lab": state,
                        "preview": preview,
                        "config_path": str(app.config_path),
                    }
                )
                return

            self._send(404, b"Not found", "text/plain; charset=utf-8")

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            path = parsed.path

            if path == "/api/preview":
                if not self._authorised(query):
                    self._json({"error": "unauthorized"}, 403)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0") or 0)
                    payload = json.loads(self.rfile.read(length) or b"{}")
                except Exception:
                    self._json({"error": "invalid json"}, 400)
                    return
                settings = UiSettings(payload.get("settings", {}))
                with app.lock:
                    preview = build_preview(app.config, settings, app.watcher)
                self._json({"preview": preview})
                return

            if path == "/api/save":
                if not self._authorised(query):
                    self._json({"error": "unauthorized"}, 403)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0") or 0)
                    payload = json.loads(self.rfile.read(length) or b"{}")
                except Exception:
                    self._json({"error": "invalid json"}, 400)
                    return
                settings = UiSettings(payload.get("settings", {}))
                with app.lock:
                    if payload.get("reset"):
                        ok, message = reset_settings(app.config_path)
                        if ok:
                            app.config = reload_config(app.config, app.config_path)
                            if app.on_saved:
                                app.on_saved()
                            preview = build_preview(app.config, None, app.watcher)
                        self._json(
                            {"ok": ok, "message": message, "preview": preview if ok else None}
                        )
                        return
                    ok, message = save_settings(app.config_path, settings)
                    if ok:
                        app.config = reload_config(app.config, app.config_path)
                        if app.on_saved:
                            app.on_saved()
                        preview = build_preview(app.config, None, app.watcher)
                self._json(
                    {"ok": ok, "message": message, "preview": preview if ok else None}
                )
                return

            if path == "/api/pause":
                if not self._authorised(query):
                    self._json({"error": "unauthorized"}, 403)
                    return
                app.paused = not getattr(app, "paused", False)
                self._json({"ok": True, "paused": app.paused})
                return

            self._send(404, b"Not found", "text/plain; charset=utf-8")

    return Handler


def reload_config(config: Config, path: Path) -> Config:
    """Reload the configuration after the web interface changed it."""
    from .config import DEFAULTS, deep_merge

    data = toml_read(path)
    return Config(deep_merge(DEFAULTS, data), path, path.stat().st_mtime if path.exists() else 0.0, data)


def toml_read(path: Path) -> Dict[str, Any]:
    from . import toml_edit

    return toml_edit.read_toml(path)


def start_web_app(
    config: Config,
    config_path: Path,
    watcher: Optional[Gns3Watcher] = None,
    port: int = DEFAULT_PORT,
    open_browser: bool = True,
    on_saved: Optional[Callable[[], None]] = None,
) -> Tuple[ThreadingHTTPServer, str]:
    """Start the web interface in a background thread.

    Returns the server and the URL to open.
    """
    real_port = find_free_port(port)
    app = WebApp(config, config_path, watcher, on_saved)
    handler = make_handler(app)
    server = ThreadingHTTPServer(("127.0.0.1", real_port), handler)
    url = f"http://127.0.0.1:{real_port}/?token={app.token}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log.info("Web interface started on %s", url)
    if open_browser:
        opened = False
        try:
            opened = bool(webbrowser.open(url))
        except Exception:  # pragma: no cover
            opened = False
        if not opened:
            # The browser could not be opened: give the URL to the user.
            try:
                if os.name == "nt":
                    subprocess.run(["clip"], input=url, text=True, check=False)
                else:
                    subprocess.run(["pbcopy"], input=url, text=True, check=False)
            except Exception:
                pass
            log.warning("Could not open the browser, the URL has been copied to the clipboard")
    return server, url


from .render_page import render_page  # noqa: E402  (imported late to avoid a cycle)
