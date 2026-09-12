# One time Cosmo's daily automation setup

import os
import platform
import plistlib
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

PLIST_LABEL = "com.cosmo.autorun"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_LABEL}.plist")
WINDOWS_TASK_NAME = "CosmoAutoRun"
CRON_MARKER = "# cosmo-auto-run"
ANNOUNCE_HOUR_ET = 20
ANNOUNCE_MINUTE_ET = 15 # Adds buffer past the 8pm ET run time

def _local_time_for_announcement() -> tuple[int, int]:
    eastern = ZoneInfo("America/New_York")
    now_et = datetime.now(eastern).replace(hour=ANNOUNCE_HOUR_ET, minute=ANNOUNCE_MINUTE_ET, second=0, microsecond=0)
    local_now = now_et.astimezone()
    return local_now.hour, local_now.minute

def ensure_scheduler_installed() -> None:
    cosmo_dir = os.path.dirname(os.path.abspath(__file__))
    email_script = os.path.join(cosmo_dir, "cosmo_email.py")
    if not os.path.exists(email_script):
        return
    
    hour, minute = _local_time_for_announcement()
    system = platform.system()

    try:
        if system == "Darwin":
            _install_macos(cosmo_dir, email_script, hour, minute)
        elif system == "Windows":
            _install_windows(email_script, hour, minute)
        elif system == "Linux":
            _install_linux(email_script, hour, minute)
    except Exception:
        pass 

def _install_macos(cosmo_dir: str, email_script: str, hour: int, minute: int) -> None:
    wrapper_path = os.path.join(cosmo_dir, "CosmoPapers")
    wrapper_contents = f'#!/bin/bash\nexec "{sys.executable}" "{email_script}"\n'

    existing = None
    if os.path.exists(PLIST_PATH):
        try:
            with open(PLIST_PATH, "rb") as f:
                existing = plistlib.load(f)
        except Exception:
            existing = None

    needs_write = (
        existing is None
        or existing.get("StartCalendarInterval", {}).get("Hour") != hour
        or existing.get("StartCalendarInterval", {}).get("Minute") != minute
        or (existing.get("ProgramArguments") or [None])[0] != wrapper_path
        or not os.path.exists(wrapper_path)
    )
    if not needs_write:
        return

    with open(wrapper_path, "w") as f:
        f.write(wrapper_contents)
    os.chmod(wrapper_path, 0o755)

    plist_data = {
        "Label": PLIST_LABEL,
        "ProgramArguments": [wrapper_path],
        "WorkingDirectory": cosmo_dir,
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": os.path.join(cosmo_dir, "daily_run.log"),
        "StandardErrorPath": os.path.join(cosmo_dir, "daily_run_error.log"),
    }
    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    if os.path.exists(PLIST_PATH):
        subprocess.run(["launchctl", "unload", PLIST_PATH], check=False, capture_output=True)
    with open(PLIST_PATH, "wb") as f:
        plistlib.dump(plist_data, f)
    subprocess.run(["launchctl", "load", PLIST_PATH], check=False, capture_output=True)


def _install_windows(email_script: str, hour: int, minute: int) -> None:
    start_time = f"{hour:02d}:{minute:02d}"
    subprocess.run(
        [
            "schtasks", "/Create", "/F",
            "/SC", "DAILY",
            "/TN", WINDOWS_TASK_NAME,
            "/TR", f'"{sys.executable}" "{email_script}"',
            "/ST", start_time,
        ],
        check=False, capture_output=True,
    )

def _install_linux(email_script: str, hour: int, minute: int) -> None:
    result = subprocess.run(["crontab", "-l"], check=False, capture_output=True, text=True)
    existing_lines = result.stdout.splitlines() if result.returncode == 0 else []
    kept_lines = [line for line in existing_lines if CRON_MARKER not in line]

    new_line = f"{minute} {hour} * * * {sys.executable} {email_script} {CRON_MARKER}"
    updated = "\n".join(kept_lines + [new_line]) + "\n"

    subprocess.run(["crontab", "-"], input=updated, text=True, check=False)