"""Discord side: publish the activity through the local Discord client.

The heavy lifting is done by `pypresence` (https://github.com/qwertyquerty/pypresence)
which speaks the Discord IPC protocol over the local named pipe. If pypresence
is not installed the companion degrades gracefully: it keeps computing the
payload and simply tells the user how to install it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict

from .render import Activity

log = logging.getLogger(__name__)

try:  # pragma: no cover - depends on the environment
    from pypresence import Presence  # type: ignore

    PYPRESENCE_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    Presence = None  # type: ignore
    PYPRESENCE_AVAILABLE = False
    log.debug("pypresence not available: %s", exc)


def pypresence_available() -> bool:
    return PYPRESENCE_AVAILABLE


class Publisher:
    """Sends activities to Discord, with rate limiting and reconnection."""

    def __init__(
        self,
        app_id: str,
        min_interval: float = 15.0,
        dry_run: bool = False,
    ):
        self.app_id = app_id
        self.min_interval = max(1.0, float(min_interval))
        self.dry_run = dry_run
        self._rpc = None
        self._connected = False
        self._last_payload_hash = ""
        self._last_sent_at = 0.0
        self._next_retry_at = 0.0

    # -- connection ------------------------------------------------------
    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self, force: bool = False) -> bool:
        """Connect to the local Discord client."""
        if self.dry_run:
            self._connected = True
            return True
        if self._connected and not force:
            return True
        if not self.app_id:
            log.error("No Discord application ID configured (discord.app_id)")
            return False
        if not PYPRESENCE_AVAILABLE:
            log.error(
                "pypresence is not installed. Run: pip install pypresence"
            )
            return False
        now = time.time()
        if now < self._next_retry_at:
            return False
        try:
            self._rpc = Presence(self.app_id)
            self._rpc.connect()
            self._connected = True
            log.info("Connected to Discord (application %s)", self.app_id)
            return True
        except Exception as exc:
            self._rpc = None
            self._connected = False
            self._next_retry_at = now + 10
            log.warning("Cannot connect to Discord: %s", exc)
            return False

    def close(self) -> None:
        if self._rpc is not None:
            try:
                self._rpc.close()
            except Exception:
                pass
        self._rpc = None
        self._connected = False

    # -- publishing ------------------------------------------------------
    @staticmethod
    def _hash(payload: Dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def should_publish(self, payload: Dict[str, Any]) -> bool:
        """Rate limit + change detection."""
        payload_hash = self._hash(payload)
        now = time.time()
        if payload_hash == self._last_payload_hash:
            return False
        if now - self._last_sent_at < self.min_interval:
            return False
        return True

    def publish(self, activity: Activity) -> bool:
        """Publish an activity. Returns True when something was sent."""
        payload = activity.as_dict()
        if not self.should_publish(payload):
            return False
        if not self.connect():
            return False
        if self.dry_run:
            self._last_payload_hash = self._hash(payload)
            self._last_sent_at = time.time()
            return True
        try:
            self._rpc.set_activity(**payload)  # type: ignore[union-attr]
            self._last_payload_hash = self._hash(payload)
            self._last_sent_at = time.time()
            log.info("Presence updated: %s", payload)
            return True
        except Exception as exc:
            log.warning("Failed to publish presence: %s", exc)
            self._connected = False
            self._rpc = None
            self._next_retry_at = time.time() + 10
            return False

    def clear(self) -> None:
        """Remove the presence from Discord."""
        if self.dry_run or not self._connected or self._rpc is None:
            return
        try:
            self._rpc.clear()
            log.info("Presence cleared")
        except Exception as exc:
            log.debug("Cannot clear presence: %s", exc)
