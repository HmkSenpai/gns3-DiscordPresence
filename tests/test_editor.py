"""Tests for the settings model used by the web interface."""

from __future__ import annotations

from pathlib import Path

from gns3presence.config import DEFAULTS, Config, deep_merge
from gns3presence.editor import (
    UiSettings,
    changes_from_settings,
    reset_settings,
    save_settings,
    settings_from_config,
    settings_from_config_file,
)
from gns3presence.toml_edit import read_toml


def make_config(**overrides) -> Config:
    return Config(deep_merge(DEFAULTS, overrides), None, 0.0)


def test_defaults_are_detected():
    settings = settings_from_config(make_config())
    assert settings.get("presence.show_project") is True
    assert settings.get("presence.show_nodes") is True
    assert settings.get("presence.show_links") is True
    assert settings.get("presence.show_elapsed") is False
    assert settings.get("presence.preset") == "student"


def test_hidden_project_is_detected():
    config = make_config(presence={"details": "Un lab", "state": "{running}/{total}"})
    settings = settings_from_config(config)
    assert settings.get("presence.show_project") is False
    assert settings.get("presence.show_links") is False


def test_changes_disable_the_project_name():
    current = settings_from_config(make_config())
    settings = UiSettings(current.to_dict())
    settings.set("presence.show_project", False)
    changes = changes_from_settings(settings, current)
    assert "{project}" not in changes["presence.details"]


def test_changes_disable_the_timer():
    current = settings_from_config(make_config())
    settings = UiSettings(current.to_dict())
    settings.set("presence.show_elapsed", False)
    changes = changes_from_settings(settings, current)
    assert "{elapsed}" not in changes["presence.state"]


def test_changes_remove_the_small_image():
    current = settings_from_config(make_config())
    settings = UiSettings(current.to_dict())
    settings.set("presence.show_device_icon", False)
    changes = changes_from_settings(settings, current)
    assert changes["presence.small_image"] == ""
    assert changes["presence.small_text"] == ""


def test_changes_build_the_state_line():
    current = settings_from_config(make_config())
    settings = UiSettings(current.to_dict())
    settings.set("presence.show_nodes", True)
    settings.set("presence.show_links", True)
    settings.set("presence.show_summary", False)
    settings.set("presence.show_elapsed", True)
    changes = changes_from_settings(settings, current)
    assert "{running}/{total}" in changes["presence.state"]
    assert "{links}" in changes["presence.state"]
    assert "{elapsed}" in changes["presence.state"]
    assert "{summary}" not in changes["presence.state"]


def test_save_and_reload(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[discord]\napp_id = "1"\n', encoding="utf-8")
    current = settings_from_config_file(path)
    settings = UiSettings(current.to_dict())
    settings.set("presence.show_elapsed", True)
    settings.set("presence.show_project", False)
    ok, message = save_settings(path, settings)
    assert ok, message
    reloaded = settings_from_config_file(path)
    assert reloaded.get("presence.show_elapsed") is True
    assert reloaded.get("presence.show_project") is False


def test_reset_restores_the_defaults(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[presence]\npreset = "compact"\n', encoding="utf-8")
    ok, message = reset_settings(path)
    assert ok, message
    data = read_toml(path)
    assert data["presence"]["preset"] == "student"
