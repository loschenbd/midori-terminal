#!/bin/sh
# Run the installers against a sandbox, then PROVE the real targets were not
# touched. Prints a receipt to paste into the commit message.
#
# HOME REDIRECTION ALONE IS NOT A SANDBOX, and assuming it is would be the
# expensive mistake here. obsidian/install-obsidian.sh reads its extra vault
# list from "$REPO_DIR/extra-vaults.txt", whose entries are ABSOLUTE paths
# (/Users/.../Projects/CFA and five siblings). Those ignore $HOME completely,
# so an installer run with HOME pointed at a scratch directory would still
# write the theme, four plugins and community-plugins.json into six real
# vaults. The repo itself has to be copied, so REPO_DIR resolves inside the
# sandbox and picks up a sandboxed extra-vaults.txt.
#
# Usage:  sh tests/dryrun-installers.sh
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="${TMPDIR:-/tmp}/midori-dryrun.$$"
FAIL=0
ok()  { printf '  ok   %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*"; FAIL=1; }
cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT INT TERM

# --- fingerprint the real targets BEFORE ------------------------------------
# Content, not mtime: a copy of an identical file changes mtime and proves
# nothing either way.
real_fingerprint() {
  {
    find "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents" \
         -name theme.css -o -name community-plugins.json 2>/dev/null
    [ -f "$REPO/obsidian/extra-vaults.txt" ] && while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in ''|\#*) continue ;; esac
      find "${line%/}/.obsidian" -name theme.css -o -name community-plugins.json 2>/dev/null
    done < "$REPO/obsidian/extra-vaults.txt"
  } | sort | while IFS= read -r f; do
        [ -f "$f" ] && printf '%s  %s\n' "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$f"
      done
}

echo "== fingerprinting real vaults before =="
BEFORE="$SANDBOX.before"
mkdir -p "$SANDBOX"
real_fingerprint > "$BEFORE"
n_real=$(wc -l < "$BEFORE" | tr -d ' ')
if [ "$n_real" -eq 0 ]; then
  bad "fingerprinted 0 real files -- the harness is broken, not the repo.
       A sandbox that proves nothing was touched by examining nothing is
       exactly the false green this whole gate exists to prevent."
else
  ok "$n_real real vault files fingerprinted"
fi

# --- build the sandbox ------------------------------------------------------
echo "== building sandbox =="
mkdir -p "$SANDBOX/home" "$SANDBOX/vaults/alpha/.obsidian" "$SANDBOX/vaults/beta/.obsidian"
mkdir -p "$SANDBOX/home/Library/Mobile Documents/iCloud~md~obsidian/Documents/gamma/.obsidian"
# Copy the repo so REPO_DIR -- and therefore extra-vaults.txt -- resolves here.
mkdir -p "$SANDBOX/repo"
tar -C "$REPO" -cf - \
    --exclude='.git' --exclude='obsidian/.fontenv' --exclude='__pycache__' . \
  | tar -C "$SANDBOX/repo" -xf -
printf '%s\n%s\n' "$SANDBOX/vaults/alpha" "$SANDBOX/vaults/beta" \
  > "$SANDBOX/repo/obsidian/extra-vaults.txt"
ok "sandbox repo + 3 fake vaults (2 extra, 1 iCloud-shaped)"

# --- run ---------------------------------------------------------------------
echo "== running obsidian installer in the sandbox =="
out="$SANDBOX/out.txt"
if HOME="$SANDBOX/home" sh "$SANDBOX/repo/obsidian/install-obsidian.sh" > "$out" 2>&1; then
  installed=$(grep -c '^Installed into' "$out" || true)
  if [ "${installed:-0}" -eq 3 ]; then
    ok "installed into all 3 sandbox vaults"
  else
    bad "installed into ${installed:-0} sandbox vaults, expected 3"
    sed 's/^/       /' "$out" | head -20
  fi
  for v in "$SANDBOX/vaults/alpha" "$SANDBOX/vaults/beta"; do
    [ -f "$v/.obsidian/themes/Midori/theme.css" ] \
      && ok "$(basename "$v"): theme.css landed" \
      || bad "$(basename "$v"): theme.css missing"
  done
else
  bad "installer exited nonzero in the sandbox"
  sed 's/^/       /' "$out" | head -20
fi

# --- prove the real targets are untouched -----------------------------------
echo "== real vaults untouched =="
AFTER="$SANDBOX.after"
real_fingerprint > "$AFTER"
if [ "$n_real" -eq 0 ]; then
  # NEVER LET THE MESSAGE BE MORE GENERAL THAN THE ASSERTION. Two empty
  # fingerprints diff clean, and "all 0 real vault files byte-identical"
  # reads as a safety proof while proving nothing at all.
  bad "cannot assert anything: 0 real files were fingerprinted"
elif diff -q "$BEFORE" "$AFTER" >/dev/null 2>&1; then
  ok "all $n_real real vault files byte-identical before and after"
else
  bad "REAL VAULT FILES CHANGED -- the sandbox leaked:"
  diff "$BEFORE" "$AFTER" | sed 's/^/       /' | head -20
fi
rm -f "$BEFORE" "$AFTER"

echo
if [ "$FAIL" -eq 0 ]; then
  echo "DRYRUN-OK: 3/3 sandbox vaults installed, $n_real real files unchanged"
else
  echo "DRYRUN: failures above"
fi
exit "$FAIL"
