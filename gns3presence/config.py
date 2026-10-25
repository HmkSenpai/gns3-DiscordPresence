"""Configuration handling: defaults, TOML loading, deep merge, hot reload."""

from __future__ import annotations

import copy
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # Python >= 3.11
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.9/3.10
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:  # pragma: no cover
        tomllib = None  # type: ignore[assignment]

from .log import user_data_dir

log = logging.getLogger(__name__)

CONFIG_FILENAME = "config.toml"

#: Everything that can be tweaked. A user file only needs to contain the keys
#: it wants to change, everything else falls back to these values.
DEFAULTS: Dict[str, Any] = {
    "discord": {
        # Application ID from https://discord.com/developers/applications
        "app_id": "",
        # Seconds between two GNS3 polls.
        "poll_interval": 15,
        # Hard floor between two Discord updates (Discord rate limit is ~5/20s).
        "min_update_interval": 15,
        # Remove the presence when nothing is running.
        "clear_when_idle": True,
    },
    "gns3": {
        # "auto" -> discovery (ini file, env var, port probing).
        "url": "auto",
        "username": "",
        # Environment variable holding the password (never stored in clear here).
        "password_env": "GNS3_PASSWORD",
        "timeout": 3.0,
        # "auto" -> read from the GNS3 server configuration file.
        "projects_path": "auto",
        # If the controller reports no opened project, fall back on the project
        # file modified within the last N minutes (0 disables the fallback).
        "fallback_recent_minutes": 10,
    },
    "presence": {
        "preset": "student",
        "details": "{project}",
        "state": "{running}/{total} nœuds · {links} liens",
        "large_image": "gns3",
        "large_text": "GNS3 {version}",
        "small_image": "{dominant_type}",
        "small_text": "{dominant_label}",
        "timestamp": "project",  # project | session | none
        "party": True,
        "buttons": [],
        "idle": {
            "details": "Au repos",
            "state": "Prêt pour un nouveau lab",
            "large_image": "idle",
            "large_text": "GNS3",
            "small_image": "",
            "small_text": "",
        },
    },
    "privacy": {
        "enabled": False,
        "patterns": ["exam", "examen", "cc", "concours", "eval", "noté", "corrigé"],
        "hide_node_names": True,
        "replacement": "Un lab réseau",
        "hide_buttons": True,
    },
    "images": {
        "router": "router",
        "switch": "switch",
        "pc": "pc",
        "firewall": "firewall",
        "vm": "vm",
        "unknown": "gns3",
    },
    "categories": {
        "router": ["dynamips", "iou", "router", "cisco"],
        "switch": ["ethernet_switch", "frame_relay_switch", "atm_switch", "switch"],
        "pc": ["vpcs", "pc", "virtual_pc", "workstation"],
        "firewall": ["firewall", "asa", "fortigate", "pfsense"],
        "vm": ["qemu", "vmware", "virtualbox", "hyper-v", "docker", "linux"],
    },
    "language": "fr",
    # Per-project overrides, first match wins.
    "rules": [],
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base``."""
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def portable_dir() -> Path:
    """Directory of the running script/executable - used for portable installs."""
    if getattr(sys, "frozen", False):  # PyInstaller / Nuitka
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def default_user_config() -> Path:
    return user_data_dir() / CONFIG_FILENAME


def candidate_config_paths(explicit: Optional[str] = None) -> List[Path]:
    """Ordered list of configuration files to look at."""
    paths: List[Path] = []
    if explicit:
        paths.append(Path(explicit).expanduser())
    env_path = os.environ.get("GNS3_PRESENCE_CONFIG")
    if env_path:
        paths.append(Path(env_path).expanduser())
    paths.append(portable_dir() / CONFIG_FILENAME)
    paths.append(default_user_config())
    return paths


class Config:
    """Loaded configuration with hot-reload support."""

    def __init__(
        self,
        data: Dict[str, Any],
        path: Optional[Path],
        mtime: float = 0.0,
        user_data: Optional[Dict[str, Any]] = None,
    ):
        self.data = data
        self.path = path
        self.mtime = mtime
        #: Raw content of the user file (empty when the defaults are used).
        self.user_data = user_data or {}

    # -- accessors -------------------------------------------------------
    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def user_set(self, dotted: str) -> bool:
        """Was this key explicitly set by the user (not a default)?"""
        node: Any = self.user_data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True

    @property
    def app_id(self) -> str:
        return str(self.get("discord.app_id", "") or "").strip()

    @property
    def rules(self) -> List[Dict[str, Any]]:
        rules = self.get("rules", [])
        return [r for r in rules if isinstance(r, dict)]

    def fingerprint(self) -> float:
        return self.mtime

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self.data)


def _read_toml(path: Path) -> Dict[str, Any]:
    if tomllib is None:  # pragma: no cover
        raise RuntimeError(
            "No TOML parser available. Install 'tomli' (pip install tomli) on Python < 3.11."
        )
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_config(explicit: Optional[str] = None) -> Config:
    """Load the configuration file, falling back to defaults."""
    errors: List[str] = []
    for candidate in candidate_config_paths(explicit):
        if not candidate.exists():
            continue
        try:
            user_data = _read_toml(candidate)
        except Exception as exc:
            message = f"{candidate}: {exc}"
            errors.append(message)
            log.error("Cannot parse %s", message)
            log.error(
                "The configuration file is invalid: the default settings are used. "
                "Fix or delete the file to restore your customisations."
            )
            continue
        log.info("Configuration loaded from %s", candidate)
        merged = deep_merge(DEFAULTS, user_data)
        mtime = candidate.stat().st_mtime
        return Config(merged, candidate, mtime, user_data)

    for message in errors:
        log.warning("Configuration error -> %s", message)
    log.info("No configuration file found, using built-in defaults")
    return Config(deep_merge(DEFAULTS, {}), None, 0.0)


def reload_if_changed(config: Config, explicit: Optional[str] = None) -> Config:
    """Return a reloaded configuration when the file changed on disk."""
    if config.path is None or not config.path.exists():
        return config
    try:
        mtime = config.path.stat().st_mtime
    except OSError:
        return config
    if mtime == config.mtime:
        return config
    log.info("Configuration file changed, reloading %s", config.path)
    return load_config(explicit or str(config.path))
