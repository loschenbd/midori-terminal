#!/bin/sh
# Patch the installed Claude Code binary so diff bands render the Midori washes
# WHILE syntax highlighting stays on. Claude Code hardcodes diff colours in the
# compiled binary (bypassing ~/.claude/themes), so the only lever is a binary
# patch: unpack the embedded JS (tweakcc) -> rewrite the 8 colour constants
# (tools/patch-claude-diffs.py) -> repack + ad-hoc re-sign (tweakcc).
#
# Idempotent and self-healing: any Claude Code update (the native installer's
# updater at ~/.local/share/claude/versions/<v>, or a brew upgrade on the cask)
# restores the stock binary, so re-run this after updates. The `claude` shell
# wrapper in zshrc.midori does it automatically when the resolved path changes.
# Needs: node 20+, npx (for `npx tweakcc`), python3.
#
# Restore the stock binary any time by copying back the per-version backup this
# script saves under ~/.config/midori/claude-backup/ (or `brew reinstall
# claude-code` if you installed via the brew cask).
set -e

# Find the JS patcher next to this script (installed copy in ~/.config/midori)
# or one level up under tools/ (running straight from the repo).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/patch-claude-diffs.py" ]; then
  PATCHER="$SCRIPT_DIR/patch-claude-diffs.py"
elif [ -f "$SCRIPT_DIR/../tools/patch-claude-diffs.py" ]; then
  PATCHER="$SCRIPT_DIR/../tools/patch-claude-diffs.py"
else
  echo "!! patch-claude-diffs.py not found next to $0 — skipping." >&2
  exit 0
fi
BACKUP_DIR="$HOME/.config/midori/claude-backup"
STAMP="$HOME/.config/midori/claude-patched-path"

CLAUDE_BIN="$(readlink -f "$(command -v claude 2>/dev/null)" 2>/dev/null || true)"
if [ -z "$CLAUDE_BIN" ] || [ ! -f "$CLAUDE_BIN" ]; then
  echo "!! claude binary not found on PATH — skipping diff patch." >&2
  exit 0
fi

# Native single-file binary only; npm/cli.js installs use a different path we
# don't support here.
case "$(file "$CLAUDE_BIN")" in
  *Mach-O*|*ELF*) : ;;
  *) echo "!! $CLAUDE_BIN is not a native binary — skipping diff patch." >&2; exit 0 ;;
esac

VERSION="$("$CLAUDE_BIN" --version 2>/dev/null | awk '{print $1}')"

# Truecolor canary. Inside tmux, Claude Code deliberately clamps its colour depth
# to 256 unless CLAUDE_CODE_TMUX_TRUECOLOR is set (upstream issue #35148). That
# escape hatch is UNDOCUMENTED, so a future release could remove or rename it and
# silently revert the Midori diffs to muddy 256-colour with no error. This runs on
# every version change (the shell `claude` wrapper re-invokes us then), so warn
# loudly if the hatch has vanished from the new binary.
if ! LC_ALL=C grep -q -a -F "CLAUDE_CODE_TMUX_TRUECOLOR" "$CLAUDE_BIN" 2>/dev/null; then
  echo "!! Claude Code $VERSION no longer contains CLAUDE_CODE_TMUX_TRUECOLOR." >&2
  echo "   The tmux truecolor escape hatch may have changed — diffs could render" >&2
  echo "   muddy 256-colour inside tmux again. Fallback: alias claude='TMUX= claude'." >&2
  echo "   Re-check upstream issue #35148 and update shell/zshrc.midori." >&2
fi

# Marker = signature of the NEWEST patch (codespan inline-code). Keying the
# idempotency check on this means adding a patch to patch-claude-diffs.py forces
# re-application over a binary that only has the older patches.
MARKER='?"#6c87a4":"#3a5572"'

# Fully patched already? -> nothing to do.
if LC_ALL=C grep -q -a -F "$MARKER" "$CLAUDE_BIN" 2>/dev/null; then
  echo "-- Claude Code $VERSION already carries the Midori patch set."
  mkdir -p "$(dirname "$STAMP")"; printf '%s\n' "$CLAUDE_BIN" > "$STAMP"
  exit 0
fi

for dep in node npx python3; do
  command -v "$dep" >/dev/null 2>&1 || { echo "!! '$dep' required, not found — skipping." >&2; exit 0; }
done

echo "-- Patching Claude Code $VERSION diff colours -> Midori washes"

# Back up the pristine binary for this version (once).
mkdir -p "$BACKUP_DIR"
BACKUP="$BACKUP_DIR/claude-$VERSION.stock"
[ -f "$BACKUP" ] || { cp "$CLAUDE_BIN" "$BACKUP"; echo "   backed up stock binary -> $BACKUP"; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

npx --yes tweakcc@4.3.1 unpack "$WORK/cc.js" "$CLAUDE_BIN" >/dev/null
python3 "$PATCHER" "$WORK/cc.js"
npx --yes tweakcc@4.3.1 repack "$WORK/cc.js" "$CLAUDE_BIN" >/dev/null

# Verify the patch actually landed and the binary still runs.
if ! LC_ALL=C grep -q -a -F "$MARKER" "$CLAUDE_BIN"; then
  echo "!! verification failed (Midori marker absent) — restoring stock binary." >&2
  cp "$BACKUP" "$CLAUDE_BIN"
  exit 1
fi
if ! "$CLAUDE_BIN" --version >/dev/null 2>&1; then
  echo "!! patched binary won't run — restoring stock binary." >&2
  cp "$BACKUP" "$CLAUDE_BIN"
  exit 1
fi

# Diff washes only show with syntax highlighting ON — undo the earlier opt-out.
python3 - <<'PY'
import json, os
p = os.path.expanduser("~/.claude/settings.json")
try:
    s = json.load(open(p))
except (FileNotFoundError, json.JSONDecodeError):
    s = {}
if s.get("syntaxHighlightingDisabled"):
    s.pop("syntaxHighlightingDisabled", None)
    json.dump(s, open(p, "w"), indent=2)
    print("   re-enabled syntax highlighting (removed syntaxHighlightingDisabled)")
PY

printf '%s\n' "$CLAUDE_BIN" > "$STAMP"
echo "   done — restart Claude Code to see Midori diffs + syntax highlighting."
