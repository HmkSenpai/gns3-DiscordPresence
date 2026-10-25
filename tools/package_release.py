"""Build the standalone executable and the release archives.

Usage::

    python tools/package_release.py            # build the exe + archives
    python tools/package_release.py --no-exe   # only refresh the archives

Outputs in ``dist/``:

* ``gns3-presence.exe`` (or ``gns3-presence`` on Linux/macOS)
* ``gns3-presence-<platform>.zip`` / ``.tar.gz``

Each archive contains the binary, the ``exemples/`` folder (sample
configuration + assets) and the README.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
EXAMPLES = ROOT / "exemples"
BINARY_NAME = "gns3-presence"


def build_executable() -> Path:
    """Run PyInstaller and return the path of the produced binary."""
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name",
        BINARY_NAME,
        "--collect-all",
        "pypresence",
        "--clean",
        "entrypoint.py",
    ]
    print("> " + " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)
    binary = DIST / (BINARY_NAME + (".exe" if platform.system() == "Windows" else ""))
    if not binary.exists():
        raise SystemExit(f"Binary not found: {binary}")
    return binary


def platform_tag() -> str:
    system = platform.system().lower()
    return {"windows": "windows", "darwin": "macos"}.get(system, "linux")


def stage(binary: Path) -> Path:
    """Create the folder that will be archived.

    The folder name carries the platform tag: on Linux/macOS the binary is
    called ``gns3-presence`` and a folder of the same name would collide.
    """
    stage_dir = DIST / f"{BINARY_NAME}-{platform_tag()}"
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)
    shutil.copy2(binary, stage_dir / binary.name)

    # Examples folder: sample configuration + assets to upload on Discord.
    examples_target = stage_dir / "exemples"
    examples_target.mkdir()
    for item in EXAMPLES.iterdir():
        if item.is_dir():
            shutil.copytree(item, examples_target / item.name)
        else:
            shutil.copy2(item, examples_target / item.name)

    for doc in ("README.md", "LICENSE"):
        source = ROOT / doc
        if source.exists():
            shutil.copy2(source, stage_dir / doc)
    return stage_dir


def archive(stage_dir: Path) -> Path:
    tag = platform_tag()
    if platform.system().lower() == "windows":
        archive_path = DIST / f"{BINARY_NAME}-{tag}.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as handle:
            for path in sorted(stage_dir.rglob("*")):
                handle.write(path, path.relative_to(stage_dir.parent))
    else:
        import tarfile

        archive_path = DIST / f"{BINARY_NAME}-{tag}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as handle:
            handle.add(stage_dir, arcname=stage_dir.name)
    return archive_path


def main() -> int:
    DIST.mkdir(exist_ok=True)
    binary = build_executable()
    stage_dir = stage(binary)
    archive_path = archive(stage_dir)
    size = archive_path.stat().st_size / (1024 * 1024)
    print(f"\nOK  {archive_path.name}  ({size:.1f} Mo)")
    print(f"    {binary.name}  ({binary.stat().st_size / (1024 * 1024):.1f} Mo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
