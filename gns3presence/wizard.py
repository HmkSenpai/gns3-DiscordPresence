"""First run assistant.

When no Discord application id is configured, the companion offers a small
interactive menu instead of failing with an error:

* paste your own Application ID (created on https://discord.com/developers/applications)
* use the shared application (zero configuration, default icons)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)

#: Application id of the shared "GNS3 Presence" application. It can be
#: overridden in the configuration file with ``discord.app_id``.
DEFAULT_APP_ID = "1562827344786235434"

BANNER = """
====================================================
 GNS3 Presence - assistant de premier lancement
====================================================
"""


def is_valid_app_id(value: str) -> bool:
    """Discord application ids are numeric strings."""
    value = (value or "").strip()
    return value.isdigit() and len(value) >= 15


def read_app_id(prompt: str = "  Application ID Discord : ") -> Optional[str]:
    """Ask the user for an Application ID (returns None if cancelled)."""
    try:
        raw = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    raw = raw.strip()
    if not raw:
        return None
    if not is_valid_app_id(raw):
        print("  [!] Cet identifiant ne ressemble pas a un Application ID Discord.")
        print("      Il se trouve dans General Information > Application ID.")
        return None
    return raw


def first_run(
    config_path: Optional[Path] = None,
    shared_app_id: str = DEFAULT_APP_ID,
    non_interactive: bool = False,
) -> Tuple[Optional[str], str]:
    """Run the first launch wizard.

    Returns ``(app_id, choice)`` where *choice* is ``"custom"``, ``"shared"``
    or ``"none"``.
    """
    print(BANNER)
    print("Aucune application Discord n'est encore configuree.")
    print()
    print("  1. Utiliser l'application partagee 'GNS3 Presence'")
    print("     -> zero configuration, l'affichage est immediat sur votre profil")
    print("     -> les icones par defaut du projet sont utilisees")
    print()
    print("  2. Utiliser ma propre application Discord")
    print("     -> https://discord.com/developers/applications")
    print("     -> 'New Application' -> General Information > Application ID")
    print("     -> Rich Presence > Art Assets -> uploadez les images du dossier")
    print("        'exemples/assets' (la cle = nom du fichier SANS extension)")
    print()

    if non_interactive or not sys.stdin or not sys.stdin.isatty():
        print("  [i] Mode non interactif : application partagee utilisee.")
        return shared_app_id, "shared"

    try:
        choice = input("  Choix [1/2] (1 par defaut) : ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        print("  [i] Aucune saisie : application partagee utilisee.")
        return shared_app_id, "shared"

    if choice in ("", "1"):
        return shared_app_id, "shared"

    app_id = read_app_id()
    if app_id:
        return app_id, "custom"
    print("  [i] Application partagee utilisee.")
    return shared_app_id, "shared"


def user_config_path() -> Path:
    """Path of the per-user configuration file."""
    from .config import CONFIG_FILENAME, user_data_dir  # local import to avoid cycles

    return user_data_dir() / CONFIG_FILENAME


def portable_config_path() -> Optional[Path]:
    """Config path next to the executable, when running in portable mode.

    Returns None when the program is not frozen or when no ``exemples``
    folder sits next to it (which means: not a portable install).
    """
    import sys

    if not getattr(sys, "frozen", False):
        return None
    folder = Path(sys.executable).resolve().parent
    if (folder / "exemples").is_dir():
        return folder / "config.toml"
    return None


def target_config_path(existing: Optional[Path] = None) -> Path:
    """Where the configuration should be written."""
    if existing is not None:
        return existing
    portable = portable_config_path()
    if portable is not None:
        return portable
    return user_config_path()


def sample_config_template() -> str:
    """Content of a fresh configuration file (commented, ready to edit)."""
    import sys

    candidates = []
    if getattr(sys, "frozen", False):
        folder = Path(sys.executable).resolve().parent
        candidates.append(folder / "exemples" / "config.toml")
    candidates.append(Path(__file__).resolve().parent.parent / "exemples" / "config.toml")
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        except OSError:
            continue
    return ""


def write_app_id_to_config(
    config_path: Path,
    app_id: str,
    preset: Optional[str] = None,
) -> bool:
    """Persist the Application ID in a configuration file."""
    target = config_path
    if target is None:
        target = target_config_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
    except OSError as exc:
        log.warning("Cannot read %s: %s", target, exc)
        existing = ""

    if not existing:
        # Start from the commented template so every option is discoverable.
        template = sample_config_template()
        if template:
            existing = template
            existing = existing.replace(
                '# app_id = "1562827344786235434"',
                f'app_id = "{app_id}"',
            )
            if f'app_id = "{app_id}"' not in existing:
                existing = existing.replace(
                    "[discord]", f'[discord]\napp_id = "{app_id}"', 1
                )

    if "[discord]" in existing:
        lines = existing.splitlines()
        replaced = False
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("app_id") and "=" in stripped:
                lines[index] = f'app_id = "{app_id}"'
                replaced = True
                break
        if replaced:
            existing = "\n".join(lines) + "\n"
        else:
            existing = existing.replace(
                "[discord]", f'[discord]\napp_id = "{app_id}"', 1
            )
    else:
        block = f'[discord]\napp_id = "{app_id}"\n'
        existing = existing.rstrip() + "\n\n" + block if existing.strip() else block

    if preset:
        existing += f'\n[presence]\npreset = "{preset}"\n'

    try:
        target.write_text(existing, encoding="utf-8")
    except OSError as exc:
        log.warning("Cannot write %s: %s", target, exc)
        return False
    print(f"  [OK] Configuration ecrite dans {target}")
    return True


def asset_instructions(assets_dir: Optional[Path] = None) -> List[str]:
    """Instructions shown when the user picks their own application."""
    lines = [
        "  Pour que tes icones s'affichent :",
        "    1. Ouvre ton application sur https://discord.com/developers/applications",
        "    2. Rich Presence > Art Assets > uploade les images",
        "    3. La cle de chaque asset est le nom du fichier SANS extension",
    ]
    if assets_dir and assets_dir.is_dir():
        names = sorted(path.stem for path in assets_dir.glob("*.png"))
        if names:
            lines.append(f"    Fichiers a uploader : {', '.join(names)}")
    return lines
