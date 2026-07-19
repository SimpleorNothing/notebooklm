"""
_browser.py — shared Playwright/session helpers for the NotebookLM skill.

All NotebookLM automation goes through a single Chromium instance whose Google
login is persisted to disk as a Playwright storage_state file. Nothing here
talks to a Google API directly (NotebookLM has no public API); every action is
driven through the real notebooklm.google.com web UI.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPTS_DIR.parent
AUTH_DIR = SKILL_ROOT / ".auth"
STATE_FILE = AUTH_DIR / "state.json"
CONFIG_DIR = SKILL_ROOT / "config"
SELECTORS_FILE = CONFIG_DIR / "selectors.json"

NOTEBOOKLM_URL = "https://notebooklm.google.com/"
# Google's default UA on the automation build sometimes triggers extra
# challenges; a stable desktop Chrome UA reduces friction.
DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def chromium_executable() -> Optional[str]:
    """Return the pre-installed Chromium binary, if we can find one.

    Passing this to launch() avoids Playwright trying to download a browser
    build that matches the pip driver version.
    """
    env = os.environ.get("NBLM_CHROMIUM_PATH")
    if env and Path(env).exists():
        return env
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    candidates = [
        Path(root) / "chromium",  # symlink installed in this environment
        Path(root) / "chromium-1194" / "chrome-linux" / "chrome",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def has_saved_session() -> bool:
    return STATE_FILE.exists() and STATE_FILE.stat().st_size > 0


def load_selectors() -> dict:
    """Load the tunable selector map, falling back to built-in defaults.

    NotebookLM's DOM changes without notice; keeping selectors in a JSON file
    lets an operator fix breakage without editing Python.
    """
    defaults = {
        # Anything that only exists once you are signed in and on the home page.
        "logged_in_marker": [
            "text=Create new",
            "text=New notebook",
            "text=새 노트북",
            "[aria-label*='notebook' i]",
        ],
        # Redirect target / elements that mean we are NOT signed in.
        "login_marker": [
            "input[type='email']",
            "text=Sign in",
            "text=로그인",
        ],
        # A tile/link representing a single notebook on the home page.
        "notebook_card": [
            "[role='listitem']",
            "a[href*='/notebook/']",
            "[data-test-id*='notebook']",
        ],
        # The chat question box inside a notebook.
        "chat_input": [
            "textarea",
            "[contenteditable='true']",
            "[role='textbox']",
            "[aria-label*='Ask' i]",
            "[placeholder*='Ask' i]",
        ],
        # Button to send the question (Enter is tried first regardless).
        "send_button": [
            "button[aria-label*='Send' i]",
            "button[aria-label*='Submit' i]",
            "button[type='submit']",
        ],
        # Container(s) holding assistant responses in the conversation.
        "response_block": [
            "[data-test-id*='response']",
            "[class*='response']",
            "[class*='message']",
            "chat-message",
        ],
    }
    if SELECTORS_FILE.exists():
        try:
            override = json.loads(SELECTORS_FILE.read_text())
            for k, v in override.items():
                if isinstance(v, list):
                    defaults[k] = v
        except Exception:
            pass
    return defaults


def _proxy_config() -> Optional[dict]:
    """Route Chromium through an outbound proxy if the environment mandates one.

    Managed/cloud containers often force egress through an HTTPS proxy; the CA
    it re-terminates TLS with is already trusted at the OS/NSS level there, so
    we only need to point Chromium at the proxy server. Set NBLM_PROXY to
    override (or "none" to force a direct connection).
    """
    override = os.environ.get("NBLM_PROXY")
    if override:
        return None if override.lower() == "none" else {"server": override}
    server = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    return {"server": server} if server else None


def launch(p, headless: bool = True, use_session: bool = True):
    """Launch Chromium and open a context.

    Returns (browser, context, page). Caller is responsible for closing the
    browser.
    """
    launch_kwargs = {
        "headless": headless,
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ],
    }
    exe = chromium_executable()
    if exe:
        launch_kwargs["executable_path"] = exe
    proxy = _proxy_config()
    if proxy:
        launch_kwargs["proxy"] = proxy

    browser = p.chromium.launch(**launch_kwargs)

    ctx_kwargs = {"user_agent": DEFAULT_UA, "viewport": {"width": 1280, "height": 900}}
    if use_session and has_saved_session():
        ctx_kwargs["storage_state"] = str(STATE_FILE)
    context = browser.new_context(**ctx_kwargs)
    page = context.new_page()
    return browser, context, page


def save_session(context) -> None:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(STATE_FILE))


def first_visible(page, selectors: list, timeout: int = 4000):
    """Return the first locator from `selectors` that is visible, or None."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:
            continue
    return None


def looks_logged_in(page, selectors: dict) -> bool:
    """Heuristic: signed-in if a home-page marker shows and no login form does."""
    if first_visible(page, selectors["login_marker"], timeout=2500) is not None:
        return False
    if "accounts.google.com" in page.url:
        return False
    return first_visible(page, selectors["logged_in_marker"], timeout=6000) is not None
