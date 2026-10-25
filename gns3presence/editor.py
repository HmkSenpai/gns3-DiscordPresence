"""Model of the web interface: which settings are exposed and how they map
to the configuration file.

The web UI works on a flat, simple model (booleans and strings) while the
configuration file uses templates. This module converts between the two.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import toml_edit
from .config import Config

#: Settings exposed as a checkbox.
TOGGLES: List[Dict[str, Any]] = [
    {
        "key": "presence.show_project",
        "label": "Montrer le nom du projet",
        "help": "Affiche le nom du lab (TP0-CamTrust, Examen final...).",
        "default": True,
    },
    {
        "key": "presence.show_nodes",
        "label": "Montrer les noeuds demarres",
        "help": "Affiche le compteur de noeuds actifs.",
        "default": True,
    },
    {
        "key": "presence.show_links",
        "label": "Montrer le nombre de liens",
        "help": "Ajoute le nombre de cables du lab.",
        "default": True,
    },
    {
        "key": "presence.show_summary",
        "label": "Montrer le resume des equipements",
        "help": "3 routeurs - 2 switchs - 3 PC.",
        "default": False,
    },
    {
        "key": "presence.show_elapsed",
        "label": "Montrer le temps ecoule",
        "help": "Affiche la duree depuis l'ouverture du lab.",
        "default": False,
    },
    {
        "key": "presence.show_device_icon",
        "label": "Montrer l'icone de l'equipement",
        "help": "Petite icone : routeur, switch, PC...",
        "default": True,
    },
    {
        "key": "presence.show_party",
        "label": "Montrer le compteur x sur y",
        "help": "Le compteur affiche par Discord a cote de l'activite.",
        "default": True,
    },
    {
        "key": "presence.show_buttons",
        "label": "Montrer les boutons",
        "help": "Les liens cliquables de l'activite.",
        "default": True,
    },
]

#: Settings exposed as a select.
CHOICES: List[Dict[str, Any]] = [
    {
        "key": "presence.preset",
        "label": "Style d'affichage",
        "options": ["minimal", "student", "teacher", "streamer", "compact"],
        "default": "student",
    },
    {
        "key": "presence.large_image",
        "label": "Icone principale",
        "options": ["gns3", "router", "switch", "pc", "firewall", "vm", "idle"],
        "default": "gns3",
    },
    {
        "key": "presence.timestamp",
        "label": "Horodatage",
        "options": ["project", "session", "none"],
        "default": "project",
    },
    {
        "key": "language",
        "label": "Langue",
        "options": ["fr", "en"],
        "default": "fr",
    },
]

#: Settings exposed as a free text field.
TEXT_FIELDS: List[Dict[str, Any]] = [
    {
        "key": "presence.details",
        "label": "Ligne du titre (details)",
        "placeholder": "{project}",
        "default": "{project}",
    },
    {
        "key": "presence.state",
        "label": "Ligne du detail (state)",
        "placeholder": "{running}/{total} {t_nodes}",
        "default": "{running}/{total} {t_nodes}",
    },
]


@dataclass
class UiSettings:
    """Flat view of the settings manipulated by the web interface."""

    values: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.values)


def _template_for(toggle: Dict[str, Any], current: Dict[str, Any]) -> Optional[str]:
    """Build the state template matching the enabled parts."""
    show_nodes = current.get("presence.show_nodes", True)
    show_links = current.get("presence.show_links", True)
    show_summary = current.get("presence.show_summary", False)
    show_elapsed = current.get("presence.show_elapsed", False)

    parts: List[str] = []
    if show_nodes:
        parts.append("{running}/{total} {t_nodes}")
    if show_summary:
        parts.append("{summary}")
    elif show_links:
        parts.append("{links} {t_links}")
    if show_elapsed:
        parts.append("{elapsed}")
    return " · ".join(parts) if parts else ""


def settings_from_config(config: Config) -> UiSettings:
    """Read the current configuration and expose it as flat settings."""
    values: Dict[str, Any] = {}

    # An empty value is meaningful here (the user chose to hide the project
    # name), so the default must only apply when the key is missing.
    details = str(config.get("presence.details", "{project}"))
    state = str(config.get("presence.state", "") or "")

    # Reverse the templates to find out which parts are enabled.
    show_nodes = "{running}" in state
    show_links = "{links}" in state
    show_summary = "{summary}" in state
    show_elapsed = "{elapsed}" in state
    show_project = "{project}" in details

    values["presence.show_project"] = show_project
    values["presence.show_nodes"] = show_nodes
    values["presence.show_links"] = show_links
    values["presence.show_summary"] = show_summary
    values["presence.show_elapsed"] = show_elapsed
    values["presence.show_device_icon"] = bool(config.get("presence.small_image", ""))
    values["presence.show_party"] = bool(config.get("presence.party", False))
    values["presence.show_buttons"] = bool(config.get("presence.buttons", []))

    values["presence.preset"] = str(config.get("presence.preset", "student") or "student")
    values["presence.large_image"] = str(
        config.get("presence.large_image", "gns3") or "gns3"
    )
    values["presence.timestamp"] = str(
        config.get("presence.timestamp", "project") or "project"
    )
    values["language"] = str(config.get("language", "fr") or "fr")
    values["presence.details"] = details
    values["presence.state"] = state

    values["privacy.enabled"] = bool(config.get("privacy.enabled", False))
    values["privacy.replacement"] = str(
        config.get("privacy.replacement", "Un lab réseau") or ""
    )
    return UiSettings(values)


def changes_from_settings(settings: UiSettings, current: UiSettings) -> Dict[str, Any]:
    """Compute the configuration keys to write for the given settings."""
    changes: Dict[str, Any] = {}

    # details line
    details = str(settings.get("presence.details", "{project}") or "")
    if not settings.get("presence.show_project", True):
        details = details.replace("{project}", "")
    changes["presence.details"] = details.strip()

    # state line
    state = _template_for({}, settings.to_dict())
    if not settings.get("presence.show_nodes", True):
        state = state.replace("{running}/{total} {t_nodes}", "").strip()
    if not settings.get("presence.show_links", True) and not settings.get(
        "presence.show_summary", False
    ):
        state = state.replace("{links} {t_links}", "").strip()
    if not settings.get("presence.show_elapsed", False):
        state = state.replace("{elapsed}", "").strip()
    state = " · ".join(part.strip() for part in state.split("·") if part.strip())
    changes["presence.state"] = state

    # small image
    if settings.get("presence.show_device_icon", True):
        changes["presence.small_image"] = "{dominant_type}"
        changes["presence.small_text"] = "{dominant_label}"
    else:
        changes["presence.small_image"] = ""
        changes["presence.small_text"] = ""

    changes["presence.party"] = bool(settings.get("presence.show_party", True))
    changes["presence.preset"] = str(settings.get("presence.preset", "student"))
    changes["presence.large_image"] = str(settings.get("presence.large_image", "gns3"))
    changes["presence.timestamp"] = str(settings.get("presence.timestamp", "project"))
    changes["language"] = str(settings.get("language", "fr"))

    if settings.get("privacy.enabled"):
        changes["privacy.enabled"] = True
        changes["privacy.replacement"] = str(
            settings.get("privacy.replacement", "Un lab réseau")
        )
    else:
        changes["privacy.enabled"] = False

    # Buttons are kept as they are; the UI only toggles their visibility.
    if not settings.get("presence.show_buttons", True):
        changes["presence.buttons"] = []
    return changes


def settings_from_config_file(path: Path) -> UiSettings:
    """Read the settings from a configuration file on disk."""
    from .config import DEFAULTS, Config, deep_merge

    data = toml_edit.read_toml(path)
    return settings_from_config(Config(deep_merge(DEFAULTS, data), path, 0.0, data))


def reset_settings(config_path: Path) -> tuple[bool, str]:
    """Restore the default appearance settings in the configuration file."""
    from .config import DEFAULTS

    defaults = DEFAULTS.get("presence", {}) or {}
    changes: Dict[str, Any] = {
        "presence.preset": defaults.get("preset", "student"),
        "presence.details": defaults.get("details", "{project}"),
        "presence.state": defaults.get("state", "{running}/{total} {t_nodes} · {links} {t_links}"),
        "presence.large_image": defaults.get("large_image", "gns3"),
        "presence.small_image": defaults.get("small_image", "{dominant_type}"),
        "presence.small_text": defaults.get("small_text", "{dominant_label}"),
        "presence.timestamp": defaults.get("timestamp", "project"),
        "presence.party": defaults.get("party", True),
        "language": DEFAULTS.get("language", "fr"),
        "privacy.enabled": False,
    }
    success, error = toml_edit.update_file(config_path, changes)
    if not success:
        return False, error or "Ecriture impossible"
    return True, str(config_path)


def save_settings(config_path: Path, settings: UiSettings) -> tuple[bool, str]:
    """Write the settings into the configuration file."""
    current = settings_from_config_file(config_path)
    changes = changes_from_settings(settings, current)
    success, error = toml_edit.update_file(config_path, changes)
    if not success:
        return False, error or "Ecriture impossible"
    return True, str(config_path)
