#!/bin/sh
# Write marktext/midori.css into MarkText's `customCss` preference.
#
# MarkText 0.20.0 has no user theme directory -- the "Import Theme" rows in
# Preferences are rendered under v-show="false" and the theme ids are a frozen
# array inside app.asar. The Custom CSS box is the whole supported surface, so
# this is just "paste the file into that box", done from a shell.
#
# MARKTEXT MUST BE QUIT. preferences.json is owned by electron-store, which
# rewrites the whole file on every preference change. An edit made underneath a
# running app is a race you lose quietly: the app's in-memory copy wins on the
# next write and the CSS is gone with no error anywhere. Refused rather than
# attempted.
#
# POSIX sh. Needs python3 for the JSON edit (jq would also do; python3 is
# already a hard dependency of this repo's tests).
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
CSS="$ROOT/marktext/midori.css"
PREFS="$HOME/Library/Application Support/marktext/preferences.json"

[ -f "$CSS" ] || { echo "missing $CSS" >&2; exit 1; }

if pgrep -x MarkText >/dev/null 2>&1; then
  echo "MarkText is running. Quit it first (Cmd-Q) -- it rewrites" >&2
  echo "preferences.json on every change and would discard this edit." >&2
  exit 1
fi

if [ ! -f "$PREFS" ]; then
  echo "no preferences.json at:" >&2
  echo "  $PREFS" >&2
  echo "Launch MarkText once so it writes its defaults, then quit and re-run." >&2
  exit 1
fi

STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="$PREFS.midori-$STAMP.bak"
cp "$PREFS" "$BACKUP"

python3 - "$PREFS" "$CSS" <<'PY'
import json, sys

prefs_path, css_path = sys.argv[1], sys.argv[2]
css = open(css_path, encoding="utf-8").read()
with open(prefs_path, encoding="utf-8") as fh:
    prefs = json.load(fh)

before = prefs.get("customCss", "")
prefs["customCss"] = css

# Pair with the two Cadmium themes. Cadmium Light injects nothing but a
# two-variable patch, so the paper values sit straight on the compiled base;
# Cadmium Dark is what puts `dark` on <body>, which is this stylesheet's mode
# marker. Any other pairing works, but a theme with its own !important chrome
# rules (Graphite, One Dark) will out-rank parts of this file.
prefs["followSystemTheme"] = True
prefs["lightModeTheme"] = "light"
prefs["darkModeTheme"] = "dark"

with open(prefs_path, "w", encoding="utf-8") as fh:
    json.dump(prefs, fh, indent="\t")

print(f"  customCss: {len(before)} -> {len(css)} bytes")
print("  followSystemTheme: true, light=Cadmium Light, dark=Cadmium Dark")
PY

echo "  backup: $BACKUP"
echo "Done. Start MarkText."
