"""Tests for the state watcher and the Discord publisher."""

from __future__ import annotations

from gns3presence.gns3_api import ApiProject
from gns3presence.presence import Publisher
from gns3presence.render import Activity
from gns3presence.state import Gns3Watcher


def test_pick_project_prefers_the_opened_one():
    projects = [
        ApiProject(project_id="1", name="closed-one", status="closed"),
        ApiProject(project_id="2", name="opened-one", status="opened"),
    ]
    assert Gns3Watcher._pick_project(projects).project_id == "2"


def test_pick_project_returns_none_when_everything_is_closed():
    projects = [ApiProject(project_id="1", name="a", status="closed")]
    assert Gns3Watcher._pick_project(projects) is None


def test_publisher_skips_identical_payloads():
    # dry_run: never touch the real Discord client.
    publisher = Publisher("123", min_interval=0, dry_run=True)
    activity = Activity(details="hello", state="world")
    assert publisher.publish(activity) is True
    assert publisher.publish(activity) is False  # unchanged payload


def test_publisher_respects_the_minimum_interval():
    publisher = Publisher("123", min_interval=999, dry_run=True)
    assert publisher.publish(Activity(details="a")) is True
    publisher._last_payload_hash = ""
    assert publisher.publish(Activity(details="b")) is False
