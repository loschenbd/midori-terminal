#!/bin/sh
# Sabotage-proof tests/check_rendered_silverbullet.py.
#
# A passing check is evidence only if you know what it examined. So before
# trusting this one, break the things it is supposed to be watching -- on
# SCRATCH COPIES of the stylesheet, never the real one -- and require the
# checker to fail while NAMING what was broken. A sabotage the checker sails
# through is a hole in the checker.
#
#   sh tests/sabotage-silverbullet.sh /path/to/silverbullet [case]
#
# case is one of: a b c d weight lines stale  (default: run them all)
#
# WHAT THIS TOUCHES. Only the throwaway harness: it kills whatever holds the
# harness ports, deletes and recreates $WORK, and writes scratch stylesheets
# under $WORK/sabotage. silverbullet/midori.css is read and never written. No
# real space, data folder, browser profile or ~/Projects path is involved.

set -eu

SB_BIN="${1:-${SB_BIN:-}}"
CASE="${2:-all}"
PORT="${PORT:-3099}"
CDP_PORT="${CDP_PORT:-9333}"
WORK="${WORK:-${TMPDIR:-/tmp}/midori-sb-harness}"
PY="${PY:-python3}"
REPO=$(cd "$(dirname "$0")/.." && pwd)
REAL="$REPO/silverbullet/midori.css"

[ -n "$SB_BIN" ] && [ -x "$SB_BIN" ] || {
	echo "usage: sh tests/sabotage-silverbullet.sh /path/to/silverbullet [case]" >&2
	exit 2
}

# OUTSIDE $WORK ON PURPOSE. dev-harness.sh does `rm -rf "$WORK"` every run, so
# a scratch stylesheet kept under $WORK is deleted before the harness reads it
# -- which it was, and the first run of this script reported that as a pass.
SAB="${SAB:-$WORK-sabotage}"
mkdir -p "$SAB"

# Run the harness with a given stylesheet, then the checker. Prints the
# verdict line and the first few named failures.
grade() {
	label=$1
	css=$2
	shift 2
	printf '\n=== %s\n' "$label"
	[ -s "$css" ] || {
		echo "  ABORT: scratch stylesheet $css is missing or empty."
		echo "  Nothing was graded. This is not a pass."
		return 1
	}
	if ! WORK="$WORK" CSS="$css" sh "$REPO/silverbullet/dev-harness.sh" \
		"$SB_BIN" > "$SAB/harness.log" 2>&1; then
		echo "  harness did not start; its last lines were:"
		sed 's/^/    /' "$SAB/harness.log" | tail -6
		echo "  Nothing was graded. A sabotage caught this early is only a pass"
		echo "  if the message names the sabotage -- read the lines above."
		return 1
	fi
	out=$("$PY" "$REPO/tests/check_rendered_silverbullet.py" \
		"http://127.0.0.1:$PORT/" --cdp "$CDP_PORT" 2>&1 || true)
	printf '%s\n' "$out" | grep -E '^(FAIL:|all green|[0-9]+ live assertion)' | sed 's/^/  /'
	printf '%s\n' "$out" | grep -E '^  - ' | head -6
	n=$(printf '%s\n' "$out" | grep -cE '^  - ' || true)
	echo "  named failures: $n"
}

# --- (a) the semantic block loses its dark-specificity branch ---------------
# The exact bug this stylesheet shipped once: collapse
#   html, html[data-theme="dark"] { ... }
# to a bare html, and every property SilverBullet redefines in its own dark
# block wins again. Light must stay perfect; dark must fail loudly.
case_a() {
	"$PY" - "$REAL" "$SAB/a-no-dark-branch.css" <<'PY'
import sys
src = open(sys.argv[1]).read()
needle = 'html,\nhtml[data-theme="dark"] {'
assert needle in src, "sabotage (a) could not find the semantic block opener"
open(sys.argv[2], "w").write(src.replace(needle, "html {", 1))
PY
	grade "(a) semantic block loses its html[data-theme] branch" "$SAB/a-no-dark-branch.css"
}

# --- (b) a palette value is wrong ------------------------------------------
# Repoint light sage at a flat grey. Everything sage in light mode must fail.
case_b() {
	"$PY" - "$REAL" "$SAB/b-wrong-sage.css" <<'PY'
import sys
src = open(sys.argv[1]).read()
needle = "  --midori-sage: #5f6f5e;"
assert needle in src, "sabotage (b) could not find the light sage declaration"
open(sys.argv[2], "w").write(src.replace(needle, "  --midori-sage: #808080;", 1))
PY
	grade "(b) light --midori-sage repointed to #808080" "$SAB/b-wrong-sage.css"
}

# --- (c) the admonition rules are deleted ----------------------------------
# These are the four colours SilverBullet keeps outside its token set. A theme
# that forgets them looks complete and leaves admonitions cyan.
case_c() {
	"$PY" - "$REAL" "$SAB/c-no-admonitions.css" <<'PY'
import re, sys
src = open(sys.argv[1]).read()
out = re.sub(r'\n\.sb-admonition\[admonition="[a-z]+" i\] \{[^}]*\}', "", src)
assert out != src, "sabotage (c) removed nothing"
open(sys.argv[2], "w").write(out)
PY
	grade "(c) admonition rules deleted" "$SAB/c-no-admonitions.css"
}

# --- (d) the stylesheet is truncated mid-file ------------------------------
# This is the triple-backtick failure, reproduced: a fence that ends early
# leaves a SHORTER but still VALID stylesheet, and the page renders fine.
# Cut just after the raw-token blocks, before the semantic mapping.
case_d() {
	"$PY" - "$REAL" "$SAB/d-truncated.css" <<'PY'
import sys
src = open(sys.argv[1]).read()
cut = src.index("html,\nhtml[data-theme=\"dark\"] {")
open(sys.argv[2], "w").write(src[:cut])
print(f"  truncated {len(src)} bytes to {cut}", file=sys.stderr)
PY
	grade "(d) stylesheet truncated before the semantic block" "$SAB/d-truncated.css"
}

# --- (weight) the heading weight rule loses its specificity contest --------
# The trap group 5 warns about, reproduced. Group 1 sets heading font-family
# with `#sb-main .cm-editor .sb-line-h1`, (1,2,0), and that works because the
# stock heading rule declares no font-family. The stock rule DOES declare
# font-weight, at `#sb-main .cm-editor .cm-line.sb-line-h1`, (1,3,0). Drop
# `.cm-line` from the weight rule and it reads exactly like the working one
# above it while changing nothing -- stock bold wins and the headings stay
# 700. This is the failure mode this repo has shipped before: "guard tests
# passed while the rule they named lost a specificity contest and did
# nothing." The h1/h2/h3 weight probes must name it.
case_weight() {
	"$PY" - "$REAL" "$SAB/weight-no-cm-line.css" <<'PY'
import re, sys
src = open(sys.argv[1]).read()
# Only inside the heading WEIGHT rule: the one whose selectors carry
# `.cm-line.sb-line-h` and whose body is font-weight: 600.
m = re.search(r'(#sb-main \.cm-editor \.cm-line\.sb-line-h1,.*?\{\s*font-weight: 600;\s*\})',
              src, re.S)
assert m, "sabotage (weight) could not find the heading weight rule"
broken = m.group(1).replace(".cm-line.sb-line-h", ".sb-line-h")
assert broken != m.group(1), "sabotage (weight) changed nothing"
open(sys.argv[2], "w").write(src.replace(m.group(1), broken, 1))
PY
	grade "(weight) heading weight rule drops .cm-line, dropping to (1,2,0)" \
		"$SAB/weight-no-cm-line.css"
}

# --- (lines) the checker's MIN_LINES floor ---------------------------------
# Install the REAL theme, then point the checker at a SHORT page. CodeMirror
# renders only what is in the viewport, so a probe into a fenced code block on
# a page that has none finds nothing; the floor has to refuse the run rather
# than report on the handful of lines it did get. (The checker forces a
# 1440x4200 viewport itself, which is why shrinking the window does not
# reproduce this -- it recovers. A thin DOCUMENT is the real case.)
case_lines() {
	printf '\n=== (lines) checker pointed at a 4-line page, real theme installed\n'
	if ! WORK="$WORK" sh "$REPO/silverbullet/dev-harness.sh" "$SB_BIN" \
		> "$SAB/harness.log" 2>&1; then
		sed 's/^/    /' "$SAB/harness.log" | tail -6
		return 1
	fi
	out=$("$PY" "$REPO/tests/check_rendered_silverbullet.py" \
		"http://127.0.0.1:$PORT/Second%20Page" --cdp "$CDP_PORT" 2>&1 || true)
	printf '%s\n' "$out" | grep -E '^(FAIL:|all green|  rendered cm-lines)' | sed 's/^/  /'
}

# --- (stale) the checker's own stale-target guard ---------------------------
# Open a SECOND page target and leave it there. The checker must refuse to
# grade rather than pick one, because picking is how it graded the previous
# client's stylesheet and reported a confident wrong answer.
case_stale() {
	printf '\n=== (stale) a second page target is left open\n'
	WORK="$WORK" sh "$REPO/silverbullet/dev-harness.sh" "$SB_BIN" >/dev/null 2>&1
	echo "  open_fresh() closes every target, opens one, then exits unless"
	echo "  exactly one remains. Leave extras open and watch it close them:"
	"$PY" - "$CDP_PORT" "$PORT" <<'PY'
import json, sys, time, urllib.request
cdp, port = sys.argv[1], sys.argv[2]
def targets():
    return [t for t in json.loads(urllib.request.urlopen(f"http://127.0.0.1:{cdp}/json").read())
            if t.get("type") == "page"]
for extra in range(2):
    urllib.request.urlopen(urllib.request.Request(
        f"http://127.0.0.1:{cdp}/json/new?http://127.0.0.1:{port}/", method="PUT")).read()
time.sleep(3)
print(f"  page targets now open: {len(targets())}")
PY
	out=$("$PY" "$REPO/tests/check_rendered_silverbullet.py" \
		"http://127.0.0.1:$PORT/" --cdp "$CDP_PORT" 2>&1 || true)
	printf '%s\n' "$out" | grep -E '^(FAIL:|all green|  closed)' | sed 's/^/  /'
}

case "$CASE" in
a) case_a ;;
b) case_b ;;
c) case_c ;;
d) case_d ;;
weight) case_weight ;;
lines) case_lines ;;
stale) case_stale ;;
all)
	case_a
	case_b
	case_c
	case_d
	case_weight
	case_lines
	case_stale
	;;
*)
	echo "unknown case: $CASE" >&2
	exit 2
	;;
esac

printf '\nsabotage copies left in %s for inspection\n' "$SAB"
printf 'the real stylesheet was never written: '
"$PY" -c "import hashlib,sys;print(hashlib.md5(open(sys.argv[1],'rb').read()).hexdigest())" "$REAL"
