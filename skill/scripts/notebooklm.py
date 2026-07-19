#!/usr/bin/env python3
"""
notebooklm.py — query and manage Google NotebookLM from the command line.

Everything runs through the real notebooklm.google.com web UI using the
session saved by auth_manager.py. There is no public NotebookLM API.

Commands:
    list
        Print the notebooks visible on your NotebookLM home page.

    ask --notebook <name-or-id> "your question" [--json] [--timeout 90]
        Open a notebook, ask a question in its chat, and print the answer.

    open --notebook <name-or-id>
        Just resolve and print the notebook URL (useful for debugging).

Run via the launcher:
    python scripts/run.py notebooklm.py list
    python scripts/run.py notebooklm.py ask --notebook "Research" "Summarize the key findings"

Debugging:
    Add --debug to save a screenshot + HTML dump to .auth/ on failure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import _browser as B


def _require_session() -> None:
    if not B.has_saved_session():
        print("✗ not signed in. Run: python scripts/run.py auth_manager.py login", file=sys.stderr)
        raise SystemExit(1)


def _dump_debug(page, tag: str) -> None:
    try:
        B.AUTH_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(B.AUTH_DIR / f"debug-{tag}.png"), full_page=True)
        (B.AUTH_DIR / f"debug-{tag}.html").write_text(page.content())
        print(f"  (debug artifacts written to {B.AUTH_DIR}/debug-{tag}.*)", file=sys.stderr)
    except Exception:
        pass


def _collect_notebooks(page, selectors) -> list[dict]:
    """Scrape notebook cards from the home page → [{title, url, id}]."""
    notebooks: list[dict] = []
    seen = set()
    # Anchors to notebooks are the most reliable signal.
    try:
        anchors = page.locator("a[href*='/notebook/']")
        count = anchors.count()
    except Exception:
        count = 0
    for i in range(count):
        try:
            a = anchors.nth(i)
            href = a.get_attribute("href") or ""
            m = re.search(r"/notebook/([\w-]+)", href)
            nb_id = m.group(1) if m else ""
            title = (a.inner_text() or "").strip().splitlines()[0] if a.inner_text() else ""
            if not title:
                title = (a.get_attribute("aria-label") or "").strip()
            url = href if href.startswith("http") else f"https://notebooklm.google.com{href}"
            key = nb_id or url
            if key and key not in seen:
                seen.add(key)
                notebooks.append({"title": title or "(untitled)", "url": url, "id": nb_id})
        except Exception:
            continue
    return notebooks


def _open_home(page, selectors) -> None:
    page.goto(B.NOTEBOOKLM_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3000)
    if not B.looks_logged_in(page, selectors):
        raise SystemExit(
            "✗ session is not valid. Re-run: python scripts/run.py auth_manager.py login"
        )


def _resolve_notebook(page, selectors, ref: str) -> dict | None:
    """Resolve a notebook by id (exact) or by title (case-insensitive contains)."""
    notebooks = _collect_notebooks(page, selectors)
    # Exact id match first.
    for nb in notebooks:
        if nb["id"] and nb["id"] == ref:
            return nb
    # Title contains.
    low = ref.lower()
    matches = [nb for nb in notebooks if low in nb["title"].lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print("Multiple notebooks match; be more specific:", file=sys.stderr)
        for nb in matches:
            print(f"  - {nb['title']}  ({nb['id']})", file=sys.stderr)
        return None
    # Maybe ref is itself a full URL or bare id we didn't see listed.
    if re.fullmatch(r"[\w-]{6,}", ref):
        return {"title": ref, "id": ref, "url": f"https://notebooklm.google.com/notebook/{ref}"}
    return None


def cmd_list(args) -> int:
    _require_session()
    selectors = B.load_selectors()
    with sync_playwright() as p:
        browser, context, page = B.launch(p, headless=True, use_session=True)
        try:
            _open_home(page, selectors)
            notebooks = _collect_notebooks(page, selectors)
            if args.json:
                print(json.dumps(notebooks, ensure_ascii=False, indent=2))
            elif not notebooks:
                print("(no notebooks found)")
            else:
                for nb in notebooks:
                    print(f"{nb['title']}\t{nb['id']}")
            return 0
        except SystemExit as e:
            print(e, file=sys.stderr)
            if args.debug:
                _dump_debug(page, "list")
            return 1
        finally:
            browser.close()


def _ask_in_notebook(page, selectors, question: str, timeout_s: int) -> str:
    box = B.first_visible(page, selectors["chat_input"], timeout=15000)
    if box is None:
        raise RuntimeError("could not find the chat input box in this notebook")

    box.click()
    box.fill(question)

    # Capture how many response blocks exist before we send, so we can detect
    # the new one.
    resp_selectors = selectors["response_block"]
    before = 0
    for sel in resp_selectors:
        try:
            before = max(before, page.locator(sel).count())
        except Exception:
            continue

    # Prefer Enter; fall back to a send button.
    sent = False
    try:
        box.press("Enter")
        sent = True
    except Exception:
        pass
    if not sent:
        btn = B.first_visible(page, selectors["send_button"], timeout=4000)
        if btn is not None:
            btn.click()

    # Wait for a new response block to appear and stop growing.
    import time

    deadline = time.time() + timeout_s
    last_text = ""
    stable_for = 0
    while time.time() < deadline:
        page.wait_for_timeout(1500)
        text = _latest_response_text(page, resp_selectors, before)
        if text and text == last_text:
            stable_for += 1
            if stable_for >= 2:  # ~3s unchanged → treat as complete
                return text
        else:
            stable_for = 0
        last_text = text
    if last_text:
        return last_text
    raise RuntimeError("timed out waiting for a response")


def _latest_response_text(page, resp_selectors, before_count: int) -> str:
    for sel in resp_selectors:
        try:
            loc = page.locator(sel)
            n = loc.count()
            if n == 0:
                continue
            # Take the last block; if new blocks were added, prefer those.
            idx = n - 1
            txt = (loc.nth(idx).inner_text() or "").strip()
            if txt:
                return txt
        except Exception:
            continue
    return ""


def cmd_ask(args) -> int:
    _require_session()
    selectors = B.load_selectors()
    with sync_playwright() as p:
        browser, context, page = B.launch(p, headless=True, use_session=True)
        try:
            _open_home(page, selectors)
            nb = _resolve_notebook(page, selectors, args.notebook)
            if nb is None:
                print(f"✗ notebook not found: {args.notebook}", file=sys.stderr)
                return 1
            page.goto(nb["url"], wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3500)
            answer = _ask_in_notebook(page, selectors, args.question, args.timeout)
            if args.json:
                print(json.dumps(
                    {"notebook": nb["title"], "id": nb["id"], "question": args.question,
                     "answer": answer},
                    ensure_ascii=False, indent=2))
            else:
                print(answer)
            return 0
        except (RuntimeError, SystemExit) as e:
            print(f"✗ {e}", file=sys.stderr)
            if args.debug:
                _dump_debug(page, "ask")
            return 1
        finally:
            browser.close()


def cmd_open(args) -> int:
    _require_session()
    selectors = B.load_selectors()
    with sync_playwright() as p:
        browser, context, page = B.launch(p, headless=True, use_session=True)
        try:
            _open_home(page, selectors)
            nb = _resolve_notebook(page, selectors, args.notebook)
            if nb is None:
                print(f"✗ notebook not found: {args.notebook}", file=sys.stderr)
                return 1
            print(nb["url"])
            return 0
        finally:
            browser.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notebooklm.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--debug", action="store_true",
                        help="dump screenshot/HTML to .auth/ on failure")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list notebooks")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_ask = sub.add_parser("ask", help="ask a question in a notebook")
    p_ask.add_argument("--notebook", required=True, help="notebook title or id")
    p_ask.add_argument("question", help="the question to ask")
    p_ask.add_argument("--json", action="store_true")
    p_ask.add_argument("--timeout", type=int, default=90, help="seconds to wait for an answer")
    p_ask.set_defaults(func=cmd_ask)

    p_open = sub.add_parser("open", help="resolve a notebook URL")
    p_open.add_argument("--notebook", required=True)
    p_open.set_defaults(func=cmd_open)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
