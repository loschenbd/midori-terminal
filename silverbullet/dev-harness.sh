#!/bin/sh
# Stand up a THROWAWAY SilverBullet and a throwaway browser, install
# silverbullet/midori.css into it, and leave both running for
# tests/check_rendered_silverbullet.py.
#
# Nothing here touches a real space, a real data folder, a real browser profile
# or any ~/Projects directory. The space it serves is a staged sample page
# written fresh every run. That is not politeness: a SilverBullet space IS a
# project folder, so a harness that installed the theme "where you already run
# it" would be writing a markdown page into a live repo.
#
#   sh silverbullet/dev-harness.sh /path/to/silverbullet
#
# POSIX sh. Needs: a silverbullet binary (passed in, or $SB_BIN), Vivaldi or
# another Chromium at $BROWSER_BIN, python3, and websocket-client in $VENV.

set -eu

SB_BIN="${1:-${SB_BIN:-}}"
PORT="${PORT:-3099}"
CDP_PORT="${CDP_PORT:-9333}"
BROWSER_BIN="${BROWSER_BIN:-/Applications/Vivaldi.app/Contents/MacOS/Vivaldi}"
WORK="${WORK:-${TMPDIR:-/tmp}/midori-sb-harness}"
HERE=$(cd "$(dirname "$0")" && pwd)

[ -n "$SB_BIN" ] && [ -x "$SB_BIN" ] || {
	echo "usage: sh silverbullet/dev-harness.sh /path/to/silverbullet" >&2
	echo "  (or set SB_BIN). The binary is not vendored here." >&2
	exit 2
}
[ -x "$BROWSER_BIN" ] || {
	echo "dev-harness.sh: no Chromium at $BROWSER_BIN (set BROWSER_BIN)" >&2
	exit 2
}

echo "harness root: $WORK"

# --- stop anything from a previous run ---------------------------------------
# WIPE THE BROWSER PROFILE, EVERY RUN, NOT JUST THE DATA FOLDER.
# SilverBullet's page index and file cache live in the browser's IndexedDB, per
# space. A page the client once saw as zero bytes STAYS zero bytes in that
# cache: the server's own listing reported 28522 bytes for the stylesheet page
# while the client's allPages entry still said size 0, so the space-style query
# returned nothing and the theme simply was not installed -- and "Space:
# Reindex" did not repair it. Restarting the server is not enough, and neither
# is reloading the tab. The profile goes.
for p in $(lsof -ti "tcp:$PORT" 2>/dev/null || true); do kill "$p" 2>/dev/null || true; done
for p in $(lsof -ti "tcp:$CDP_PORT" 2>/dev/null || true); do kill "$p" 2>/dev/null || true; done
sleep 2
rm -rf "$WORK"
mkdir -p "$WORK/space" "$WORK/data"

# --- the staged sample page -------------------------------------------------
# Every construct the checker probes has to be ON this page, or its selector
# matches nothing and the probe fails (which is the intended behaviour -- a
# zero-match probe is never a pass). Staged content only: no project material.
cat > "$WORK/space/index.md" <<'SAMPLE'
---
title: Midori sample
tags: [sample, theme]
---
# Midori for SilverBullet

A sample page, staged for theme verification. **Bold ink**, *italic*,
~~struck through~~ and `inline code` in one paragraph, so the baseline can be
read across all four at once.

## Headings all carry one colour

### Third level

#### Fourth level

## Links and references

An external [link to a site](https://example.com), a naked URL
https://example.com, a wiki link [[Second Page]], a deliberately broken one
[[Nowhere At All]], a #tag and an @mention.

## Blockquote

> The stylesheet can be regenerated from understanding;
> the understanding cannot be regenerated from the stylesheet.
>
> > A nested quote, for the second bar.

## Tasks

* [ ] An open task
* [x] A finished task
* [ ] A task with a #label
    * [ ] A nested open task

## Lists

1. First ordered item
2. Second ordered item
   * A nested bullet
   * Another nested bullet

## Code

```javascript
// A comment, then a string, a number and an operator.
const paper = "#f3f1eb";
function tint(hex, amount = 0.5) {
  const n = parseInt(hex.slice(1), 16);
  return n * amount;
}
export default tint;
```

```python
# Python, for a second tokenizer
import json
PALETTE = {"sage": "#5f6f5e", "ochre": "#b88a3a"}
def load(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)
```

```lua
-- Space Lua
local greeting = "hello"
print(greeting .. " world", 42)
```

## Table

| Role  | Light     | Dark      |
|-------|-----------|-----------|
| paper | `#f3f1eb` | `#1a1917` |
| ink   | `#2a2825` | `#ebe8e2` |
| sage  | `#5f6f5e` | `#9aab97` |
| ochre | `#b88a3a` | `#d8b06a` |

---

## Admonitions

> **note** A note admonition.

> **warning** A warning admonition.

> **danger** A danger admonition.

> **success** A success admonition.
SAMPLE

cat > "$WORK/space/Second Page.md" <<'SAMPLE'
# Second Page

A second page, so the wiki link on the sample page resolves and the broken one
is distinguishable from it.
SAMPLE

# --- the theme, installed the documented way --------------------------------
sh "$HERE/wrap-midori.sh" --space-style > "$WORK/space/Midori Theme.md"
echo "installed theme page: $(wc -c < "$WORK/space/Midori Theme.md" | tr -d ' ') bytes"

# --- provision and serve ----------------------------------------------------
# access=write, so the harness needs no login. The enum is none|read|write --
# "full" is rejected at boot with "unknown variant", which is how I learnt it.
"$SB_BIN" setup --admin 'harness:harness' --space 'Midori' --at '/' \
	--space-folder "$WORK/space" "$WORK/data" >/dev/null
python3 - "$WORK/data/spaces.json" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
for v in d.values():
    v["access"] = "write"
json.dump(d, open(p, "w"), indent=2)
PY

"$SB_BIN" -L 127.0.0.1 -p "$PORT" "$WORK/data" > "$WORK/server.log" 2>&1 &
sleep 4
grep -q 'server running' "$WORK/server.log" || {
	echo "dev-harness.sh: server did not come up:" >&2
	tail -5 "$WORK/server.log" >&2
	exit 1
}
echo "server: http://127.0.0.1:$PORT  (log: $WORK/server.log)"

# Prove the server sees the whole stylesheet page. If this disagrees with the
# bytes reported above, stop here rather than grading a truncated theme.
served=$(curl -s "http://127.0.0.1:$PORT/.fs" | python3 -c 'import json,sys
print(next((f["size"] for f in json.load(sys.stdin) if f["name"]=="Midori Theme.md"), 0))')
echo "server reports Midori Theme.md: $served bytes"
[ "$served" -gt 1000 ] || {
	echo "dev-harness.sh: server reports $served bytes for the theme page" >&2
	exit 1
}

# --- browser, on a profile created seconds ago ------------------------------
"$BROWSER_BIN" --headless=new --remote-debugging-port="$CDP_PORT" \
	--user-data-dir="$WORK/profile" --no-first-run --no-default-browser-check \
	--disable-gpu > "$WORK/browser.log" 2>&1 &
sleep 5
curl -sf "http://127.0.0.1:$CDP_PORT/json/version" >/dev/null || {
	echo "dev-harness.sh: browser is not answering CDP on $CDP_PORT" >&2
	tail -5 "$WORK/browser.log" >&2
	exit 1
}
echo "browser: CDP on $CDP_PORT, fresh profile at $WORK/profile"
echo
echo "now run:  python3 tests/check_rendered_silverbullet.py http://127.0.0.1:$PORT/ --cdp $CDP_PORT"
