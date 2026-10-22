"""Turn GNS3 data into a normalized "lab state" the renderer can use."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import discovery, gns3_api
from .config import Config

log = logging.getLogger(__name__)


@dataclass
class LabState:
    """Snapshot of what is currently happening in GNS3."""

    project_id: Optional[str] = None
    project_name: str = ""
    nodes: List[gns3_api.ApiNode] = field(default_factory=list)
    links: List[gns3_api.ApiLink] = field(default_factory=list)
    server_version: str = ""
    server_url: str = ""
    source: str = "none"  # api | files | none
    gns3_running: bool = False
    project_started_at: Optional[float] = None
    opened: bool = False

    @property
    def total(self) -> int:
        return len(self.nodes)

    @property
    def running(self) -> int:
        return sum(1 for node in self.nodes if node.is_running)

    @property
    def link_count(self) -> int:
        return len(self.links)

    @property
    def state_name(self) -> str:
        if not self.opened:
            return "closed"
        if self.running:
            return "running"
        if self.total:
            return "loaded"
        return "idle"

    def node_types(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for node in self.nodes:
            counts[node.node_type] = counts.get(node.node_type, 0) + 1
        return counts


def gns3_process_running() -> bool:
    """Best effort detection of a running GNS3 GUI/server."""
    if os.name == "nt":
        for image in ("gns3.exe", "gns3server.exe"):
            try:
                output = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {image}", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                ).stdout
                if image.lower() in output.lower():
                    return True
            except Exception:
                continue
        return False
    for binary in ("pgrep",):
        if shutil.which(binary):
            try:
                result = subprocess.run(
                    [binary, "-f", "gns3"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    return True
            except Exception:
                continue
    return False


class Gns3Watcher:
    """Polls GNS3 and produces a :class:`LabState`."""

    def __init__(self, config: Config):
        self.config = config
        self.endpoint: Optional[discovery.Endpoint] = None
        self.api: Optional[gns3_api.Gns3Api] = None
        self.projects_path: Optional[Path] = None
        self._last_scan = 0.0
        self._scan_interval = 60.0
        self._server_version = ""
        self._server_url = ""
        self._next_connect_at = 0.0

    # -- connection ------------------------------------------------------
    def connect(self) -> Optional[gns3_api.Gns3Api]:
        """Find a working GNS3 controller and keep it for later calls."""
        now = time.time()
        if now < self._next_connect_at:
            return None
        configured_url = str(self.config.get("gns3.url", "auto") or "auto")
        configured_path = str(self.config.get("gns3.projects_path", "auto") or "auto")
        candidates = discovery.candidate_endpoints(configured_url, configured_path)
        self.projects_path = discovery.resolved_projects_path(candidates)

        timeout = float(self.config.get("gns3.timeout", 5.0) or 5.0)
        username = str(self.config.get("gns3.username", "") or "")
        password = ""
        password_env = str(self.config.get("gns3.password_env", "") or "")
        if password_env:
            password = os.environ.get(password_env, "")

        # All candidates are probed in parallel: on a machine where several
        # ports are closed (firewall drop), a sequential probe would be slow.
        def _probe(candidate: discovery.Endpoint):
            api = gns3_api.Gns3Api(
                candidate.url, username=username or None, password=password, timeout=timeout
            )
            try:
                return candidate, api, api.version()
            except gns3_api.Gns3Error:
                return None

        results: Dict[int, Any] = {}
        if candidates:
            with ThreadPoolExecutor(max_workers=min(8, len(candidates))) as pool:
                for index, outcome in enumerate(pool.map(_probe, candidates)):
                    if outcome:
                        results[index] = outcome

        for index, candidate in enumerate(candidates):  # keep the priority order
            if index not in results:
                continue
            _, api, version = results[index]
            self.endpoint = candidate
            self.api = api
            self._server_version = str(
                version.get("version", "") or version.get("local_version", "") or ""
            )
            self._server_url = candidate.url
            log.info(
                "GNS3 controller found at %s (v%s, source: %s)",
                candidate.url,
                self._server_version or "?",
                candidate.source,
            )
            return api

        log.warning(
            "No GNS3 controller reachable (tried %s)", ", ".join(c.url for c in candidates)
        )
        self.endpoint = None
        self.api = None
        self._next_connect_at = time.time() + 30.0
        return None

    def _ensure_api(self) -> Optional[gns3_api.Gns3Api]:
        if self.api is not None:
            if self.api.ping():
                return self.api
            log.info("Lost connection to %s, rediscovery...", self._server_url)
            self.api = None
        return self.connect()

    # -- polling ---------------------------------------------------------
    def poll(self) -> LabState:
        api = self._ensure_api()
        state = LabState(gns3_running=gns3_process_running())
        if api is not None:
            try:
                return self._poll_api(api, state)
            except gns3_api.Gns3Error as exc:
                log.debug("API poll failed: %s", exc)
                self.api = None
        return self._poll_files(state)

    def _poll_api(self, api: gns3_api.Gns3Api, state: LabState) -> LabState:
        projects = api.list_projects()
        state.source = "api"
        state.server_url = self._server_url
        state.server_version = self._server_version
        state.gns3_running = True

        active = self._pick_project(projects)
        if active is None:
            active = self._pick_recent_project(projects)
        if active is None:
            state.opened = False
            return state

        state.opened = True
        state.project_id = active.project_id
        state.project_name = active.name
        state.nodes = api.list_nodes(active.project_id)
        state.links = api.list_links(active.project_id)
        gns3_file = active.gns3_file
        if gns3_file and gns3_file.exists():
            try:
                state.project_started_at = gns3_file.stat().st_mtime
            except OSError:
                state.project_started_at = None
        return state

    @staticmethod
    def _pick_project(projects: List[gns3_api.ApiProject]) -> Optional[gns3_api.ApiProject]:
        """The project currently opened in the GUI, else the only running one."""
        opened = [p for p in projects if p.opened or p.status.lower() == "opened"]
        if opened:
            return opened[0]
        running = [p for p in projects if p.node_count and p.status.lower() not in ("closed",)]
        if len(running) == 1:
            return running[0]
        return None

    def _pick_recent_project(
        self, projects: List[gns3_api.ApiProject]
    ) -> Optional[gns3_api.ApiProject]:
        """Safety net: the project whose ``.gns3`` file was touched recently.

        Useful when the controller does not report an opened project (remote
        controller, GNS3 VM, controller restarted by the GUI...).
        """
        minutes = float(self.config.get("gns3.fallback_recent_minutes", 10) or 0)
        if minutes <= 0:
            return None
        disk = gns3_api.scan_projects(self.projects_path)
        if not disk:
            return None
        latest = disk[0]
        age = time.time() - latest.mtime
        if age > minutes * 60:
            return None
        for project in projects:
            if project.name == latest.name:
                log.debug("Using recent project %s (modified %.0f s ago)", project.name, age)
                return project
        return None

    def _poll_files(self, state: LabState) -> LabState:
        """Fallback: read the ``.gns3`` files directly."""
        now = time.time()
        if now - self._last_scan < self._scan_interval:
            return state
        self._last_scan = now
        projects = gns3_api.scan_projects(self.projects_path)
        if not projects:
            state.source = "none"
            return state
        state.source = "files"
        latest = projects[0]
        state.opened = True
        state.project_id = latest.project_id
        state.project_name = latest.name
        state.nodes = latest.nodes
        state.links = latest.links
        state.project_started_at = latest.mtime
        return state


def guess_console_command() -> str:  # pragma: no cover - convenience helper
    return f"{Path(sys.executable).name} --check"
