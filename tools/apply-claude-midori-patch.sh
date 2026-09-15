#!/bin/sh
# Make Claude Code draw inline code and tips in the terminal's ANSI blue, which the
# Midori terminal themes set to the colours those two theme tokens were meant to
# have (#3a5572 paper, #6c87a4 night). Both render paths ignore ~/.claude/themes,
# so the only lever is the binary: tools/patch-claude-binary.py writes a patched
# COPY with the call sites rewritten in place and the precompiled bytecode of the
# modules that hold them dropped; this script re-signs that copy, checks it, backs
# up the stock binary, and renames the copy over it. Mechanism and measurements,
# including why diff bands are no longer patched, are in that file's docstring.
#
# Until Sept 2026 this unpacked the embedded JS with tweakcc, edited it, and
# repacked. tweakcc cannot extract Claude Code 2.1.229 or later, so nothing was
# patched from 2.1.229 through 2.1.272. The in-place edit needs python3, plus
# codesign on macOS: no node, no npx, no download.
#
# Idempotent and self-healing: any Claude Code update (the native installer's
# updater at ~/.local/share/claude/versions/<v>, or a brew upgrade on the cask)
# restores the stock binary, so re-run this after updates. The `claude` shell
# wrapper in zshrc.midori does it automatically when the resolved path changes.
#
# Restore the stock binary any time by copying back the per-version backup this
# script saves under ~/.config/midori/claude-backup/ (or `brew reinstall
# claude-code` if you installed via the brew cask).
set -e

# --auto: invoked by the shell wrapper on every `claude` launch. Suppresses the
# "this build is unpatchable" notice so a blocked version does not print on each
# shell. Hand-runs (no flag) still explain themselves.
AUTO=0
[ "$1" = "--auto" ] && AUTO=1

# Documented escape hatch. Set MIDORI_SKIP_CC_PATCH=1 to leave the stock binary
# alone — useful when debugging whether a Claude Code problem is ours.
if [ -n "$MIDORI_SKIP_CC_PATCH" ]; then
  [ "$AUTO" = "1" ] || echo "-- MIDORI_SKIP_CC_PATCH set; leaving Claude Code unpatched."
  exit 0
fi

# Find the patcher next to this script (installed copy in ~/.config/midori)
# or one level up under tools/ (running straight from the repo).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/patch-claude-binary.py" ]; then
  PATCHER="$SCRIPT_DIR/patch-claude-binary.py"
elif [ -f "$SCRIPT_DIR/../tools/patch-claude-binary.py" ]; then
  PATCHER="$SCRIPT_DIR/../tools/patch-claude-binary.py"
else
  echo "!! patch-claude-binary.py not found next to $0 — skipping." >&2
  exit 0
fi
BACKUP_DIR="$HOME/.config/midori/claude-backup"
STAMP="$HOME/.config/midori/claude-patched-path"
# Records a build the patcher refused (its exit 2), so the wrapper doesn't re-read
# a 200 MB binary on every `claude` launch only to refuse it again. Keyed on the
# binary PATH and the patch METHOD: a new Claude Code version retries by itself,
# and so does a new method. The tweakcc patch recorded the path alone, so the
# 2.1.229+ builds it gave up on no longer match and get tried again.
# Cleared on the next successful patch.
UNPATCHABLE="$HOME/.config/midori/claude-unpatchable"
METHOD="bun-module-table-1"

CLAUDE_BIN="$(readlink -f "$(command -v claude 2>/dev/null)" 2>/dev/null || true)"
if [ -z "$CLAUDE_BIN" ] || [ ! -f "$CLAUDE_BIN" ]; then
  echo "!! claude binary not found on PATH — skipping Midori patch." >&2
  exit 0
fi

# Another account's binary? The patched copy is written beside the binary and
# renamed over it, so both the file and its directory must be writable by this
# account. On a Mac shared between accounts, Homebrew's claude-code cask sits
# under the prefix of whoever installed Homebrew. Checking here, before the
# patcher reads 200 MB, keeps the `claude` wrapper from paying that on every
# launch only to fail at the write. (The tweakcc version of this script would have
# backed up and unpacked the binary first, then failed at repack.) Nothing is
# recorded, so the patch applies as soon as the binary on PATH is one this
# account can write.
if [ ! -w "$CLAUDE_BIN" ] || [ ! -w "$(dirname "$CLAUDE_BIN")" ]; then
  if [ "$AUTO" != "1" ]; then
    echo "-- $CLAUDE_BIN is not writable by this account; Midori patch skipped."
    echo "   If the account that owns it has patched it, this account sees the patch too."
  fi
  exit 0
fi

# Known-unpatchable build? Bail before anything expensive: the wrapper runs us on
# every `claude` launch until a build is patched or recorded. (The tweakcc patch
# measured ~3 s for its checks on a 295 MB binary; the patcher reads the whole
# file.)
if [ "$(cat "$UNPATCHABLE" 2>/dev/null)" = "$CLAUDE_BIN $METHOD" ]; then
  # --auto means the shell wrapper called us: stay silent. A hand-run explains.
  if [ "$AUTO" != "1" ]; then
    V="$("$CLAUDE_BIN" --version 2>/dev/null | awk '{print $1}')"
    echo "-- The Midori patch doesn't recognise Claude Code $V's layout; skipped."
    echo "   Recorded in $UNPATCHABLE. Retries by itself on the next Claude Code"
    echo "   update, or delete that file to force another attempt."
  fi
  exit 0
fi

# Native single-file binary only; npm/cli.js installs use a different path we
# don't support here.
KIND="$(file "$CLAUDE_BIN")"
case "$KIND" in
  *Mach-O*|*ELF*) : ;;
  *) echo "!! $CLAUDE_BIN is not a native binary — skipping Midori patch." >&2; exit 0 ;;
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

command -v python3 >/dev/null 2>&1 || { echo "!! python3 required, not found — skipping." >&2; exit 0; }
case "$KIND" in
  *Mach-O*) command -v codesign >/dev/null 2>&1 || {
    echo "!! codesign required to re-sign a Mach-O binary, not found — skipping." >&2; exit 0; } ;;
esac

# The copy sits beside the binary, so the final rename is atomic and a Claude Code
# that is already running keeps the stock file it has open.
TMP="$CLAUDE_BIN.midori-$$"
trap 'rm -f "$TMP"' EXIT
rc=0
out="$(python3 "$PATCHER" "$CLAUDE_BIN" "$TMP" 2>&1)" || rc=$?
case "$rc" in
  0) : ;;
  3)
    [ "$AUTO" = "1" ] || echo "-- Claude Code $VERSION already carries the Midori patch."
    mkdir -p "$(dirname "$STAMP")"; printf '%s\n' "$CLAUDE_BIN" > "$STAMP"
    exit 0 ;;
  2)
    echo "!! The Midori patch doesn't recognise Claude Code $VERSION: $out" >&2
    echo "   Inline code and tips stay stock blue. Not retrying until the next Claude" >&2
    echo "   Code update; tools/patch-claude-binary.py needs its anchors checked." >&2
    mkdir -p "$(dirname "$UNPATCHABLE")"
    printf '%s %s\n' "$CLAUDE_BIN" "$METHOD" > "$UNPATCHABLE"
    exit 0 ;;
  *)
    echo "!! tools/patch-claude-binary.py failed (exit $rc): $out" >&2
    exit 1 ;;
esac

echo "-- Patching Claude Code $VERSION: inline code + tips -> terminal ANSI blue"
printf '%s\n' "$out" | sed 's/^/   /'
chmod 755 "$TMP"
case "$KIND" in
  *Mach-O*) codesign -f -s - "$TMP" >/dev/null 2>&1 || {
    echo "!! codesign failed — stock binary left in place." >&2; exit 1; } ;;
esac

# Verify the copy before it replaces anything: the patcher must recognise its own
# output, and the binary must still start. `--version` returns in ~0.01 s without
# loading the rewritten modules, so it proves the signature and the module table
# are intact, not the colours; the render was checked by hand (patcher docstring).
vrc=0
python3 "$PATCHER" "$TMP" /dev/null >/dev/null 2>&1 || vrc=$?
if [ "$vrc" != 3 ]; then
  echo "!! verification failed (patcher exit $vrc on its own output) — stock binary left in place." >&2
  exit 1
fi
if ! "$TMP" --version >/dev/null 2>&1; then
  echo "!! patched binary won't run — stock binary left in place." >&2
  exit 1
fi

# Back up the pristine binary for this version (once), then swap the copy in.
mkdir -p "$BACKUP_DIR"
BACKUP="$BACKUP_DIR/claude-$VERSION.stock"
[ -f "$BACKUP" ] || { cp "$CLAUDE_BIN" "$BACKUP"; echo "   backed up stock binary -> $BACKUP"; }
mv -f "$TMP" "$CLAUDE_BIN"

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
rm -f "$UNPATCHABLE"   # this build patched fine; clear any earlier block
echo "   done — restart Claude Code to see Midori inline code and tips."
