---
name: notebooklm
description: Query and manage the user's Google NotebookLM notebooks. Use when the user asks to search, ask, or summarize from "my NotebookLM" / "노트북LM" / a named notebook (e.g. "내 NotebookLM에 물어봐줘 …", "ask my NotebookLM about …", "list my notebooks", "summarize the Research notebook"). NotebookLM has no public API, so this drives the real web UI with a saved Google login.
---

# NotebookLM agent

Drives Google NotebookLM (https://notebooklm.google.com) through its web UI
with Playwright, reusing a one-time Google sign-in. Everything runs through
`scripts/run.py`, which bootstraps an isolated venv on first use.

## Prerequisites (one time)

1. `python scripts/run.py auth_manager.py status` — bootstraps deps and checks login.
2. `python scripts/run.py auth_manager.py login` — sign in to Google (headed browser).
   - On a headless/cloud host with no display, sign in on your own machine,
     export a Playwright `storage_state` JSON, then
     `python scripts/run.py auth_manager.py import <state.json>` (see README).

## How to use (agent workflow)

When the user asks something like "내 NotebookLM에 물어봐줘: …" or "ask my
NotebookLM about X":

1. **Check auth** (only if unsure):
   `python scripts/run.py auth_manager.py status`
   If it reports not signed in, tell the user to run the `login` step — do not
   try to log in on their behalf without a browser.

2. **Find the notebook.** If the user named one, pass it to `--notebook`. If
   not, list them and pick/confirm:
   `python scripts/run.py notebooklm.py list`

3. **Ask the question:**
   `python scripts/run.py notebooklm.py ask --notebook "<title-or-id>" "<question>"`
   Add `--json` when you need structured output, `--timeout <sec>` for long
   answers, `--debug` to capture a screenshot/HTML on failure.

4. **Return the answer** to the user verbatim (it is grounded in their
   sources), and mention which notebook it came from.

## Commands

| Command | Purpose |
| --- | --- |
| `run.py auth_manager.py status` | Is there a valid session? |
| `run.py auth_manager.py login` | Interactive Google sign-in (headed). |
| `run.py auth_manager.py import <f>` | Import a storage_state JSON. |
| `run.py auth_manager.py logout` | Remove the saved session. |
| `run.py notebooklm.py list [--json]` | List notebooks. |
| `run.py notebooklm.py ask --notebook <n> "<q>" [--json] [--timeout N] [--debug]` | Ask in a notebook. |
| `run.py notebooklm.py open --notebook <n>` | Resolve a notebook URL. |

## When it breaks

NotebookLM's DOM changes without notice. If `list`/`ask` stop finding things,
edit `config/selectors.json` (first visible match wins per key) — no code
change needed. Re-run with `--debug` to capture `.auth/debug-*.png|html` for
inspection.

## Notes

- Session and venv live in `.auth/` and `.venv/` (gitignored). Never commit them.
- This does **not** use any private Google API; it automates the same UI a
  human uses, subject to the user's own account and Google's terms.
