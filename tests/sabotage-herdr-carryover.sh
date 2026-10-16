#!/bin/sh
# Sabotage-proof the herdr carry-over cases in tests/test_midori_theme.py.
#
# A passing check is evidence only if you know what it examined. Those cases
# went green the first time they ran, which is exactly the shape this repo has
# been bitten by: tests/lint.sh traversed zero files for two days while every
# task cited "lint all green", and a guard test passed while the rule it named
# had lost a specificity contest. So before trusting them, break what each one
# watches and require the suite to FAIL while NAMING the break.
#
#   sh tests/sabotage-herdr-carryover.sh [case]
#
# case is one of: drop carry-all append cmp truncate silent
#                 (default: all)
#
# WHAT IT TOUCHES. A COPY of tools/midori-theme under its own work directory,
# never the real one; tests/test_midori_theme.py takes $MIDORI_THEME for
# exactly this. The real script's checksum is re-asserted after every case,
# because "it only edits a copy" is a claim and not a fact -- the Vivaldi
# sabotage harness next door made that claim while writing into a symlink that
# led straight back to what the live browser loads.
#
# THE SUITE SANDBOXES ITS OWN HOME, so nothing here reaches the live herdr
# config, the live Ghostty config or launchd. The one thing worth knowing:
# $HERDR_SOCKET_PATH is an ABSOLUTE path to the live herdr server's socket and
# ignores HOME completely, which is the "what does this name absolutely"
# question CLAUDE.md insists on. The suite answers it the plain way -- PATH is
# stripped, so the herdr binary is simply absent and `herdr server
# reload-config` is never reached.
#
# IT IS SLOW: each case re-runs the whole 22-case suite, which is ~3 minutes,
# so a full run is ~20. That is why it is not in lint. The cheap half of the
# same ground -- that the script and the generated files agree -- is what lint
# carries.

set -eu

CASE="${1:-all}"
REPO=$(cd "$(dirname "$0")/.." && pwd)
REAL="$REPO/tools/midori-theme"
SUITE="$REPO/tests/test_midori_theme.py"
WORK="${TMPDIR:-/tmp}/midori-herdr-sabotage.$$"
TOOL="$WORK/midori-theme"

mkdir -p "$WORK"
REAL_SHA=$(shasum -a 256 "$REAL" | cut -d' ' -f1)

# Put the copy back, and re-assert that the ORIGINAL never moved. The second
# half is the part that matters.
restore() {
	cp "$REAL" "$TOOL"
	now=$(shasum -a 256 "$REAL" | cut -d' ' -f1)
	[ "$now" = "$REAL_SHA" ] || {
		echo "STOP: $REAL changed during this run ($now, was $REAL_SHA)." >&2
		echo "This harness is meant to touch only $TOOL." >&2
		exit 1
	}
}
cleanup() { restore; rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

PASS=0
HOLES=0

# grade <label> <pattern the failure must name>
# Requires BOTH a non-zero exit AND output naming what was broken. An exit code
# alone is not enough: a suite that dies for an unrelated reason -- a syntax
# error in the sabotage, a missing file, a crash -- is indistinguishable from
# one that caught the sabotage, and that is how a sabotage harness ends up
# certifying a guard that does nothing.
grade() {
	label=$1
	want=$2
	out=$(MIDORI_THEME="$TOOL" python3 "$SUITE" 2>&1) && rc=0 || rc=$?
	if [ "$rc" -eq 0 ]; then
		echo "  HOLE  $label: the suite PASSED a sabotaged script"
		HOLES=$((HOLES + 1))
	elif printf '%s' "$out" | grep -qi -- "$want"; then
		echo "  ok    $label"
		printf '%s\n' "$out" | grep -i -- "$want" | head -2 | sed 's/^/          /'
		PASS=$((PASS + 1))
	else
		echo "  WEAK  $label: the suite failed, but never named /$want/"
		printf '%s\n' "$out" | grep -i "FAIL" | head -4 | sed 's/^/          /'
		HOLES=$((HOLES + 1))
	fi
}

run_case() {
	restore
	case $1 in
	drop)
		# Carry nothing: the ownership test never fires, which is behaviourally
		# the `cp -f config.<lang>.toml config.toml` this fix replaced.
		sed -i '' 's|if (!(a\[1\] in own)) print }|if (0) print }|' "$TOOL"
		grade "nothing is carried, as the old plain cp did" "appears 0x"
		;;
	carry-all)
		# Carry everything, ownership ignored. The interesting failure is not
		# "too much was kept" but INVALID TOML: a key the language file also
		# declares ends up at the top level twice, and herdr falls back to its
		# built-in defaults -- an unthemed herdr with no error on screen.
		sed -i '' 's|if (!(a\[1\] in own)) print }|if (1) print }|' "$TOOL"
		grade "a key the language file claims is carried too (duplicate key)" \
			"ALSO carried"
		;;
	append)
		# Appended instead of prepended. Still valid TOML and still parses --
		# which is the trap: the key is now filed under the LAST table, so it
		# is read as ui.toast.onboarding and the top-level setting is simply
		# absent. herdr/README.md records this costing a debugging round.
		python3 - "$TOOL" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text()
old = """    { printf '%s\\n' "$_keep"; cat "$_lang"; } > "$_new" ||"""
new = """    { cat "$_lang"; printf '%s\\n' "$_keep"; } > "$_new" ||"""
assert t.count(old) == 1, f"compose prepend not found ({t.count(old)}x)"
p.write_text(t.replace(old, new))
PY
		grade "carried keys appended, so TOML files them under the last table" \
			"not above the first table header"
		;;
	cmp)
		# The identity check reverted to what it was: a byte comparison against
		# a file herdr has since written into, which can only ever answer no.
		python3 - "$TOOL" <<'PY'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text()
new = re.sub(r"herdr_is\(\) \{.*?\n\}\n",
             'herdr_is() {\n  cmp -s "$1" "$2"\n}\n', t, count=1, flags=re.S)
assert new != t, "herdr_is not found"
p.write_text(new)
PY
		grade "identity by cmp again, so no language ever matches" \
			"cannot name herdr's language"
		;;
	truncate)
		# A compose that writes a short file, with the shape check removed so
		# it lands. This is the failure the write-then-move dance exists for,
		# and the one that is invisible in use: herdr starts fine on a
		# truncated config, just unthemed.
		sed -i '' 's|cat "$_lang"|head -5 "$_lang"|g' "$TOOL"
		sed -i '' 's|if \[ ! -s "$_new" \] \|\| \[ "$_got" -ne "$_want" \]; then|if false; then|' "$TOOL"
		grade "a truncated config lands because the shape check is gone" \
			"byte for byte"
		;;
	silent)
		# The refusal stops announcing itself. The live config is still intact,
		# so every file-level assertion passes -- and a switch that quietly did
		# nothing reads exactly like one that worked, with a reload line
		# printed under it for good measure.
		sed -i '' '/say "!! composing config.toml did not produce the expected shape/d' "$TOOL"
		sed -i '' '/say "   left the live herdr config alone"/d' "$TOOL"
		grade "the refusal is silent" "without saying so"
		;;
	*)
		echo "unknown case $1" >&2
		exit 2
		;;
	esac
}

echo "sabotaging a COPY at $TOOL"
echo "the real script ($REAL_SHA) is checksum-verified after every case"
echo

if [ "$CASE" = all ]; then
	set -- drop carry-all append cmp truncate silent
else
	set -- "$CASE"
fi
for c in "$@"; do run_case "$c"; done

restore
echo
echo "sabotage: $PASS held, $HOLES hole(s)"
[ "$HOLES" -eq 0 ] || exit 1
