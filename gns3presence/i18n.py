"""Tiny translation helper (fr / en)."""

from __future__ import annotations

from typing import Any, Dict

TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "fr": {
        "nodes": "nœuds",
        "node": "nœud",
        "links": "liens",
        "link": "lien",
        "router": "routeur",
        "routers": "routeurs",
        "switch": "switch",
        "switches": "switches",
        "pc": "PC",
        "pcs": "PC",
        "firewall": "firewall",
        "firewalls": "firewalls",
        "vm": "VM",
        "vms": "VM",
        "unknown": "équipement",
        "unknowns": "équipements",
        "idle_details": "Au repos",
        "idle_state": "Prêt pour un nouveau lab",
        "running": "en marche",
        "closed_details": "GNS3",
        "closed_state": "Session terminée",
    },
    "en": {
        "nodes": "nodes",
        "node": "node",
        "links": "links",
        "link": "link",
        "router": "router",
        "routers": "routers",
        "switch": "switch",
        "switches": "switches",
        "pc": "PC",
        "pcs": "PCs",
        "firewall": "firewall",
        "firewalls": "firewalls",
        "vm": "VM",
        "vms": "VMs",
        "unknown": "device",
        "unknowns": "devices",
        "idle_details": "Idle",
        "idle_state": "Ready for a new lab",
        "running": "running",
        "closed_details": "GNS3",
        "closed_state": "Session over",
    },
}

PLURALS = {
    "router": ("router", "routers"),
    "switch": ("switch", "switches"),
    "pc": ("pc", "pcs"),
    "firewall": ("firewall", "firewalls"),
    "vm": ("vm", "vms"),
    "unknown": ("unknown", "unknowns"),
}


class Translator:
    def __init__(self, language: str = "fr"):
        self.language = language if language in TRANSLATIONS else "fr"

    def t(self, key: str, default: str = "") -> str:
        return TRANSLATIONS[self.language].get(key, default or key)

    def count(self, category: str, amount: int) -> str:
        singular, plural = PLURALS.get(category, (category, category + "s"))
        word = singular if amount <= 1 else plural
        return f"{amount} {self.t(word, word)}"
