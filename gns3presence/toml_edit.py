"""Non destructive TOML editing.

The web interface must be able to change a few settings without destroying
the comments and the keys the user wrote by hand. ``tomllib`` only reads, so
this module implements a small writer that updates a file in place:

* known keys are replaced (keeping the surrounding comments),
* unknown keys and sections are preserved,
* new keys are appended to their section.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
KEY_RE = re.compile(r"^(\s*)([A-Za-z0-9_.\-]+)\s*=\s*(.*)$")


def _split_key(path: str) -> List[str]:
    return [part.strip() for part in path.split(".") if part.strip()]


def _format_value(value: object) -> str:
    """Render a Python value as TOML."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    if isinstance(value, dict):
        inner = ", ".join(f"{k} = {_format_value(v)}" for k, v in value.items())
        return "{" + inner + "}"
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _dump_table(data: Dict[str, object], prefix: str = "") -> List[str]:
    """Render a table as TOML lines (scalars first, then sub tables)."""
    lines: List[str] = []
    scalars = {k: v for k, v in data.items() if not isinstance(v, dict)}
    tables = {k: v for k, v in data.items() if isinstance(v, dict)}
    if scalars and prefix:
        lines.append(f"[{prefix}]")
    for key, value in scalars.items():
        lines.append(f"{key} = {_format_value(value)}")
    if scalars and prefix:
        lines.append("")
    for key, value in tables.items():
        name = f"{prefix}.{key}" if prefix else key
        lines.extend(_dump_table(value, name))
    return lines


def read_toml(path: Path) -> Dict[str, object]:
    """Read a TOML file (returns an empty dict when unreadable)."""
    try:
        import tomllib

        with path.open("rb") as handle:
            return tomllib.load(handle)
    except Exception:
        return {}


def set_value(content: str, path: str, value: object) -> str:
    """Return the file content with ``path`` set to ``value``.

    ``path`` uses dotted notation: ``"presence.state"``.
    """
    parts = _split_key(path)
    if not parts:
        return content
    lines = content.splitlines()
    section = ""
    rendered = _format_value(value)

    # 1. The key already exists -> replace it in place.
    target_section = ".".join(parts[:-1])
    target_key = parts[-1]
    for index, line in enumerate(lines):
        match = SECTION_RE.match(line)
        if match:
            section = match.group(1).strip()
            continue
        match = KEY_RE.match(line)
        if not match:
            continue
        key = match.group(2)
        current_section = section
        if current_section:
            key_path = f"{current_section}.{key}"
        else:
            key_path = key
        if key_path == path:
            indent = match.group(1)
            lines[index] = f"{indent}{target_key} = {rendered}"
            return "\n".join(lines) + ("\n" if content.endswith("\n") else "")
        # A root level key may physically sit after a section: in that case it
        # still belongs to the root table.
        if not target_section and current_section and key == target_key:
            indent = match.group(1)
            lines[index] = f"{indent}{target_key} = {rendered}"
            return "\n".join(lines) + ("\n" if content.endswith("\n") else "")

    # 2. The key does not exist -> add it to its section (or create it).
    if target_section:
        section_start = None
        section_end = len(lines)
        for index, line in enumerate(lines):
            match = SECTION_RE.match(line)
            if not match:
                continue
            name = match.group(1).strip()
            if name == target_section:
                section_start = index
            elif section_start is not None and name.startswith(target_section + "."):
                section_end = index
                break
            elif section_start is not None:
                section_end = index
                break
        if section_start is None:
            # The section does not exist: create it at the end of the file.
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(f"[{target_section}]")
            lines.append(f"{parts[-1]} = {rendered}")
            lines.append("")
        else:
            insert_at = section_end
            lines.insert(insert_at, f"{parts[-1]} = {rendered}")
    else:
        # A root level key must be written before the first section, otherwise
        # TOML would attach it to that section.
        first_section = None
        for index, line in enumerate(lines):
            if SECTION_RE.match(line):
                first_section = index
                break
        new_line = f"{target_key} = {rendered}"
        if first_section is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(new_line)
        else:
            insert_at = first_section
            while insert_at > 0 and not lines[insert_at - 1].strip():
                insert_at -= 1
            lines.insert(insert_at, new_line)
    return "\n".join(lines) + "\n"


def update_file(path: Path, changes: Dict[str, object]) -> Tuple[bool, Optional[str]]:
    """Apply several changes to a TOML file.

    Returns ``(success, error_message)``.
    """
    try:
        content = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError as exc:
        return False, str(exc)
    for key, value in changes.items():
        content = set_value(content, key, value)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, None


def remove_value(content: str, path: str) -> str:
    """Return the content without the given key."""
    parts = _split_key(path)
    if not parts:
        return content
    lines = content.splitlines()
    section = ""
    target_section = ".".join(parts[:-1])
    kept: List[str] = []
    for line in lines:
        match = SECTION_RE.match(line)
        if match:
            section = match.group(1).strip()
            kept.append(line)
            continue
        match = KEY_RE.match(line)
        if match:
            key_path = f"{section}.{match.group(2)}" if section else match.group(2)
            if key_path == path or (
                section == target_section and match.group(2) == parts[-1]
            ):
                continue
        kept.append(line)
    return "\n".join(kept) + "\n"
