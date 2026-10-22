"""Generate the Discord art assets shipped with the repository.

Usage::

    pip install pillow
    python tools/make_assets.py

The PNG files are then uploaded manually in the Discord developer portal
(https://discord.com/developers/applications -> Rich Presence -> Art Assets).
The asset key used by the companion is the file name without its extension.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

SIZES = {"large": 512, "small": 128}

PALETTE = {
    "gns3": ((49, 168, 84), (255, 255, 255)),
    "router": ((38, 108, 214), (255, 255, 255)),
    "switch": ((0, 150, 136), (255, 255, 255)),
    "pc": ((55, 61, 79), (255, 255, 255)),
    "firewall": ((200, 62, 46), (255, 255, 255)),
    "vm": ((123, 76, 173), (255, 255, 255)),
    "idle": ((96, 104, 112), (255, 255, 255)),
}


def _canvas(size: int, color) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = int(size * 0.06)
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=int(size * 0.18),
        fill=color,
    )
    return image


def _glyph(draw: ImageDraw.ImageDraw, size: int, kind: str, color) -> None:
    """Draw a simple white glyph in the middle of the square."""
    c = size // 2
    u = size / 100.0  # unit
    w = max(2, int(size * 0.055))

    if kind == "gns3":  # topology: 3 nodes + links
        r = int(6 * u)
        points = [(c - 18 * u, c - 14 * u), (c + 18 * u, c - 14 * u), (c, c + 20 * u)]
        for a, b in ((0, 2), (1, 2), (0, 1)):
            draw.line((points[a], points[b]), fill=color, width=w)
        for point in points:
            draw.ellipse(
                (point[0] - r, point[1] - r, point[0] + r, point[1] + r),
                fill=color,
            )
    elif kind == "router":  # router: rounded box with two arrows
        box = (c - 24 * u, c - 12 * u, c + 24 * u, c + 12 * u)
        draw.rounded_rectangle(box, radius=int(5 * u), outline=color, width=w)
        draw.line((c - 12 * u, c - 5 * u, c + 12 * u, c - 5 * u), fill=color, width=w)
        draw.line((c - 12 * u, c + 4 * u, c + 12 * u, c + 4 * u), fill=color, width=w)
    elif kind == "switch":  # switch: two opposite arrows
        draw.line((c - 26 * u, c - 12 * u, c + 20 * u, c - 12 * u), fill=color, width=w)
        draw.line((c + 20 * u, c - 12 * u, c + 10 * u, c - 20 * u), fill=color, width=w)
        draw.line((c + 20 * u, c - 12 * u, c + 10 * u, c - 4 * u), fill=color, width=w)
        draw.line((c + 26 * u, c + 12 * u, c - 20 * u, c + 12 * u), fill=color, width=w)
        draw.line((c - 20 * u, c + 12 * u, c - 10 * u, c + 4 * u), fill=color, width=w)
        draw.line((c - 20 * u, c + 12 * u, c - 10 * u, c + 20 * u), fill=color, width=w)
    elif kind == "pc":  # monitor
        draw.rounded_rectangle(
            (c - 22 * u, c - 20 * u, c + 22 * u, c + 10 * u),
            radius=int(4 * u),
            outline=color,
            width=w,
        )
        draw.line((c, c + 10 * u, c, c + 20 * u), fill=color, width=w)
        draw.line((c - 12 * u, c + 20 * u, c + 12 * u, c + 20 * u), fill=color, width=w)
    elif kind == "firewall":  # brick wall
        rows = 3
        height = 40 * u
        top = c - height / 2
        brick_h = height / rows
        for row in range(rows):
            y = top + row * brick_h
            offset = (brick_h / 2) if row % 2 else 0
            x = c - 26 * u + offset
            while x < c + 26 * u:
                draw.rectangle((x, y, x + 14 * u, y + brick_h), outline=color, width=w)
                x += 16 * u
    elif kind == "vm":  # server stack
        for index in range(3):
            y = c - 20 * u + index * 14 * u
            draw.rounded_rectangle(
                (c - 24 * u, y, c + 24 * u, y + 10 * u),
                radius=int(2 * u),
                outline=color,
                width=w,
            )
            draw.ellipse(
                (c + 15 * u, y + 3 * u, c + 19 * u, y + 7 * u), fill=color
            )
    elif kind == "idle":  # moon
        draw.ellipse(
            (c - 20 * u, c - 20 * u, c + 20 * u, c + 20 * u), outline=color, width=w
        )
        draw.ellipse(
            (c - 6 * u, c - 24 * u, c + 26 * u, c + 12 * u), fill=(0, 0, 0, 0)
        )


def make_icon(kind: str, size: int) -> Image.Image:
    background, foreground = PALETTE[kind]
    image = _canvas(size, background)
    draw = ImageDraw.Draw(image)
    _glyph(draw, size, kind, foreground)
    return image


def main() -> None:
    for folder, size in SIZES.items():
        target = ASSETS / folder
        target.mkdir(parents=True, exist_ok=True)
        for kind in PALETTE:
            image = make_icon(kind, size)
            path = target / f"{kind}.png"
            image.save(path, "PNG", optimize=True)
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
