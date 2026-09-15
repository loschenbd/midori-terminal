#!/bin/sh
# Install the Midori herdr config.
# This repo is the single source of truth; ~/.config/herdr/config.toml is an
# install target. Idempotent — re-run after edits.
#
# herdr has no theme *files*, so unlike Ghostty/Antinote there is nothing here
# but one config.toml. See README.md in this directory for why (short version:
# the theme list is fixed, so Midori rides on the built-in "terminal" theme plus
# per-appearance overrides — and those overrides only exist from herdr 0.9.0).
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="$HOME/.config/herdr"
DEST="$DEST_DIR/config.toml"
SRC="$REPO_DIR/config.toml"

if ! command -v herdr >/dev/null 2>&1; then
  echo "herdr not installed — skipping. (brew install herdr)"
  exit 0
fi

# The config needs 0.9.0: [theme.custom.light] / [theme.custom.dark] and the
# surface keys are new there. 0.8.x ignores them as unknown keys, and the
# "terminal" base then renders its ANSI 8 slab (README.md, "0.8.x"). Warn rather
# than refuse — this is still the right file to have in place for the upgrade.
herdr_version=$(herdr --version 2>/dev/null | awk '{print $2}')
case "$herdr_version" in
  0.[0-8].*)
    echo "!! herdr $herdr_version is older than 0.9.0; this config needs 0.9.0."
    echo "   brew upgrade herdr — then see herdr/README.md, \"Upgrading from 0.8.x\"."
    ;;
esac

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
  echo "   Merge the [theme] / [theme.custom*] blocks by hand: $DEST_DIR"
fi

# Validate whatever ended up at the destination, then hot-reload a running
# server so the change lands without detaching.
if herdr config check 2>&1 | grep -q '^config: ok'; then
  echo "config check: ok"
else
  echo "!! herdr config check reported issues:"
  herdr config check 2>&1 | sed 's/^/   /'
fi

# A failed reload does not mean no server is running: a 0.9.0 herdr cannot
# reach a server still running 0.8.x (different endpoint generation), and that
# is exactly the state right after `brew upgrade herdr`.
if herdr server reload-config >/dev/null 2>&1; then
  echo "Reloaded the running herdr server."
else
  echo "Could not reload a running herdr server (none running, or one older than"
  echo "this herdr) — the config applies the next time the server starts."
fi
