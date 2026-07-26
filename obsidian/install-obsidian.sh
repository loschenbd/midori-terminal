#!/bin/sh
# Install the "Midori" Obsidian theme (Midori palette, mint dot grid + page
# glow, Spectral/M PLUS fonts) into every iCloud-synced Obsidian vault.
# This repo is the single source of truth; the vaults are install targets.
#
# Re-run after edits, then reload Obsidian (or toggle the theme) to pick up
# changes. Idempotent. Use ../sync.sh to pull live edits back into the repo.
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VAULTS="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"
THEME="Midori"
LEGACY="Dot Grid"   # theme was renamed; clean up the old install

pgrep -x Obsidian >/dev/null 2>&1 && obsidian_running=1 || obsidian_running=0

installed=0
for vault in "$VAULTS"/*/; do
  [ -d "$vault.obsidian" ] || continue

  dest="$vault.obsidian/themes/$THEME"
  mkdir -p "$dest"
  cp "$REPO_DIR/theme.css" "$REPO_DIR/manifest.json" "$dest/"

  # Retire the pre-rename copy so it stops showing up in the theme picker.
  [ -d "$vault.obsidian/themes/$LEGACY" ] && rm -rf "$vault.obsidian/themes/$LEGACY"

  # Point the vault at the renamed theme. Obsidian holds appearance.json in
  # memory and rewrites it on any settings change, so an external edit only
  # sticks while the app is closed — hence the note printed at the end.
  appearance="$vault.obsidian/appearance.json"
  if [ -f "$appearance" ]; then
    THEME="$THEME" LEGACY="$LEGACY" python3 - "$appearance" <<'PY'
import json, os, sys
path = sys.argv[1]
try:
    with open(path) as f:
        cfg = json.load(f)
except (OSError, ValueError):
    sys.exit(0)
if cfg.get("cssTheme", "") in (os.environ["LEGACY"], ""):
    cfg["cssTheme"] = os.environ["THEME"]
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
PY
  fi

  echo "Installed into $(basename "$vault")"
  installed=1
done

if [ "$installed" -eq 0 ]; then
  echo "No Obsidian vaults found under $VAULTS" >&2
  exit 1
fi

echo
if [ "$obsidian_running" -eq 1 ]; then
  echo "Obsidian is running: it keeps appearance.json in memory, so if the theme"
  echo "does not switch by itself, pick '$THEME' under Settings -> Appearance."
else
  echo "Done. '$THEME' is selected in every vault."
fi
