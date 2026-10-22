"""Optional system tray icon (Windows / Linux / macOS).

The tray is a convenience, never a requirement: if pystray or Pillow are not
available the companion still runs headless.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

try:  # pragma: no cover - depends on the environment
    import pystray  # type: ignore
    from PIL import Image, ImageDraw  # type: ignore

    TRAY_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    pystray = None  # type: ignore
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    TRAY_AVAILABLE = False
    log.debug("Tray unavailable: %s", exc)


def tray_available() -> bool:
    return TRAY_AVAILABLE


def _icon_image() -> Any:  # pragma: no cover - visual only
    """Draw a small GNS3-ish icon (green rounded square with a link glyph)."""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((4, 4, size - 4, size - 4), radius=12, fill=(49, 168, 84, 255))
    draw.ellipse((14, 26, 26, 38), outline=(255, 255, 255, 255), width=4)
    draw.ellipse((38, 26, 50, 38), outline=(255, 255, 255, 255), width=4)
    draw.line((26, 32, 38, 32), fill=(255, 255, 255, 255), width=4)
    return image


class Tray:
    """Thin wrapper around pystray running in its own thread."""

    def __init__(
        self,
        on_quit: Callable[[], None],
        on_pause: Callable[[], bool],
        on_reload: Callable[[], None],
        status_provider: Callable[[], str],
    ):
        self.on_quit = on_quit
        self.on_pause = on_pause
        self.on_reload = on_reload
        self.status_provider = status_provider
        self._icon: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        if not TRAY_AVAILABLE:
            return False
        try:  # pragma: no cover - GUI code
            self._icon = pystray.Icon(
                "gns3-presence",
                _icon_image(),
                "GNS3 Presence",
                menu=pystray.Menu(
                    pystray.MenuItem(
                        lambda _: self.status_provider(), None, enabled=False
                    ),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem(
                        "Pause / Resume", lambda *_: self.on_pause(), default=True
                    ),
                    pystray.MenuItem("Reload configuration", lambda *_: self.on_reload()),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Quit", lambda *_: self.on_quit()),
                ),
            )
            self._thread = threading.Thread(target=self._icon.run, daemon=True)
            self._thread.start()
            return True
        except Exception as exc:
            log.warning("Cannot start tray icon: %s", exc)
            return False

    def stop(self) -> None:  # pragma: no cover - GUI code
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
