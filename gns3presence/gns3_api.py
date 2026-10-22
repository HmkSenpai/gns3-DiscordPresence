"""Minimal GNS3 REST API client (stdlib only) plus a filesystem fallback.

The API is the v2 controller API:

    GET /v2/version
    GET /v2/projects
    GET /v2/projects/{project_id}
    GET /v2/projects/{project_id}/nodes
    GET /v2/projects/{project_id}/links
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


class Gns3Error(Exception):
    """Raised when the GNS3 API cannot be reached or answers an error."""


@dataclass
class ApiNode:
    node_id: str = ""
    name: str = ""
    node_type: str = ""
    status: str = ""
    compute_id: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_running(self) -> bool:
        return str(self.status).lower() == "started"


@dataclass
class ApiLink:
    link_id: str = ""
    nodes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ApiProject:
    project_id: str = ""
    name: str = ""
    status: str = ""
    path: str = ""
    filename: str = ""
    node_count: int = 0
    link_count: int = 0
    opened: bool = False

    @property
    def gns3_file(self) -> Optional[Path]:
        if self.filename:
            return Path(self.filename)
        if self.path:
            return Path(self.path) / (self.name + ".gns3")
        return None


class Gns3Api:
    """Tiny HTTP client for the GNS3 controller API."""

    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 5.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._auth_header: Optional[str] = None
        if username:
            token = base64.b64encode(f"{username}:{password or ''}".encode()).decode()
            self._auth_header = f"Basic {token}"

    # -- low level -------------------------------------------------------
    def _request(self, path: str, method: str = "GET") -> Any:
        url = f"{self.base_url}{path}"
        request = urllib.request.Request(url, method=method)
        request.add_header("Accept", "application/json")
        if self._auth_header:
            request.add_header("Authorization", self._auth_header)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise Gns3Error(f"{method} {url} -> HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise Gns3Error(f"{method} {url} -> {exc.reason}") from exc
        except OSError as exc:
            raise Gns3Error(f"{method} {url} -> {exc}") from exc
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise Gns3Error(f"{method} {url} -> invalid JSON ({exc})") from exc

    # -- endpoints -------------------------------------------------------
    def version(self) -> Dict[str, Any]:
        data = self._request("/v2/version")
        return data if isinstance(data, dict) else {}

    def ping(self) -> bool:
        try:
            self.version()
            return True
        except Gns3Error:
            return False

    def list_projects(self) -> List[ApiProject]:
        data = self._request("/v2/projects")
        projects: List[ApiProject] = []
        for item in data if isinstance(data, list) else []:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status", "") or "")
            projects.append(
                ApiProject(
                    project_id=str(item.get("project_id", item.get("id", "")) or ""),
                    name=str(item.get("name", "") or ""),
                    status=status,
                    path=str(item.get("path", "") or ""),
                    filename=str(item.get("filename", "") or ""),
                    node_count=int(item.get("node_count", 0) or 0),
                    link_count=int(item.get("link_count", 0) or 0),
                    opened=status.lower() == "opened",
                )
            )
        return projects

    def list_nodes(self, project_id: str) -> List[ApiNode]:
        data = self._request(f"/v2/projects/{project_id}/nodes")
        nodes: List[ApiNode] = []
        for item in data if isinstance(data, list) else []:
            if not isinstance(item, dict):
                continue
            properties = item.get("properties")
            nodes.append(
                ApiNode(
                    node_id=str(item.get("node_id", item.get("id", "")) or ""),
                    name=str(item.get("name", "") or ""),
                    node_type=str(item.get("node_type", "") or ""),
                    status=str(item.get("status", "") or ""),
                    compute_id=str(item.get("compute_id", "") or ""),
                    properties=properties if isinstance(properties, dict) else {},
                )
            )
        return nodes

    def list_links(self, project_id: str) -> List[ApiLink]:
        data = self._request(f"/v2/projects/{project_id}/links")
        links: List[ApiLink] = []
        for item in data if isinstance(data, list) else []:
            if not isinstance(item, dict):
                continue
            links.append(
                ApiLink(
                    link_id=str(item.get("link_id", item.get("id", "")) or ""),
                    nodes=item.get("nodes") if isinstance(item.get("nodes"), list) else [],
                )
            )
        return links


# ---------------------------------------------------------------------------
# Filesystem fallback (no server needed)
# ---------------------------------------------------------------------------


@dataclass
class DiskProject:
    project_id: str
    name: str
    path: Path
    nodes: List[ApiNode]
    links: List[ApiLink]
    mtime: float
    opened: bool = True


def read_project_file(path: Path) -> Optional[DiskProject]:
    """Parse a ``.gns3`` topology file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.debug("Cannot parse %s: %s", path, exc)
        return None
    if not isinstance(data, dict):
        return None
    topology = data.get("topology") if isinstance(data.get("topology"), dict) else {}
    nodes: List[ApiNode] = []
    for item in topology.get("nodes", []) or []:
        if not isinstance(item, dict):
            continue
        properties = item.get("properties")
        nodes.append(
            ApiNode(
                node_id=str(item.get("node_id", "") or ""),
                name=str(item.get("name", "") or ""),
                node_type=str(item.get("node_type", "") or ""),
                status="",  # unknown without a running server
                compute_id=str(item.get("compute_id", "") or ""),
                properties=properties if isinstance(properties, dict) else {},
            )
        )
    links: List[ApiLink] = []
    for item in topology.get("links", []) or []:
        if not isinstance(item, dict):
            continue
        links.append(
            ApiLink(
                link_id=str(item.get("link_id", "") or ""),
                nodes=item.get("nodes") if isinstance(item.get("nodes"), list) else [],
            )
        )
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    return DiskProject(
        project_id=str(data.get("project_id", "") or path.stem),
        name=str(data.get("name", path.stem) or path.stem),
        path=path,
        nodes=nodes,
        links=links,
        mtime=mtime,
    )


def scan_projects(projects_path: Optional[Path]) -> List[DiskProject]:
    """Find every ``.gns3`` file below ``projects_path`` (most recent first)."""
    if not projects_path or not projects_path.is_dir():
        return []
    projects: List[DiskProject] = []
    try:
        for file in projects_path.rglob("*.gns3"):
            project = read_project_file(file)
            if project:
                projects.append(project)
    except OSError as exc:
        log.debug("Cannot scan %s: %s", projects_path, exc)
    projects.sort(key=lambda p: p.mtime, reverse=True)
    return projects
