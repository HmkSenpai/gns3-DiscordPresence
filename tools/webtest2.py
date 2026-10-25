import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gns3presence.config import DEFAULTS, Config, deep_merge
from gns3presence.webapp import start_web_app

tmp = Path(__file__).parent.parent / ".tmp-webtest2"
tmp.mkdir(exist_ok=True)
config_path = tmp / "config.toml"
config_path.write_text('[discord]\napp_id = "123"\n', encoding="utf-8")

data = {}
config = Config(deep_merge(DEFAULTS, data), config_path, 0.0, data)
server, url = start_web_app(config, config_path, port=8950, open_browser=False)
token = url.split("token=")[1]
base = f"http://127.0.0.1:{server.server_address[1]}"

print("URL:", url)
try:
    with urllib.request.urlopen(f"{base}/api/state?token={token}") as r:
        print("GET state ->", r.status)
        payload = json.loads(r.read())
        print("lab:", payload["lab"])
        print("settings count:", len(payload["settings"]))

    # POST preview
    req = urllib.request.Request(
        f"{base}/api/preview?token={token}",
        data=json.dumps({"settings": {"presence.show_project": False}}).encode(),
        headers={"Content-Type": "application/json", "X-Preset-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        print("POST preview ->", r.status, json.loads(r.read())["preview"])

    # POST save
    req = urllib.request.Request(
        f"{base}/api/save?token={token}",
        data=json.dumps({"settings": {"presence.show_project": False}}).encode(),
        headers={"Content-Type": "application/json", "X-Preset-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        data2 = json.loads(r.read())
        print("POST save ->", r.status, data2["ok"], data2["message"])
    print("--- file ---")
    print(config_path.read_text(encoding="utf-8"))
finally:
    server.shutdown()
    server.server_close()
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)

