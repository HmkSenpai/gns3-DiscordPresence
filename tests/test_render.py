"""Tests for the activity renderer."""

from __future__ import annotations

from gns3presence.config import DEFAULTS, Config, deep_merge
from gns3presence.render import Renderer, render_template

from .conftest import make_node, make_state


def build_config(**overrides) -> Config:
    return Config(deep_merge(DEFAULTS, overrides), None, 0.0)


def test_render_template_keeps_unknown_placeholders():
    assert render_template("a {known} b {unknown}", {"known": "X"}) == "a X b {unknown}"


def test_render_uses_project_and_counters():
    config = build_config()
    renderer = Renderer(config)
    state = make_state(
        nodes=[
            make_node("R1", "dynamips", "started"),
            make_node("R2", "dynamips", "stopped"),
            make_node("PC1", "vpcs", "started"),
        ],
        links=2,
    )
    activity = renderer.render(state)
    assert activity.details == "TP0-CamTrust"
    assert "2/3" in activity.state
    assert activity.party_size == [2, 3]
    assert activity.large_image == "gns3"


def test_preset_teacher_uses_summary():
    config = build_config(presence={"preset": "teacher"})
    renderer = Renderer(config)
    state = make_state(
        nodes=[make_node("R1", "dynamips", "started"), make_node("PC1", "vpcs", "started")],
        links=1,
    )
    activity = renderer.render(state)
    assert "routeur" in activity.state


def test_idle_state_when_nothing_is_open():
    config = build_config()
    renderer = Renderer(config)
    state = make_state(nodes=[], opened=False, project_name="")
    activity = renderer.render(state)
    assert activity.details == "Au repos"
    assert activity.large_image == "idle"


def test_rule_overrides_template():
    config = build_config(
        rules=[{"match": "TP0-*", "details": "Cours {project}", "state": "custom"}]
    )
    renderer = Renderer(config)
    activity = renderer.render(make_state())
    assert activity.details == "Cours TP0-CamTrust"
    assert activity.state == "custom"


def test_rule_regex_match():
    config = build_config(rules=[{"match": "re:devoir", "details": "hidden"}])
    renderer = Renderer(config)
    activity = renderer.render(make_state(project_name="Devoir final"))
    assert activity.details == "hidden"


def test_first_matching_rule_wins():
    config = build_config(
        rules=[
            {"match": "TP0-*", "details": "first"},
            {"match": "TP0-CamTrust", "details": "second"},
        ]
    )
    renderer = Renderer(config)
    activity = renderer.render(make_state())
    assert activity.details == "first"


def test_privacy_hides_project_name():
    config = build_config(privacy={"enabled": True})
    renderer = Renderer(config)
    activity = renderer.render(make_state(project_name="Examen TP"))
    assert activity.details == "Un lab réseau"
    assert "CamTrust" not in activity.state


def test_privacy_pattern_triggers():
    config = build_config(privacy={"patterns": ["secret"]})
    renderer = Renderer(config)
    activity = renderer.render(make_state(project_name="my secret lab"))
    assert activity.details == "Un lab réseau"


def test_privacy_can_be_forced_by_a_rule():
    config = build_config(rules=[{"match": "TP*", "privacy": True}])
    renderer = Renderer(config)
    activity = renderer.render(make_state())
    assert activity.details == "Un lab réseau"


def test_buttons_are_validated_and_limited():
    config = build_config(
        presence={
            "buttons": [
                {"label": "ok", "url": "https://example.com"},
                {"label": "bad", "url": "javascript:alert(1)"},
                {"label": "second", "url": "https://example.org"},
                {"label": "third", "url": "https://example.net"},
            ]
        }
    )
    renderer = Renderer(config)
    activity = renderer.render(make_state())
    assert len(activity.buttons) == 2
    assert all(b["url"].startswith("https://") for b in activity.buttons)


def test_small_image_follows_dominant_category():
    config = build_config()
    renderer = Renderer(config)
    state = make_state(
        nodes=[
            make_node("SW1", "ethernet_switch", "started"),
            make_node("SW2", "ethernet_switch", "started"),
            make_node("PC1", "vpcs", "stopped"),
        ]
    )
    activity = renderer.render(state)
    assert activity.small_image == "switch"
    assert activity.small_text == "switch"


def test_payload_is_truncated_to_discord_limits():
    config = build_config(presence={"details": "x" * 300, "state": "y" * 300})
    renderer = Renderer(config)
    activity = renderer.render(make_state())
    assert len(activity.details) <= 128
    assert len(activity.state) <= 128
