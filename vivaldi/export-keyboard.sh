#!/bin/sh
# Re-export the canonical keyboard shortcuts from a Vivaldi profile into
# vivaldi/keyboard.json. Run this after tweaking hotkeys in Vivaldi's UI so the
# repo stays the single source of truth (install-vivaldi.sh writes it back out).
#
# Usage:
#   ./export-keyboard.sh                        # from the Default profile
#   ./export-keyboard.sh --profile "Artisan Studios"
#   ./export-keyboard.sh --profile Default
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VIVALDI_DIR="$HOME/Library/Application Support/Vivaldi"

PROFILE_SEL="Default"
case "${1:-}" in
  --profile) PROFILE_SEL="${2:-Default}" ;;
  --profile=*) PROFILE_SEL="${1#*=}" ;;
  "") : ;;
  *) PROFILE_SEL="$1" ;;
esac

REPO_DIR="$REPO_DIR" VIVALDI_DIR="$VIVALDI_DIR" PROFILE_SEL="$PROFILE_SEL" python3 - <<'EOF'
import json, os, sys, collections

repo = os.environ["REPO_DIR"]
vdir = os.environ["VIVALDI_DIR"]
sel = os.environ["PROFILE_SEL"].strip()

try:
    info = json.load(open(os.path.join(vdir, "Local State"))) \
             .get("profile", {}).get("info_cache", {})
except (FileNotFoundError, json.JSONDecodeError):
    info = {}

# resolve sel -> profile dir (exact dir name, or case-insensitive display name)
d = None
if os.path.exists(os.path.join(vdir, sel, "Preferences")):
    d = sel
else:
    for k, v in info.items():
        if v.get("name", "").lower() == sel.lower():
            d = k
            break
if not d:
    sys.exit(f"Profile {sel!r} not found.")

v = json.load(open(os.path.join(vdir, d, "Preferences"))).get("vivaldi", {})
if not v.get("actions"):
    sys.exit(f"Profile {sel!r} has no custom keyboard shortcuts to export.")

actions = [collections.OrderedDict(sorted(v["actions"][0].items()))]
out = {"actions": actions, "keyboard": v.get("keyboard", {})}
dst = os.path.join(repo, "keyboard.json")
json.dump(out, open(dst, "w"), indent=2)
open(dst, "a").write("\n")

bound = sum(1 for a in actions[0].values() if a.get("shortcuts"))
print(f"Exported {len(actions[0])} commands ({bound} bound) from "
      f"{info.get(d, {}).get('name', d)} -> vivaldi/keyboard.json")
EOF
