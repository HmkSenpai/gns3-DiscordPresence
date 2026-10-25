"""Render a Discord activity payload from a :class:`~gns3presence.state.LabState`.

The renderer is intentionally data-driven: everything the user can customise
lives in ``config.toml`` (templates, presets, per-project rules, privacy).
"""

from __future__ import annotations

import fnmatch
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import Config
from .i18n import Translator
from .state import LabState

log = logging.getLogger(__name__)

PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\}")

#: Presets are simple partial overrides applied before the user templates.
PRESETS: Dict[str, Dict[str, Any]] = {
    "minimal": {
        "details": "{project}",
        "state": "{running}/{total}",
        "small_image": "",
        "small_text": "",
        "party": False,
    },
    "student": {
        "details": "{project}",
        "state": "{running}/{total} {t_nodes} · {links} {t_links}",
        "small_image": "{dominant_type}",
        "small_text": "{dominant_label}",
        "party": True,
    },
    "teacher": {
        "details": "{project}",
        "state": "{running}/{total} {t_nodes} · {summary}",
        "small_image": "{dominant_type}",
        "small_text": "{dominant_label}",
        "party": True,
    },
    "streamer": {
        "details": "{project}",
        "state": "{running}/{total} {t_nodes} · {elapsed}",
        "small_image": "{dominant_type}",
        "small_text": "{dominant_label}",
        "party": True,
    },
    "compact": {
        "details": "{project}",
        "state": "{running}/{total}",
        "small_image": "",
        "small_text": "",
        "party": False,
    },
}


@dataclass
class Activity:
    """A Discord activity payload (only the fields Discord understands)."""

    details: str = ""
    state: str = ""
    large_image: str = ""
    large_text: str = ""
    small_image: str = ""
    small_text: str = ""
    start: Optional[float] = None
    party_size: Optional[List[int]] = None
    buttons: List[Dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "details": self.details,
            "state": self.state,
        }
        if self.large_image:
            payload["large_image"] = self.large_image
            payload["large_text"] = self.large_text
        if self.small_image:
            payload["small_image"] = self.small_image
            payload["small_text"] = self.small_text
        if self.start is not None:
            payload["start"] = int(self.start)
        if self.party_size:
            payload["party_size"] = self.party_size
        if self.buttons:
            payload["buttons"] = self.buttons
        return payload


def _classify(node_type: str, categories: Dict[str, List[str]]) -> str:
    """Map a GNS3 node type to a friendly category."""
    needle = (node_type or "").lower()
    for category, types in categories.items():
        for known in types:
            if needle == known.lower() or needle.startswith(known.lower()):
                return category
    return "unknown"


def _match_rule(rule: Dict[str, Any], project_name: str) -> bool:
    """Does a rule apply to this project?"""
    pattern = str(rule.get("match", "")).strip()
    if not pattern:
        return False
    if pattern.startswith("re:"):
        try:
            return bool(re.search(pattern[3:], project_name, re.IGNORECASE))
        except re.error as exc:
            log.warning("Invalid regex in rule %r: %s", pattern, exc)
            return False
    if "/" in pattern:
        try:
            return bool(re.fullmatch(pattern, project_name, re.IGNORECASE))
        except re.error:
            pass
    return fnmatch.fnmatch(project_name.lower(), pattern.lower())


def _privacy_triggered(config: Config, project_name: str) -> bool:
    privacy = config.get("privacy", {}) or {}
    if privacy.get("enabled"):
        return True
    patterns = privacy.get("patterns", []) or []
    lowered = project_name.lower()
    for pattern in patterns:
        try:
            if re.search(str(pattern), lowered, re.IGNORECASE):
                return True
        except re.error:
            if str(pattern).lower() in lowered:
                return True
    return False


def build_context(state: LabState, config: Config, translator: Translator) -> Dict[str, Any]:
    """All values usable in the templates."""
    categories = config.get("categories", {}) or {}
    images = config.get("images", {}) or {}

    per_category: Dict[str, int] = {}
    running_per_category: Dict[str, int] = {}
    for node in state.nodes:
        category = _classify(node.node_type, categories)
        per_category[category] = per_category.get(category, 0) + 1
        if node.is_running:
            running_per_category[category] = running_per_category.get(category, 0) + 1

    dominant = "unknown"
    best = 0
    for category, count in sorted(per_category.items(), key=lambda kv: kv[1], reverse=True):
        if count > best:
            dominant, best = category, count

    summary_parts = [
        translator.count(category, count)
        for category, count in sorted(per_category.items(), key=lambda kv: kv[1], reverse=True)
        if count
    ]

    elapsed = ""
    if state.project_started_at:
        import time as _time

        minutes = int(max(0, _time.time() - state.project_started_at) // 60)
        if minutes < 60:
            elapsed = f"{minutes} min"
        else:
            elapsed = f"{minutes // 60} h {minutes % 60:02d} min"

    context: Dict[str, Any] = {
        "project": state.project_name or "",
        "project_id": state.project_id or "",
        "running": state.running,
        "total": state.total,
        "links": state.link_count,
        "server_version": state.server_version,
        "version": state.server_version,
        "server_url": state.server_url,
        "source": state.source,
        "dominant_type": images.get(dominant, images.get("unknown", "gns3")),
        "dominant_category": dominant,
        "dominant_label": translator.t(dominant, dominant),
        "summary": " · ".join(summary_parts),
        "elapsed": elapsed,
        "t_nodes": translator.t("nodes"),
        "t_links": translator.t("links"),
        "t_running": translator.t("running"),
        "state": state.state_name,
    }
    for category, count in per_category.items():
        context[f"count.{category}"] = count
        context[f"running.{category}"] = running_per_category.get(category, 0)
    return context


def render_template(template: str, context: Dict[str, Any]) -> str:
    """Replace ``{placeholder}`` markers, leaving unknown ones untouched."""

    def _replace(match: "re.Match[str]") -> str:
        key = match.group(1)
        if key in context:
            return str(context[key])
        head, _, tail = key.partition(".")
        if head in context and isinstance(context[head], dict):
            value = context[head].get(tail)
            if value is not None:
                return str(value)
        return match.group(0)

    return PLACEHOLDER_RE.sub(_replace, template or "").strip()


class Renderer:
    """Turns a :class:`LabState` into a Discord :class:`Activity`."""

    def __init__(self, config: Config):
        self.config = config
        self.translator = Translator(str(config.get("language", "fr") or "fr"))

    def _template_block(self, state_name: str) -> Dict[str, Any]:
        """Build the template set for a given state.

        Priority: user configuration > preset > built-in default.
        """
        presence = self.config.get("presence", {}) or {}
        block: Dict[str, Any] = {
            key: value
            for key, value in presence.items()
            if key not in ("idle", "preset", "buttons")
        }

        preset_name = str(presence.get("preset", "student") or "student").lower()
        for key, value in PRESETS.get(preset_name, {}).items():
            if not self._is_customised(key, value):
                block[key] = value

        if state_name in ("idle", "closed"):
            # Nothing to show but the "at rest" presence: the [presence.idle]
            # block wins over the main templates (it may be user defined).
            idle_block = dict(presence.get("idle", {}) or {})
            merged = dict(block)
            merged.update(idle_block)
            block = merged
        return block

    def _is_customised(self, key: str, preset_value: Any) -> bool:
        """Has the user set this key (explicitly, even to an empty value)?"""
        if self.config.user_set(f"presence.{key}"):
            return True
        # The value may also have been changed through the web interface: in
        # that case it differs from the built-in default.
        from .config import DEFAULTS

        default_value = (DEFAULTS.get("presence", {}) or {}).get(key)
        current = self.config.get(f"presence.{key}")
        if current is None:
            return False
        if isinstance(default_value, str) and isinstance(current, str):
            return current != default_value
        return current != default_value


    def render(self, state: LabState) -> Activity:
        context = build_context(state, self.config, self.translator)
        state_name = state.state_name

        block = self._template_block(state_name)
        details = render_template(str(block.get("details", "")), context)
        state_text = render_template(str(block.get("state", "")), context)
        large_image = render_template(str(block.get("large_image", "")), context)
        large_text = render_template(str(block.get("large_text", "")), context)
        small_image = render_template(str(block.get("small_image", "")), context)
        small_text = render_template(str(block.get("small_text", "")), context)
        party = bool(block.get("party", False))
        timestamp = str(block.get("timestamp", "project") or "none").lower()
        buttons = self._buttons(self.config.get("presence.buttons", []) or [])

        # Per-project rules (first match wins).
        forced_privacy = False
        for rule in self.config.rules:
            if not _match_rule(rule, state.project_name or ""):
                continue
            details = render_template(str(rule.get("details", details)), context)
            state_text = render_template(str(rule.get("state", state_text)), context)
            large_image = render_template(str(rule.get("large_image", large_image)), context)
            large_text = render_template(str(rule.get("large_text", large_text)), context)
            small_image = render_template(str(rule.get("small_image", small_image)), context)
            small_text = render_template(str(rule.get("small_text", small_text)), context)
            if "party" in rule:
                party = bool(rule["party"])
            if "timestamp" in rule:
                timestamp = str(rule["timestamp"]).lower()
            if "buttons" in rule:
                buttons = self._buttons(rule["buttons"])
            if "privacy" in rule:
                forced_privacy = bool(rule["privacy"])
            log.debug("Rule matched for project %s", state.project_name)
            break

        # Privacy.
        privacy_hit = forced_privacy or _privacy_triggered(
            self.config, state.project_name or ""
        )
        if state_name != "closed" and privacy_hit:
            privacy = self.config.get("privacy", {}) or {}
            replacement = str(privacy.get("replacement", "Un lab réseau"))
            details = replacement
            state_text = render_template(
                str(privacy.get("state", "{running}/{total} {t_nodes}")), context
            )
            small_image = ""
            small_text = ""
            if privacy.get("hide_buttons", True):
                buttons = []
            log.info("Privacy mode active for project %s", state.project_name)

        activity = Activity(
            details=details[:128],
            state=state_text[:128],
            large_image=large_image,
            large_text=large_text[:128],
            small_image=small_image,
            small_text=small_text[:128],
            buttons=buttons[:2],
        )

        # Discord rejects an empty "details" (and an empty activity): when the
        # user hides everything, fall back on a neutral text.
        if not activity.details.strip():
            activity.details = "GNS3"
        if not activity.state.strip():
            activity.state = "En cours"

        if timestamp == "project" and state.project_started_at:
            activity.start = state.project_started_at
        elif timestamp == "session":
            activity.start = state.project_started_at

        if party and state.total:
            activity.party_size = [state.running, state.total]
        return activity

    @staticmethod
    def _buttons(raw: Any) -> List[Dict[str, str]]:
        buttons: List[Dict[str, str]] = []
        if not isinstance(raw, list):
            return buttons
        for item in raw:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()[:32]
            url = str(item.get("url", "")).strip()
            if not label or not url.startswith(("http://", "https://")):
                continue
            buttons.append({"label": label, "url": url})
        return buttons
