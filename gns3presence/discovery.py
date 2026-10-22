"""Discovery of the local (or remote) GNS3 server.

The whole point of this module is portability: nothing about the GNS3
installation is hardcoded. We look, in order, at:

1. ``[gns3] url`` from the user configuration,
2. the ``GNS3_URL`` environment variable,
3. the GNS3 server configuration file (``gns3_server.ini`` / ``.conf``),
4. the servers declared by the GUI (``gns3_gui.ini`` -> ``Servers``),
5. the usual local ports (3080, 80, 8000, 8080).

Whatever answers ``GET /v2/version`` wins.
"""

from __future__ import annotations

import configparser
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

DEFAULT_PORTS = (3080, 80, 8000, 8080)
SERVER_FILE_NAMES = ("gns3_server.ini", "gns3_server.conf", "gns3_server_run.conf")
GUI_FILE_NAMES = ("gns3_gui.ini", "gns3_gui.conf")


@dataclass
class Gns3ServerSettings:
    """Values extracted from the GNS3 server configuration file."""

    host: str = "localhost"
    port: int = 3080
    protocol: str = "http"
    auth: bool = False
    username: str = ""
    projects_path: Optional[str] = None
    source: Optional[Path] = None

    @property
    def base_url(self) -> str:
        host = self.host
        if host in ("0.0.0.0", "::", ""):
            host = "localhost"
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"{self.protocol}://{host}:{self.port}"


@dataclass
class Endpoint:
    """A candidate GNS3 controller URL with the reason it was proposed."""

    url: str
    source: str
    settings: Optional[Gns3ServerSettings] = None
    extra: Dict[str, Any] = field(default_factory=dict)


def gns3_config_dirs() -> List[Path]:
    """Directories where GNS3 stores its per-user configuration."""
    dirs: List[Path] = []
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            dirs.append(Path(base) / "GNS3")
    else:
        home = Path.home()
        dirs.append(home / ".config" / "GNS3")
        dirs.append(home / "Library" / "Application Support" / "GNS3")
    dirs.append(Path("/etc/gns3"))
    return [d for d in dirs if d.is_dir()]


def find_server_files() -> List[Path]:
    """All GNS3 server configuration files found on this machine."""
    files: List[Path] = []
    for directory in gns3_config_dirs():
        for name in SERVER_FILE_NAMES:
            direct = directory / name
            if direct.is_file():
                files.append(direct)
            # GNS3 2.x keeps one folder per version: %APPDATA%/GNS3/2.2/gns3_server.ini
            try:
                for child in sorted(directory.iterdir()):
                    if not child.is_dir():
                        continue
                    candidate = child / name
                    if candidate.is_file():
                        files.append(candidate)
            except OSError:
                continue
    return files


def find_gui_files() -> List[Path]:
    files: List[Path] = []
    for directory in gns3_config_dirs():
        for name in GUI_FILE_NAMES:
            direct = directory / name
            if direct.is_file():
                files.append(direct)
            try:
                for child in sorted(directory.iterdir()):
                    if not child.is_dir():
                        continue
                    candidate = child / name
                    if candidate.is_file():
                        files.append(candidate)
            except OSError:
                continue
    return files


def parse_server_settings(path: Path) -> Optional[Gns3ServerSettings]:
    """Parse a GNS3 server INI file."""
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    try:
        parser.read(path, encoding="utf-8")
    except Exception as exc:
        log.debug("Cannot read %s: %s", path, exc)
        return None
    if not parser.has_section("Server"):
        return None
    section = parser["Server"]

    def _get(key: str, default: str = "") -> str:
        return str(section.get(key, default) or default).strip()

    port_text = _get("port", "3080")
    try:
        port = int(port_text)
    except ValueError:
        port = 3080
    protocol = _get("protocol", "http") or "http"
    host = _get("host", "localhost") or "localhost"
    auth_text = _get("auth", "False").lower()
    auth = auth_text in ("1", "true", "yes", "on")
    return Gns3ServerSettings(
        host=host,
        port=port,
        protocol=protocol,
        auth=auth,
        username=_get("user", ""),
        projects_path=_get("projects_path", "") or None,
        source=path,
    )


def server_settings() -> List[Gns3ServerSettings]:
    """All server settings found on the machine (most recent file first)."""
    results: List[Gns3ServerSettings] = []
    for path in find_server_files():
        settings = parse_server_settings(path)
        if settings:
            results.append(settings)
    results.sort(key=lambda s: s.source.stat().st_mtime if s.source else 0, reverse=True)
    return results


def gui_servers() -> List[Endpoint]:
    """Remote servers declared by the GNS3 GUI (``gns3_gui.ini``)."""
    endpoints: List[Endpoint] = []
    for path in find_gui_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        servers = data.get("Servers") if isinstance(data, dict) else None
        if not isinstance(servers, dict):
            continue
        for name, server in servers.items():
            if not isinstance(server, dict):
                continue
            host = server.get("host") or "localhost"
            try:
                port = int(server.get("port", 3080))
            except (TypeError, ValueError):
                port = 3080
            protocol = server.get("protocol", "http") or "http"
            if host in ("0.0.0.0", "::", ""):
                host = "localhost"
            endpoints.append(
                Endpoint(
                    url=f"{protocol}://{host}:{port}",
                    source=f"gns3_gui.ini ({name})",
                )
            )
    return endpoints


def candidate_endpoints(
    configured_url: str = "auto",
    projects_path: str = "auto",
) -> List[Endpoint]:
    """Build the ordered list of candidate GNS3 controllers."""
    candidates: List[Endpoint] = []
    seen = set()

    def _add(url: str, source: str, settings: Optional[Gns3ServerSettings] = None) -> None:
        url = url.rstrip("/")
        if not url or url in seen:
            return
        if "://" not in url:
            url = f"http://{url}"
        seen.add(url)
        candidates.append(Endpoint(url=url, source=source, settings=settings))

    if configured_url and configured_url.lower() != "auto":
        _add(configured_url, "configuration file")

    env_url = os.environ.get("GNS3_URL")
    if env_url:
        _add(env_url, "GNS3_URL environment variable")

    settings_list = server_settings()
    for settings in settings_list:
        _add(settings.base_url, f"GNS3 configuration ({settings.source.name})", settings)

    for endpoint in gui_servers():
        _add(endpoint.url, endpoint.source)

    for port in DEFAULT_PORTS:
        _add(f"http://localhost:{port}", f"default port {port}")

    # Keep the projects path of the most recent server file for the fallback.
    if projects_path and projects_path.lower() != "auto":
        for candidate in candidates:
            candidate.extra.setdefault("projects_path", projects_path)
    elif settings_list:
        for candidate in candidates:
            candidate.extra.setdefault(
                "projects_path", settings_list[0].projects_path or ""
            )
    return candidates


def resolved_projects_path(candidates: List[Endpoint]) -> Optional[Path]:
    """Best guess of the directory holding the ``.gns3`` project files."""
    for candidate in candidates:
        raw = candidate.extra.get("projects_path")
        if raw:
            path = Path(raw).expanduser()
            if path.is_dir():
                return path
    for candidate in candidates:
        settings = candidate.settings
        if settings and settings.projects_path:
            path = Path(settings.projects_path).expanduser()
            if path.is_dir():
                return path
    return None
