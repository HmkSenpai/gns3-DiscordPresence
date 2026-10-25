import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gns3presence import wizard

print("portable_config_path:", wizard.portable_config_path())
print("target_config_path:", wizard.target_config_path(None))
print("user_config_path:", wizard.user_config_path())
target = wizard.target_config_path(None)
ok = wizard.write_app_id_to_config(target, "123456789012345678")
print("write ok:", ok)
print("exists:", target.exists())
if target.exists():
    print(target.read_text(encoding="utf-8")[:200])
