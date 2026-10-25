"""One off helper: rebuild a clean local config from the shipped template."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gns3presence.editor import reset_settings  # noqa: E402
from gns3presence.toml_edit import read_toml  # noqa: E402

target = Path(sys.argv[1])
template = Path(sys.argv[2]) if len(sys.argv) > 2 else None

if template and template.exists():
    content = template.read_text(encoding="utf-8")
    # Keep the application id if the broken file had one.
    app_id = "1562827344786235434"
    content = content.replace('# app_id = "1562827344786235434"', f'app_id = "{app_id}"')
    if f'app_id = "{app_id}"' not in content:
        content = content.replace("[discord]", f'[discord]\napp_id = "{app_id}"', 1)
    target.write_text(content, encoding="utf-8")
    print("rebuilt from", template)
else:
    target.write_text("", encoding="utf-8")

ok, message = reset_settings(target)
print("reset:", ok, message)
data = read_toml(target)
print("language:", data.get("language"))
print("sections:", list(data.keys()))
