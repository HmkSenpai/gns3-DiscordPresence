"""Tests that keep the shipped configuration files valid.

A root level key placed after a section silently belongs to that section in
TOML, which broke the ``language`` setting: it must stay before the first
section.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import tomllib  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    pass

from gns3presence.toml_edit import _toml_module  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = [
    ROOT / "config.example.toml",
    ROOT / "exemples" / "config.toml",
]

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
ROOT_KEY_RE = re.compile(r"^([A-Za-z0-9_]+)\s*=")


@pytest.mark.parametrize("path", TEMPLATES)
def test_template_is_valid_toml(path: Path):
    if not path.exists():
        pytest.skip(f"{path} not present")
    with path.open("rb") as handle:
        _toml_module().load(handle)


@pytest.mark.parametrize("path", TEMPLATES)
def test_root_keys_are_before_the_first_section(path: Path):
    """A key written before any section belongs to the root table.

    A *root* key written after a section is ambiguous: TOML attaches it to
    that section. The test only looks at the keys that are meant to be at the
    root level, i.e. the ones appearing before the first section.
    """
    if not path.exists():
        pytest.skip(f"{path} not present")
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        if SECTION_RE.match(line):
            break
        match = ROOT_KEY_RE.match(line)
        if match:
            # A root key: make sure it is a known one.
            assert match.group(1) in ("language",), (
                f"{path.name}:{number}: unexpected root key '{match.group(1)}'"
            )


@pytest.mark.parametrize("path", TEMPLATES)
def test_language_is_a_root_key(path: Path):
    if not path.exists():
        pytest.skip(f"{path} not present")
    with path.open("rb") as handle:
        data = _toml_module().load(handle)
    assert "language" in data, "language must be a root level key"
    assert "language" not in data.get("categories", {})
    assert "language" not in data.get("privacy", {})


@pytest.mark.parametrize("path", TEMPLATES)
def test_no_duplicated_key_in_the_same_section(path: Path):
    if not path.exists():
        pytest.skip(f"{path} not present")
    section = ""
    seen = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        match = SECTION_RE.match(line)
        if match:
            section = match.group(1).strip()
            seen = set()
            continue
        match = ROOT_KEY_RE.match(line)
        if match:
            key = f"{section}.{match.group(1)}"
            assert key not in seen, f"{path.name}:{number}: duplicated key '{key}'"
            seen.add(key)

