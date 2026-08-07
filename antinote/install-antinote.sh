#!/bin/sh
# Install the Midori Paper / Midori Night Antinote themes.
# This repo is the single source of truth; the theme folder is an install
# target. Idempotent — re-run after edits, then click "Reload Custom Themes"
# under Settings -> Visuals (no restart needed).
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Antinote is sandboxed, and the container id depends on where the app came
# from (Setapp vs direct/App Store). Install into every folder that exists
# rather than guessing one — a machine can legitimately have both.
installed=0
for dest in \
  "$HOME"/Library/Containers/com.chabomakers.Antinote*/Data/Documents/Themes \
  "$HOME/Library/Application Support/Antinote/Themes"
do
  # The glob stays literal when it matches nothing; the Application Support
  # path is only real for a non-sandboxed build.
  case "$dest" in *'*'*) continue ;; esac
  [ -d "$dest" ] || continue

  cp -f "$REPO_DIR/midori-paper.json" "$REPO_DIR/midori-night.json" "$dest/"
  echo "Installed into ${dest#$HOME/}"
  installed=1
done

if [ "$installed" -eq 0 ]; then
  echo "No Antinote theme folder found." >&2
  echo "Open Antinote -> Settings -> Visuals, click the button that opens the" >&2
  echo "theme folder, and copy these two files in:" >&2
  echo "  $REPO_DIR/midori-paper.json" >&2
  echo "  $REPO_DIR/midori-night.json" >&2
  exit 1
fi

echo
echo "Done. In Antinote: Settings -> Visuals -> Reload Custom Themes,"
echo "then pick 'Midori Paper' or 'Midori Night'."
