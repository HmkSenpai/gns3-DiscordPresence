"""Tests for the configuration loader."""

from __future__ import annotations

from pathlib import Path

from gns3presence.config import DEFAULTS, Config, deep_merge, load_config


def test_deep_merge_keeps_defaults():
    merged = deep_merge(DEFAULTS, {"discord": {"app_id": "123"}})
    assert merged["discord"]["app_id"] == "123"
    assert merged["discord"]["poll_interval"] == DEFAULTS["discord"]["poll_interval"]
    assert merged["presence"]["preset"] == "student"


def test_load_config_reads_toml(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[discord]\napp_id = "42"\n\n[presence]\npreset = "teacher"\n', encoding="utf-8"
    )
    config = load_config(str(path))
    assert config.app_id == "42"
    assert config.get("presence.preset") == "teacher"
    assert config.path == path


def test_load_config_falls_back_to_defaults(tmp_path: Path):
    config = load_config(str(tmp_path / "does-not-exist.toml"))
    assert isinstance(config, Config)
    assert config.get("presence.preset") == "student"


def test_get_returns_default_for_unknown_key(config: Config):
    assert config.get("nope.nothing", "fallback") == "fallback"


def test_invalid_toml_is_ignored(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text("this is not toml = = =", encoding="utf-8")
    config = load_config(str(path))
    assert config.get("presence.preset") == "student"
