"""End to end test of the web interface (API level)."""

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gns3presence.config import DEFAULTS, Config, deep_merge  # noqa: E402
from gns3presence.webapp import find_free_port, start_web_app  # noqa: E402

tmp = Path(__file__).parent.parent / ".tmp-webtest"
tmp.mkdir(exist_ok=True)
config_path = tmp / "config.toml"
config_path.write_text(
    '[discord]\napp_id = "123"\n\n[presence]\ndetails = "{project}"\n'
    'state = "{running}/{total} {t_nodes}"\n',
    encoding="utf-8",
)

data = {}
config = Config(deep_merge(DEFAULTS, data), config_path, 0.0, data)
server, url = start_web_app(
    config, config_path, port=find_free_port(8900), open_browser=False
)
token = url.split("token=")[1]


def get(path):
    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}") as r:
        return json.loads(r.read())


def post(path, payload):
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_address[1]}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Preset-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(request) as r:
        return json.loads(r.read())


try:
    state = get(f"/api/state?token={token}")
    print("STATE ok:", state["settings"]["presence.show_project"] is True)

    preview = post(f"/api/preview?token={token}", {"settings": {"presence.show_project": False}})
    print("PREVIEW:", preview["preview"])

    saved = post(
        f"/api/save?token={token}",
        {"settings": {"presence.show_project": False, "presence.show_elapsed": True}},
    )
    print("SAVE ok:", saved["ok"], saved["message"])
    print("--- file ---")
    print(config_path.read_text(encoding="utf-8"))

    state2 = get(f"/api/state?token={token}")
    print("show_project after save:", state2["settings"]["presence.show_project"])
    print("show_elapsed after save:", state2["settings"]["presence.show_elapsed"])
finally:
    server.shutdown()
    server.server_close()
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)
