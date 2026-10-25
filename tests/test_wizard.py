"""Tests for the first run assistant."""

from __future__ import annotations

from pathlib import Path

from gns3presence import wizard


def test_valid_app_id():
    assert wizard.is_valid_app_id("1562827344786235434")
    assert not wizard.is_valid_app_id("")
    assert not wizard.is_valid_app_id("abc")
    assert not wizard.is_valid_app_id("123")


def test_write_app_id_creates_the_file(tmp_path: Path):
    target = tmp_path / "config.toml"
    assert wizard.write_app_id_to_config(target, "1562827344786235434")
    content = target.read_text(encoding="utf-8")
    assert '[discord]' in content
    assert 'app_id = "1562827344786235434"' in content


def test_write_app_id_updates_an_existing_section(tmp_path: Path):
    target = tmp_path / "config.toml"
    target.write_text(
        '[discord]\napp_id = "OLD"\npoll_interval = 20\n', encoding="utf-8"
    )
    wizard.write_app_id_to_config(target, "NEW")
    content = target.read_text(encoding="utf-8")
    assert 'app_id = "NEW"' in content
    assert "OLD" not in content
    assert "poll_interval = 20" in content


def test_write_app_id_adds_the_section_when_missing(tmp_path: Path):
    target = tmp_path / "config.toml"
    target.write_text("[presence]\npreset = \"student\"\n", encoding="utf-8")
    wizard.write_app_id_to_config(target, "1562827344786235434")
    content = target.read_text(encoding="utf-8")
    assert "[discord]" in content
    assert 'app_id = "1562827344786235434"' in content
    assert "[presence]" in content


def test_shared_app_id_is_valid():
    assert wizard.is_valid_app_id(wizard.DEFAULT_APP_ID)


def test_asset_instructions(tmp_path: Path):
    (tmp_path / "gns3.png").write_bytes(b"")
    (tmp_path / "router.png").write_bytes(b"")
    lines = wizard.asset_instructions(tmp_path)
    assert any("gns3" in line for line in lines)
    assert any("router" in line for line in lines)
