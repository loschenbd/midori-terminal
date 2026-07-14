#!/bin/sh
# Install the "Dot Grid" Obsidian theme (Midori palette + Spectral/M PLUS
# fonts) into every iCloud-synced Obsidian vault. Re-run after edits; then
# reload Obsidian (or toggle the theme) to pick up changes.
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VAULTS="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"

installed=0
for vault in "$VAULTS"/*/; do
  [ -d "$vault/.obsidian" ] || continue
  dest="$vault.obsidian/themes/Dot Grid"
  mkdir -p "$dest"
  cp "$REPO_DIR/theme.css" "$REPO_DIR/manifest.json" "$dest/"
  echo "Installed into $(basename "$vault")"
  installed=1
done

if [ "$installed" -eq 0 ]; then
  echo "No Obsidian vaults found under $VAULTS" >&2
  exit 1
fi

echo "Done. Select the 'Dot Grid' theme in Obsidian Appearance settings."
