"""Tests for the non destructive TOML editing."""

from __future__ import annotations

from pathlib import Path

from gns3presence.toml_edit import read_toml, remove_value, set_value, update_file


def test_set_value_replaces_an_existing_key():
    content = '[discord]\napp_id = "OLD"\npoll_interval = 15\n'
    result = set_value(content, "discord.app_id", "NEW")
    assert 'app_id = "NEW"' in result
    assert "OLD" not in result
    assert "poll_interval = 15" in result


def test_set_value_keeps_the_comments():
    content = "# a comment\n[discord]\n# another comment\napp_id = \"OLD\"\n"
    result = set_value(content, "discord.app_id", "NEW")
    assert "# a comment" in result
    assert "# another comment" in result
    assert 'app_id = "NEW"' in result


def test_set_value_adds_a_key_to_an_existing_section():
    content = "[discord]\napp_id = \"1\"\n\n[presence]\npreset = \"student\"\n"
    result = set_value(content, "presence.large_image", "gns3")
    assert 'large_image = "gns3"' in result
    # The key must land in the [presence] section, not in [discord].
    assert result.index("[presence]") < result.index('large_image = "gns3"')


def test_set_value_creates_a_missing_section():
    content = "[discord]\napp_id = \"1\"\n"
    result = set_value(content, "presence.preset", "teacher")
    assert "[presence]" in result
    assert 'preset = "teacher"' in result


def test_set_value_preserves_unknown_sections():
    content = "[discord]\napp_id = \"1\"\n\n[custom]\nfoo = 42\n"
    result = set_value(content, "discord.app_id", "2")
    assert "[custom]" in result
    assert "foo = 42" in result


def test_values_are_formatted_as_toml():
    content = "[discord]\n"
    assert 'x = "text"' in set_value(content, "discord.x", "text")
    assert "x = true" in set_value(content, "discord.x", True)
    assert "x = false" in set_value(content, "discord.x", False)
    assert "x = 42" in set_value(content, "discord.x", 42)
    assert 'x = ["a"]' in set_value(content, "discord.x", ["a"])
    assert 'x = "say \\"hi\\""' in set_value(content, "discord.x", 'say "hi"')


def test_update_file_round_trip(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[discord]\napp_id = "1"\n', encoding="utf-8")
    ok, error = update_file(path, {"discord.app_id": "42", "presence.preset": "teacher"})
    assert ok, error
    data = read_toml(path)
    assert data["discord"]["app_id"] == "42"
    assert data["presence"]["preset"] == "teacher"


def test_update_file_creates_the_file(tmp_path: Path):
    path = tmp_path / "sub" / "config.toml"
    ok, error = update_file(path, {"discord.app_id": "42"})
    assert ok, error
    assert path.exists()


def test_remove_value():
    content = '[discord]\napp_id = "1"\npoll_interval = 15\n'
    result = remove_value(content, "discord.app_id")
    assert "app_id" not in result
    assert "poll_interval = 15" in result
