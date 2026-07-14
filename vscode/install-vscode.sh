#!/bin/sh
# Install the Midori Paper / Midori Night theme extension into Cursor and
# VS Code. Symlinking into ~/.cursor/extensions does NOT work — Cursor and
# modern VS Code only load extensions registered in extensions.json, so the
# extension must go through `--install-extension` with a packaged .vsix.
#
# After running: reload the editor, then either pick the theme directly
# (Cmd+K Cmd+T) or let it follow macOS appearance via:
#   "window.autoDetectColorScheme": true,
#   "workbench.preferredLightColorTheme": "Midori Paper",
#   "workbench.preferredDarkColorTheme": "Midori Night"
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VSIX="$REPO_DIR/midori-theme.vsix"

echo "Packaging midori-theme.vsix..."
(cd "$REPO_DIR/midori-theme" && \
  npx -y @vscode/vsce package --allow-missing-repository --skip-license -o "$VSIX")

installed=0

# Careful: /usr/local/bin/code is often Cursor's shim, so resolve the real
# app binaries directly instead of trusting whatever is on PATH.
CURSOR_BIN="/Applications/Cursor.app/Contents/Resources/app/bin/code"
VSCODE_BIN="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"

if [ -x "$CURSOR_BIN" ]; then
  "$CURSOR_BIN" --install-extension "$VSIX" --force
  echo "Installed into Cursor"
  installed=1
fi

if [ -x "$VSCODE_BIN" ]; then
  "$VSCODE_BIN" --install-extension "$VSIX" --force
  echo "Installed into VS Code"
  installed=1
fi

if [ "$installed" -eq 0 ]; then
  echo "Neither Cursor nor VS Code found in /Applications." >&2
  exit 1
fi

echo "Done. Reload the editor(s), then pick Midori Paper / Midori Night."
