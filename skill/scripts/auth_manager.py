#!/usr/bin/env python3
"""
auth_manager.py — manage the persisted Google/NotebookLM login session.

Commands:
    status              Report whether a usable NotebookLM session exists.
    login [--headless]  Interactive Google sign-in; saves the session.
                        Defaults to a headed browser (you need a display).
    import <file.json>  Import a Playwright storage_state exported elsewhere.
    logout              Delete the saved session.

Run via the launcher so dependencies are present:
    python scripts/run.py auth_manager.py status
    python scripts/run.py auth_manager.py login

Headless-server note:
    A managed/cloud container usually has no display, so `login` cannot open a
    real browser for you. In that case, sign in to NotebookLM in a normal
    Chrome/Chromium on your own machine, export the storage_state to JSON, and
    bring it over with `import`. See README for a copy-paste export snippet.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import _browser as B


def cmd_status() -> int:
    if not B.has_saved_session():
        print("● not signed in — no saved session.")
        print("  run:  python scripts/run.py auth_manager.py login")
        return 1

    selectors = B.load_selectors()
    with sync_playwright() as p:
        browser, context, page = B.launch(p, headless=True, use_session=True)
        try:
            page.goto(B.NOTEBOOKLM_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
            ok = B.looks_logged_in(page, selectors)
            if ok:
                print("✓ signed in — NotebookLM session is valid.")
                email = _detect_email(page)
                if email:
                    print(f"  account: {email}")
                return 0
            print("✗ session expired or invalid — please sign in again.")
            print("  run:  python scripts/run.py auth_manager.py login")
            return 1
        finally:
            browser.close()


def _detect_email(page) -> str | None:
    for sel in [
        "[aria-label*='@']",
        "a[href*='SignOutOptions']",
        "img[alt*='@']",
    ]:
        try:
            val = page.locator(sel).first.get_attribute("aria-label", timeout=1500)
            if val and "@" in val:
                return val.strip()
        except Exception:
            continue
    return None


def cmd_login(headless: bool) -> int:
    if headless:
        print("Attempting headless sign-in — this only works if you are already")
        print("authenticated at the OS/browser profile level, which is rare.")
    else:
        print("A browser window will open. Sign in to your Google account and")
        print("open NotebookLM. This tool waits until it detects you are in.")

    selectors = B.load_selectors()
    with sync_playwright() as p:
        browser, context, page = B.launch(p, headless=headless, use_session=False)
        try:
            page.goto(B.NOTEBOOKLM_URL, wait_until="domcontentloaded", timeout=45000)
            print("Waiting for a signed-in NotebookLM home page (up to 5 minutes)…")
            deadline = 300  # seconds
            waited = 0
            while waited < deadline:
                if B.looks_logged_in(page, selectors):
                    B.save_session(context)
                    print(f"✓ signed in — session saved to {B.STATE_FILE}")
                    return 0
                page.wait_for_timeout(2000)
                waited += 2
            print("✗ timed out waiting for sign-in.")
            return 1
        except Exception as e:  # pragma: no cover - environment dependent
            print(f"✗ login failed: {e}")
            if headless:
                print("  A headless container cannot show a login page. Use the")
                print("  `import` flow instead (see README).")
            return 1
        finally:
            browser.close()


def cmd_import(src: str) -> int:
    src_path = Path(src).expanduser()
    if not src_path.exists():
        print(f"✗ file not found: {src_path}")
        return 1
    try:
        import json

        json.loads(src_path.read_text())  # validate
    except Exception as e:
        print(f"✗ not valid JSON storage_state: {e}")
        return 1
    B.AUTH_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_path, B.STATE_FILE)
    print(f"✓ imported session → {B.STATE_FILE}")
    print("  verify with:  python scripts/run.py auth_manager.py status")
    return 0


def cmd_logout() -> int:
    if B.STATE_FILE.exists():
        B.STATE_FILE.unlink()
        print("✓ signed out — saved session removed.")
    else:
        print("● nothing to do — no saved session.")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "status":
        return cmd_status()
    if cmd == "login":
        return cmd_login(headless="--headless" in rest)
    if cmd == "import":
        if not rest:
            print("usage: auth_manager.py import <storage_state.json>")
            return 2
        return cmd_import(rest[0])
    if cmd == "logout":
        return cmd_logout()
    print(f"unknown command: {cmd}")
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
