#!/usr/bin/env bash
#
# install-notebooklm-skill.sh
# ----------------------------
# Copies the NotebookLM skill from this repo into a project's
# `.claude/skills/notebooklm` directory so Claude Code can discover and run it.
#
# Usage (from the repo root):
#   bash scripts/install-notebooklm-skill.sh [DEST_DIR]
#
#   DEST_DIR  Optional. Where to install the skill.
#             Defaults to "<git-repo-root>/.claude/skills/notebooklm",
#             or "$PWD/.claude/skills/notebooklm" if not inside a git repo.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="$REPO_ROOT/skill"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "✗ Source skill directory not found: $SRC_DIR" >&2
  exit 1
fi

# Resolve destination.
if [[ "${1:-}" != "" ]]; then
  DEST_DIR="$1"
else
  if PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    DEST_DIR="$PROJECT_ROOT/.claude/skills/notebooklm"
  else
    DEST_DIR="$PWD/.claude/skills/notebooklm"
  fi
fi

echo "Installing NotebookLM skill"
echo "  from: $SRC_DIR"
echo "  to:   $DEST_DIR"

mkdir -p "$DEST_DIR"
# Copy contents (including dotfiles) but never the local runtime state dirs.
cp -R "$SRC_DIR/." "$DEST_DIR/"
rm -rf "$DEST_DIR/.venv" "$DEST_DIR/.auth"

chmod +x "$DEST_DIR/scripts/run.py" 2>/dev/null || true

echo "✓ Installed."
echo
echo "Next steps:"
echo "  cd \"$DEST_DIR\""
echo "  python scripts/run.py auth_manager.py status   # first run bootstraps deps + checks login"
echo "  python scripts/run.py auth_manager.py login     # one-time Google sign-in"
