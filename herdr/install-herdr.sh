#!/bin/sh
# Install the Midori herdr config.
# This repo is the single source of truth; ~/.config/herdr/config.toml is an
# install target. Idempotent — re-run after edits.
#
# herdr has no theme *files*, so unlike Ghostty/Antinote there is nothing here
# but one config.toml. See README.md in this directory for why (short version:
# the theme list is fixed and an unknown name silently renders Catppuccin).
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="$HOME/.config/herdr"
DEST="$DEST_DIR/config.toml"
SRC="$REPO_DIR/config.toml"

if ! command -v herdr >/dev/null 2>&1; then
  echo "herdr not installed — skipping. (brew install herdr)"
  exit 0
fi

mkdir -p "$DEST_DIR"

# Same policy as the Ghostty config in install.sh: never clobber a config the
# user has edited. herdr's config carries keybindings and per-host settings
# that are none of this repo's business.
if [ ! -f "$DEST" ]; then
  cp -f "$SRC" "$DEST"
  echo "Installed ${DEST#"$HOME"/}"
elif cmp -s "$SRC" "$DEST"; then
  echo "${DEST#"$HOME"/} already up to date"
else
  cp -f "$SRC" "$DEST_DIR/config.midori.toml"
  echo "!! Existing herdr config differs — wrote config.midori.toml next to it."
  echo "   Merge the [theme] / [theme.custom] blocks by hand: $DEST_DIR"
fi

# Validate whatever ended up at the destination, then hot-reload a running
# server so the change lands without detaching.
if herdr config check 2>&1 | grep -q '^config: ok'; then
  echo "config check: ok"
else
  echo "!! herdr config check reported issues:"
  herdr config check 2>&1 | sed 's/^/   /'
fi

if herdr server reload-config >/dev/null 2>&1; then
  echo "Reloaded the running herdr server."
else
  echo "No herdr server running — the config applies on next launch."
fi
