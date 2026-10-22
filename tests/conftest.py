"""Shared fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gns3presence.config import Config, deep_merge  # noqa: E402
from gns3presence.gns3_api import ApiLink, ApiNode  # noqa: E402
from gns3presence.state import LabState  # noqa: E402


@pytest.fixture
def config() -> Config:
    from gns3presence.config import DEFAULTS

    return Config(deep_merge(DEFAULTS, {}), None, 0.0)


def make_node(name: str, node_type: str, status: str = "stopped") -> ApiNode:
    return ApiNode(node_id=name.lower(), name=name, node_type=node_type, status=status)


def make_state(nodes=None, links=0, project_name="TP0-CamTrust", opened=True) -> LabState:
    state = LabState(
        project_id="abc",
        project_name=project_name,
        nodes=nodes if nodes is not None else [],
        links=[ApiLink(link_id=str(i)) for i in range(links)],
        server_version="2.2.61",
        server_url="http://localhost:80",
        source="api",
        opened=opened,
        project_started_at=1_700_000_000.0,
    )
    return state
