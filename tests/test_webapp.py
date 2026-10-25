"""Tests for the local web interface."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from gns3presence.config import DEFAULTS, Config, deep_merge
from gns3presence.webapp import start_web_app


def _config(path: Path) -> Config:
    data = {}
    return Config(deep_merge(DEFAULTS, data), path, 0.0, data)


def test_two_instances_do_not_share_the_same_port(tmp_path: Path):
    """A second instance must get its own port, not answer with its own token.

    On Windows, ``SO_REUSEADDR`` would let both listen on the same port and
    the requests would be answered by the first one, with a wrong token.
    """
    first_path = tmp_path / "a.toml"
    second_path = tmp_path / "b.toml"
    first_path.write_text('[discord]\napp_id = "1"\n', encoding="utf-8")
    second_path.write_text('[discord]\napp_id = "2"\n', encoding="utf-8")

    server1, url1 = start_web_app(_config(first_path), first_path, port=8971, open_browser=False)
    server2, url2 = start_web_app(_config(second_path), second_path, port=8971, open_browser=False)
    try:
        assert url1 != url2, "the two instances must not share the same port"
        for url in (url1, url2):
            with urllib.request.urlopen(url) as response:
                assert response.status == 200
                body = response.read()
                assert b"GNS3 Presence" in body
    finally:
        for server in (server1, server2):
            server.shutdown()
            server.server_close()


def test_the_api_refuses_a_wrong_token(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[discord]\napp_id = "1"\n', encoding="utf-8")
    server, url = start_web_app(_config(path), path, port=8973, open_browser=False)
    port = server.server_address[1]
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/state?token=wrong-token"
        )
        try:
            urllib.request.urlopen(request)
            raise AssertionError("a wrong token must be rejected")
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
    finally:
        server.shutdown()
        server.server_close()


def test_saving_updates_the_file(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[discord]\napp_id = "1"\n', encoding="utf-8")
    server, url = start_web_app(_config(path), path, port=8975, open_browser=False)
    port = server.server_address[1]
    token = url.split("token=")[-1]
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/save?token={token}",
            data=json.dumps({"settings": {"presence.show_project": False}}).encode(),
            headers={"Content-Type": "application/json", "X-Preset-Token": token},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read())
        assert payload["ok"] is True
        content = path.read_text(encoding="utf-8")
        assert "app_id" in content
        assert "details" in content
    finally:
        server.shutdown()
        server.server_close()
