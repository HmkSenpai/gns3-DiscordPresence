import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gns3presence.config import DEFAULTS, Config, deep_merge
from gns3presence.editor import changes_from_settings, settings_from_config
from gns3presence.render import Renderer
from gns3presence.state import LabState, gns3_api

data = {}
config = Config(deep_merge(DEFAULTS, data), None, 0.0, data)
settings = settings_from_config(config)
settings.set("presence.show_project", False)
settings.set("presence.show_elapsed", False)

changes = changes_from_settings(settings, settings)
merged = config.data
for key, value in changes.items():
    node = merged
    parts = key.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
config2 = Config(merged, None, 0.0, data)

nodes = [
    gns3_api.ApiNode(name="R1", node_type="dynamips", status="started"),
    gns3_api.ApiNode(name="PC1", node_type="vpcs", status="stopped"),
]
state = LabState(
    project_id="x",
    project_name="TP0-CamTrust",
    nodes=nodes,
    links=[gns3_api.ApiLink(link_id="1")],
    server_version="2.2.61",
    opened=True,
    project_started_at=1700000000.0,
)
activity = Renderer(config2).render(state)
print("details =", repr(activity.details))
print("state   =", repr(activity.state))
print("payload =", activity.as_dict())
