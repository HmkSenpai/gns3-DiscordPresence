"""Tests for the GNS3 server discovery."""

from __future__ import annotations

from pathlib import Path

from gns3presence import discovery

INI_CONTENT = """[Server]
path = C:\\Program Files\\GNS3\\gns3server.EXE
host = localhost
port = 80
projects_path = C:\\Users\\Someone\\GNS3\\projects
auth = False
user = admin
protocol = http
"""


def test_parse_server_settings(tmp_path: Path):
    path = tmp_path / "gns3_server.ini"
    path.write_text(INI_CONTENT, encoding="utf-8")
    settings = discovery.parse_server_settings(path)
    assert settings is not None
    assert settings.host == "localhost"
    assert settings.port == 80
    assert settings.protocol == "http"
    assert settings.auth is False
    assert settings.username == "admin"
    assert settings.projects_path.endswith("projects")
    assert settings.base_url == "http://localhost:80"


def test_parse_server_settings_handles_missing_file(tmp_path: Path):
    assert discovery.parse_server_settings(tmp_path / "nope.ini") is None


def test_candidate_endpoints_priority(tmp_path: Path, monkeypatch):
    path = tmp_path / "gns3_server.ini"
    path.write_text(INI_CONTENT, encoding="utf-8")
    monkeypatch.setattr(discovery, "find_server_files", lambda: [path])
    monkeypatch.setattr(discovery, "gui_servers", lambda: [])
    monkeypatch.delenv("GNS3_URL", raising=False)

    candidates = discovery.candidate_endpoints("auto", "auto")
    urls = [c.url for c in candidates]
    assert "http://localhost:80" in urls
    assert "http://localhost:3080" in urls
    # The file based URL comes before the default ports.
    assert urls.index("http://localhost:80") < urls.index("http://localhost:3080")


def test_explicit_url_wins(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(discovery, "find_server_files", lambda: [])
    monkeypatch.setattr(discovery, "gui_servers", lambda: [])
    monkeypatch.delenv("GNS3_URL", raising=False)
    candidates = discovery.candidate_endpoints("http://192.168.1.10:3080", "auto")
    assert candidates[0].url == "http://192.168.1.10:3080"
    assert candidates[0].source == "configuration file"


def test_environment_variable_is_used(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(discovery, "find_server_files", lambda: [])
    monkeypatch.setattr(discovery, "gui_servers", lambda: [])
    monkeypatch.setenv("GNS3_URL", "http://gns3.lan:80")
    candidates = discovery.candidate_endpoints("auto", "auto")
    assert candidates[0].url == "http://gns3.lan:80"


def test_duplicate_urls_are_removed(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(discovery, "find_server_files", lambda: [])
    monkeypatch.setattr(discovery, "gui_servers", lambda: [])
    monkeypatch.delenv("GNS3_URL", raising=False)
    candidates = discovery.candidate_endpoints("http://localhost:3080", "auto")
    urls = [c.url for c in candidates]
    assert len(urls) == len(set(urls))
