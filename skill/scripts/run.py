#!/usr/bin/env python3
"""
run.py — self-bootstrapping launcher for the NotebookLM skill scripts.

It creates (once) an isolated virtualenv next to the skill, installs the
Python dependencies into it, and then executes the requested script inside
that venv. This lets every other script assume Playwright is importable
without the caller worrying about environment setup.

Usage:
    python scripts/run.py <script.py> [args...]

Examples:
    python scripts/run.py auth_manager.py status
    python scripts/run.py auth_manager.py login
    python scripts/run.py notebooklm.py list
    python scripts/run.py notebooklm.py ask --notebook "My Notes" "Summarize source 2"

Environment:
    NBLM_PLAYWRIGHT_VERSION   Override the pinned playwright pip version.
    NBLM_FORCE_REINSTALL=1     Recreate the venv from scratch.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPTS_DIR.parent
VENV_DIR = SKILL_ROOT / ".venv"
REQUIREMENTS = SKILL_ROOT / "requirements.txt"
STAMP = VENV_DIR / ".deps-installed"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def log(msg: str) -> None:
    print(f"[run] {msg}", file=sys.stderr, flush=True)


def ensure_venv() -> None:
    force = os.environ.get("NBLM_FORCE_REINSTALL") == "1"
    if force and VENV_DIR.exists():
        import shutil

        log("NBLM_FORCE_REINSTALL=1 → removing existing venv")
        shutil.rmtree(VENV_DIR)

    if not venv_python().exists():
        log(f"creating virtualenv at {VENV_DIR}")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

    if STAMP.exists() and not force:
        return

    py = str(venv_python())
    log("installing dependencies (first run only, this can take a minute)")
    subprocess.run([py, "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=True)

    req_args = ["-r", str(REQUIREMENTS)] if REQUIREMENTS.exists() else []
    pin = os.environ.get("NBLM_PLAYWRIGHT_VERSION")
    if pin:
        req_args = [f"playwright=={pin}"]
    if not req_args:
        req_args = ["playwright"]

    # Browsers are pre-provisioned in this environment; never let pip's
    # postinstall try to download them.
    env = dict(os.environ, PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD="1")
    subprocess.run([py, "-m", "pip", "install", "--quiet", *req_args], check=True, env=env)

    STAMP.write_text("ok\n")
    log("dependencies ready")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    target_arg = sys.argv[1]
    target = Path(target_arg)
    if not target.is_absolute():
        # Resolve relative to the scripts dir so `run.py auth_manager.py` works
        # regardless of the current working directory.
        candidate = SCRIPTS_DIR / target.name
        target = candidate if candidate.exists() else (Path.cwd() / target_arg)

    if not target.exists():
        log(f"target script not found: {target_arg}")
        return 2

    ensure_venv()

    cmd = [str(venv_python()), str(target), *sys.argv[2:]]
    log(f"exec: {' '.join(cmd)}")
    completed = subprocess.run(cmd)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
