"""Command line interface of the GNS3 Presence companion."""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from . import __version__, wizard
from . import presence as presence_mod
from .config import Config, load_config, reload_if_changed
from .discovery import candidate_endpoints
from .render import Renderer
from .state import Gns3Watcher

log = logging.getLogger(__name__)

OK = "[OK]"
KO = "[KO]"
WARN = "[!!]"
INFO = "[--]"

DASH = "-" * 62


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gns3-presence",
        description="Discord Rich Presence companion for GNS3.",
    )
    parser.add_argument("--version", action="version", version=f"gns3-presence {__version__}")
    parser.add_argument("-c", "--config", help="path to a configuration file (TOML)")
    parser.add_argument(
        "--app-id",
        help="Discord application id (skips the first run assistant)",
    )
    parser.add_argument(
        "--shared-app",
        action="store_true",
        help="use the shared 'GNS3 Presence' application (no configuration needed)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="run the first launch assistant and exit",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="run diagnostics (Discord, GNS3, application id, assets) and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the activity that would be published, without touching Discord",
    )
    parser.add_argument("--once", action="store_true", help="publish one activity and exit")
    parser.add_argument("--interval", type=float, help="poll interval in seconds")
    parser.add_argument(
        "--print-config", action="store_true", help="print the resolved configuration"
    )
    parser.add_argument(
        "--install-autostart",
        action="store_true",
        help="register the companion to start with the system",
    )
    parser.add_argument(
        "--uninstall-autostart",
        action="store_true",
        help="remove the autostart registration",
    )
    parser.add_argument("--no-tray", action="store_true", help="disable the tray icon")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose logs")
    return parser


# ---------------------------------------------------------------------------
# Autostart
# ---------------------------------------------------------------------------


def _start_command() -> List[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "gns3presence"]


def install_autostart() -> int:
    command = _start_command()
    if os.name == "nt":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        value = subprocess.list2cmdline(command)
        winreg.SetValueEx(key, "GNS3Presence", 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        print(f"{OK} Autostart registered (HKCU Run): {value}")
        return 0

    if sys.platform == "darwin":
        import plistlib

        agents = Path.home() / "Library" / "LaunchAgents"
        agents.mkdir(parents=True, exist_ok=True)
        plist_path = agents / "com.gns3presence.agent.plist"
        payload = {
            "Label": "com.gns3presence.agent",
            "ProgramArguments": command,
            "RunAtLoad": True,
            "KeepAlive": False,
        }
        with plist_path.open("wb") as handle:
            plistlib.dump(payload, handle)
        print(f"{OK} Autostart registered: {plist_path}")
        print(f"{INFO} Load it with: launchctl load -w {plist_path}")
        return 0

    autostart = Path.home() / ".config" / "autostart"
    autostart.mkdir(parents=True, exist_ok=True)
    desktop = autostart / "gns3-presence.desktop"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Exec={' '.join(command)}\n"
        "Name=GNS3 Presence\n"
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )
    print(f"{OK} Autostart registered: {desktop}")
    return 0


def uninstall_autostart() -> int:
    if os.name == "nt":
        import winreg

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.DeleteValue(key, "GNS3Presence")
            winreg.CloseKey(key)
            print(f"{OK} Autostart removed")
            return 0
        except FileNotFoundError:
            print(f"{INFO} Nothing to remove")
            return 0

    if sys.platform == "darwin":
        plist_path = Path.home() / "Library" / "LaunchAgents" / "com.gns3presence.agent.plist"
        if plist_path.exists():
            plist_path.unlink()
            print(f"{OK} Autostart removed")
        else:
            print(f"{INFO} Nothing to remove")
        return 0

    desktop = Path.home() / ".config" / "autostart" / "gns3-presence.desktop"
    if desktop.exists():
        desktop.unlink()
        print(f"{OK} Autostart removed")
    else:
        print(f"{INFO} Nothing to remove")
    return 0


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def discord_client_running() -> bool:
    """Is a Discord client running on this machine?"""
    if os.name == "nt":
        try:
            output = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Discord.exe", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout
            if "Discord.exe" in output:
                return True
        except Exception:
            pass
    # Named pipe check (works on every platform that supports Discord).
    try:
        if os.name == "nt":
            import ctypes

            handle = ctypes.windll.kernel32.CreateFileW(
                r"\\.\pipe\discord-ipc-0", 0x40000000, 0, None, 3, 0, None
            )
            if handle != -1:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
    except Exception:
        pass
    return False


def run_check(config: Config) -> int:
    """Print a diagnostic report and return an exit code (0 = everything fine)."""
    problems = 0
    print(DASH)
    print(" GNS3 Presence - diagnostic")
    print(DASH)

    print(f"{INFO} version           : {__version__}")
    print(f"{INFO} python           : {platform.python_version()} ({sys.platform})")
    print(f"{INFO} configuration    : {config.path or 'defaults (no file found)'}")

    # 1. Discord client
    if discord_client_running():
        print(f"{OK} Discord client    : running")
    else:
        print(f"{KO} Discord client    : NOT running - start Discord first")
        problems += 1

    # 2. pypresence
    if presence_mod.pypresence_available():
        print(f"{OK} pypresence       : installed")
    else:
        print(f"{KO} pypresence       : missing - pip install pypresence")
        problems += 1

    # 3. Application ID
    app_id = config.app_id
    if not app_id:
        print(f"{KO} application id   : missing - run with --setup (assistant)")
        print("      ou --shared-app pour utiliser l'application partagee")
        problems += 1
    elif not app_id.isdigit():
        print(f"{KO} application id   : '{app_id}' is not a valid Discord application id")
        problems += 1
    else:
        print(f"{OK} application id   : {app_id}")

    # 4. GNS3 server
    configured_url = str(config.get("gns3.url", "auto") or "auto")
    candidates = candidate_endpoints(
        configured_url, str(config.get("gns3.projects_path", "auto") or "auto")
    )
    watcher = Gns3Watcher(config)
    api = watcher.connect()
    if api is not None:
        version = watcher._server_version or "?"
        print(f"{OK} GNS3 server      : {watcher._server_url} (v{version})")
    else:
        print(f"{KO} GNS3 server      : unreachable")
        print(f"      tried: {', '.join(c.url for c in candidates[:8])}")
        problems += 1

    # 5. Current state
    state = watcher.poll()
    print(
        f"{INFO} current state    : {state.state_name} "
        f"(source: {state.source}, project: {state.project_name or '-'})"
    )
    if state.project_name:
        print(
            f"{INFO} nodes            : {state.running}/{state.total} started, "
            f"{state.link_count} links"
        )

    # 6. Rendered payload
    renderer = Renderer(config)
    activity = renderer.render(state)
    print(f"{INFO} rendered details : {activity.details!r}")
    print(f"{INFO} rendered state   : {activity.state!r}")
    if activity.small_image:
        print(
            f"{INFO} images           : large={activity.large_image!r} "
            f"small={activity.small_image!r}"
        )
    else:
        print(f"{INFO} images           : large={activity.large_image!r}")

    print(DASH)
    if problems:
        print(f" {problems} problem(s) found - see the messages above.")
    else:
        print(" Everything looks good.")
    print(DASH)
    return 1 if problems else 0


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run(config: Config, args: argparse.Namespace) -> int:
    interval = args.interval or float(config.get("discord.poll_interval", 15) or 15)
    min_update = float(config.get("discord.min_update_interval", 15) or 15)
    app_id = config.app_id

    # ---- first launch: no application id yet -----------------------------
    if args.app_id:
        app_id = args.app_id.strip()
    elif args.shared_app:
        app_id = wizard.DEFAULT_APP_ID
    elif not app_id:
        app_id, choice = wizard.first_run(
            config_path=config.path, shared_app_id=wizard.DEFAULT_APP_ID
        )
        if not app_id:
            print()
            print("  [i] Aucune application configuree : le tool va tourner sans presence.")
            print("      Relance-le plus tard avec --setup pour la configurer.")
            print()
        else:
            target = wizard.target_config_path(config.path)
            wizard.write_app_id_to_config(target, app_id)
            if choice == "custom":
                print()
                for line in wizard.asset_instructions():
                    print(line)
                print()

    if not args.dry_run and not app_id:
        log.error(
            "No Discord application id configured. Use --dry-run to preview, "
            "or run with --setup to configure it."
        )
        return 2

    watcher = Gns3Watcher(config)
    publisher = presence_mod.Publisher(app_id, min_interval=min_update, dry_run=args.dry_run)
    renderer = Renderer(config)

    paused = False
    running = True

    def stop() -> None:
        nonlocal running
        running = False

    def toggle_pause() -> bool:
        nonlocal paused
        paused = not paused
        log.info("Presence %s", "paused" if paused else "resumed")
        return paused

    def reload_config() -> None:
        nonlocal config
        config = reload_if_changed(config, args.config)

    tray = None
    if not args.no_tray and not args.once and not args.dry_run:
        try:
            from .tray import Tray, tray_available

            if tray_available():
                tray = Tray(
                    on_quit=stop,
                    on_pause=toggle_pause,
                    on_reload=reload_config,
                    status_provider=lambda: renderer.render(watcher.poll()).details or "Idle",
                )
                tray.start()
        except Exception as exc:
            log.debug("Tray not started: %s", exc)

    last_state_key = ""
    try:
        while running:
            config = reload_if_changed(config, args.config)
            renderer = Renderer(config)

            if paused:
                time.sleep(min(5, interval))
                continue

            state = watcher.poll()
            activity = renderer.render(state)

            if args.dry_run:
                payload = activity.as_dict()
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                if args.once:
                    return 0
                time.sleep(interval)
                continue

            published = publisher.publish(activity)

            state_key = f"{state.project_name}|{state.running}|{state.total}|{activity.details}|{activity.state}"
            if state_key != last_state_key:
                last_state_key = state_key
                log.info(
                    "GNS3: %s | project=%s | nodes=%s/%s | details=%s | state=%s%s",
                    state.state_name,
                    state.project_name or "-",
                    state.running,
                    state.total,
                    activity.details,
                    activity.state,
                    " (published)" if published else "",
                )

            if args.once:
                return 0

            time.sleep(max(2.0, interval))
    except KeyboardInterrupt:
        log.info("Interrupted by the user")
    finally:
        if tray is not None:
            tray.stop()
        if config.get("discord.clear_when_idle", True) and not args.dry_run:
            publisher.clear()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Make sure accented characters survive on legacy Windows consoles.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:  # pragma: no cover - not a real console
            pass

    from .log import setup_logging

    setup_logging(verbose=args.verbose)

    if args.install_autostart:
        return install_autostart()
    if args.uninstall_autostart:
        return uninstall_autostart()

    config = load_config(args.config)

    if args.print_config:
        print(json.dumps(config.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.setup:
        app_id, choice = wizard.first_run(
            config_path=config.path, shared_app_id=wizard.DEFAULT_APP_ID
        )
        if not app_id:
            print("  [!] Configuration annulee.")
            return 1
        target = wizard.target_config_path(config.path)
        wizard.write_app_id_to_config(target, app_id)
        if choice == "custom":
            print()
            for line in wizard.asset_instructions():
                print(line)
            print()
        print("  [OK] C'est pret : lance le tool pour afficher ta presence.")
        return 0

    if args.check:
        return run_check(config)

    return run(config, args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
