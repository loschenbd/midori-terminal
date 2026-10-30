#!/bin/sh
# Cheap syntax/lint guards for the parts that aren't unit-testable (shell
# scripts, the zsh/tmux fragments, the Python bakers) + the patcher unit tests.
# Local/macOS-oriented (the tmux fragment uses `defaults`); CI runs a portable
# subset (see .github/workflows/ci.yml). Run:  sh tests/lint.sh
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
FAIL=0
ok()   { printf '  ok   %s\n' "$*"; }
bad()  { printf '  FAIL %s\n' "$*"; FAIL=1; }

# DOT-DIRECTORIES ARE PRUNED, not just .git. obsidian/.fontenv is a virtualenv
# with ~2000 .py files in site-packages, and py_compiling third-party code we
# did not write turned a two-second lint into a several-minute one. Anything
# hidden is either vendored or machinery; neither is ours to check.
#
# MINDEPTH 1 IS LOAD-BEARING. Without it, `find .` visits `.` itself first,
# whose own basename is `.` -- which matches the `-name '.*'` glob -- so
# `-prune` pruned the repo root before find ever descended into it, and
# nothing below was traversed. This silently matched zero files from the day
# this helper was written until 2026-08-17: `FILES '*.py'` returned 0 files
# and `FILES '*.sh'` returned 0 files; with `-mindepth 1` they return 17 and
# 11. Every "python compiles" and "shell scripts" line below had been passing
# by checking nothing, and every task in this plan that cited "lint all
# green" as evidence was citing a check that had never run.
FILES() { find . -mindepth 1 -name '.*' -prune -o -name "$1" -print; }

# A LOOP OVER AN EMPTY SET LOOKS EXACTLY LIKE A LOOP WHERE EVERYTHING PASSED.
# That is the whole reason the bug above survived two days: zero iterations, no
# bad(), section green. Counting the set before walking it is what makes the
# next broken finder announce itself instead of going quiet, and the count is
# printed because a green run that cannot say HOW MANY things it checked is not
# evidence.
#
# THE CHECK RUNS IN THE PARENT SHELL, DELIBERATELY. Wrapping this in a helper
# called as `for f in $(found ...)` is the obvious shape and it is wrong twice:
# bad() writes to stdout, so its message would be captured and word-split into
# the loop as filenames; and `$( )` is a subshell, so the FAIL=1 it sets would
# be discarded and the run would still exit 0 -- the exact silent-pass this
# guard exists to prevent, reintroduced by the guard. Both were observed.
PY_FILES=$(FILES '*.py')
SH_FILES=$(FILES '*.sh')
count() { printf '%s\n' "$1" | wc -l | tr -d ' '; }

echo "== python compiles =="
if [ -z "$PY_FILES" ]; then
  bad "no .py files found at all -- FILES() is broken, not the repo"
else
  ok "$(count "$PY_FILES") python files to check"
  # ONE INTERPRETER, NOT ONE PER FILE. `python3 -m py_compile` in a loop pays
  # full interpreter startup per file: measured on this repo, 32s for 20 files
  # against 3s for shellcheck over 13. Batching them is the single biggest win
  # available in this script.
  #
  # The per-file ok/FAIL lines are kept deliberately. A green section that
  # cannot name what it checked is not evidence, and collapsing 20 lines into
  # "python ok" would trade a 30s saving for exactly the blindness the count
  # guard above exists to prevent. Python prints the lines; the shell reads
  # only the exit status, because bad() cannot be called from inside it.
  # shellcheck disable=SC2086
  if python3 - $PY_FILES <<'PYC'
import py_compile, sys
bad = 0
for f in sys.argv[1:]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  ok   py_compile {f}")
    except Exception as exc:
        print(f"  FAIL py_compile {f}: {exc.__class__.__name__}")
        bad = 1
sys.exit(bad)
PYC
  then :; else FAIL=1; fi
fi

echo "== shell scripts =="
if [ -z "$SH_FILES" ]; then
  bad "no .sh files found at all -- FILES() is broken, not the repo"
fi
for sh in $SH_FILES; do
  if command -v shellcheck >/dev/null 2>&1; then
    # -S error: fail only on real errors, not style nits in these hand-written scripts.
    if shellcheck -S error "$sh" >/dev/null 2>&1; then ok "shellcheck $sh"; else bad "shellcheck $sh"; fi
  else
    if sh -n "$sh" 2>/dev/null; then ok "sh -n $sh"; else bad "sh -n $sh"; fi
  fi
done

echo "== zsh fragment parses =="
if command -v zsh >/dev/null 2>&1; then
  if zsh -n shell/zshrc.midori 2>/dev/null; then ok "zsh -n shell/zshrc.midori"; else bad "zsh -n shell/zshrc.midori"; fi
else
  echo "  skip (zsh not found)"
fi

echo "== tmux fragment parses =="
if command -v tmux >/dev/null 2>&1; then
  if tmux -L midori-lint -f tmux/midori.tmux.conf start-server \; kill-server >/dev/null 2>&1; then
    ok "tmux parse tmux/midori.tmux.conf"
  else
    bad "tmux parse tmux/midori.tmux.conf"
  fi
else
  echo "  skip (tmux not found)"
fi

echo "== patcher unit tests =="
if python3 tests/test_patch_claude_binary.py; then :; else FAIL=1; fi

echo "== moshi themes are current =="
if python3 tests/test_moshi_themes.py; then :; else FAIL=1; fi

echo "== midori-timer unit tests =="
if command -v node >/dev/null 2>&1; then
  if node tests/test_midori_timer.js; then :; else FAIL=1; fi
  if node tests/test_caret_writes.js; then :; else FAIL=1; fi
else
  echo "  skip (node not found)"
fi

echo "== vivaldi ui mods resolve in both languages =="
# The mods reference ~47 custom properties and two palettes declare them. An
# undeclared custom property is not a CSS error -- the declaration is simply
# dropped and the surface renders in Vivaldi's own colour -- so a typo in one
# name is invisible until someone opens that pane in that mode. Sabotage-proved
# with 9 cases (scratchpad sab_viv.py): typo'd name, a variable missing from one
# mode only, an orphaned theme id, the specificity tie, a leaked Midori colour,
# a dangling scheduleOS id, an emptied mods dir, a declaration left inside a
# comment, and a reference no palette declares.
if python3 tests/test_vivaldi_css_vars.py; then :; else FAIL=1; fi

echo "== lemonardo vivaldi palette matches its generator =="
# lemonardo-palette.css is GENERATED, and every number in it is gated on
# derivation -- stack separation, label contrast, wash loudness against
# Midori's, and the active tab's material layer. Those gates only bind if the
# shipped file is the generator's output, so this re-runs the derivation and
# refuses a file that has drifted from it. Without this a hand edit sails
# through: tests/check_vivaldi_tab_material.py reads its alphas OUT of this
# file, so it would faithfully confirm that whatever is written there is what
# reaches the screen.
if python3 vivaldi/make-lemonardo-palette.py --check; then :; else FAIL=1; fi

echo "== palette has one definition =="
if python3 tests/test_palette_is_defined.py; then :; else FAIL=1; fi

echo "== prose typography =="
if python3 tests/test_prose_typography.py; then :; else FAIL=1; fi

# A BACKTICK INSIDE THE INJECTED STYLESHEET ENDS IT. Every plugin here injects
# its CSS as a template literal, and every one documents the CSS in prose above
# the rules — where it is natural to quote a selector or a property `like this`,
# which terminates the string and turns the rest of the file into syntax errors
# far from the cause. Hit three times in one session before this check existed.
# node --check does catch it, but only afterwards and pointing at the wrong
# line; this names the actual mistake.
echo "== no backticks inside injected stylesheets =="
if python3 tests/check_style_literals.py; then :; else FAIL=1; fi

echo "== block geometry =="
if python3 tests/test_block_geometry.py; then :; else FAIL=1; fi

echo "== obsidian plugins parse =="
if command -v node >/dev/null 2>&1; then
  for js in obsidian/plugins/*/main.js; do
    if node --check "$js" 2>/dev/null; then ok "node --check $js"; else bad "node --check $js"; fi
  done
else
  echo "  skip (node not found)"
fi

# PARSING IS NOT LOADING. A main.js truncated at a top-level boundary — by an
# edit that replaced a range and swallowed the rest of the file — is still
# valid JavaScript. It parses, the stylesheet check passes, and the only
# symptom is Obsidian saying "Failed to load plugin" with no line number.
# Happened once; this requires each plugin the way Obsidian does instead.
echo "== obsidian plugins load and export a Plugin =="
if command -v node >/dev/null 2>&1; then
  if node tests/check_plugin_loads.js; then :; else FAIL=1; fi
else
  echo "  skip (node not found)"
fi

# The t3 theme is GENERATED, and t3 validates it strictly on import -- an
# unknown role or a non-hex value throws by name. Catching that here means the
# failure lands at commit time rather than in a dialog inside someone's
# browser, and the --check half fails if the committed JSON was hand-edited
# away from the source that produced it.
echo "== t3 theme matches its source =="
if python3 t3/build-t3-theme.py --check; then :; else FAIL=1; fi

# THE PALETTE ROUND-TRIP, which for a long time did not run. tools/emit-theme.py
# documented a gate -- "emitting midori must reproduce the committed block byte
# for byte" -- that nothing ever invoked, because no target carried the sentinels
# and lint did not call it. Wiring it found the adapter dropped nine comment
# lines and carried a correction that had never shipped. The loop below fails on
# an EMPTY target list as well as on a mismatch: a round-trip over zero files is
# this repo's documented failure mode, not a pass.
echo "== theme palettes round-trip from themes/*.json =="
RT_PAIRS=$(python3 - <<'EOF'
import importlib.util
spec = importlib.util.spec_from_file_location("e", "tools/emit-theme.py")
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except SystemExit:
    pass
# Every pair a target DECLARES. A target that ships no file for a theme is not
# a gap here -- it declares nothing and nothing is checked. A target that
# declares a file which is missing or stale fails, by name.
for t in sorted(m.TARGETS):
    for th in sorted(m.TARGETS[t]["files"]):
        print(f"{t}:{th}")
EOF
)
RT_N=0
for pair in $RT_PAIRS; do
  t=${pair%%:*}; th=${pair##*:}
  if python3 tools/emit-theme.py --target "$t" --theme "$th" --check; then :; else FAIL=1; fi
  RT_N=$((RT_N + 1))
done
if [ "$RT_N" -eq 0 ]; then
  echo "  FAIL round-tripped 0 target/theme pairs -- the gate examined nothing"
  FAIL=1
else
  echo "  $RT_N target/theme pair(s) round-tripped"
fi

echo
echo "== colour arithmetic selftest =="
# Run FIRST among the colour checks in spirit, even though it prints here: if
# CIEDE2000 or the Oklab matrices are wrong, every distance and contrast number
# the Lemonardo gates print is confidently wrong in the same direction.
if python3 tools/colorspace.py; then :; else FAIL=1; fi

echo
echo "== lemonardo ansi matches its rules and clears its gates =="
if python3 tests/test_lemonardo_ansi.py; then :; else FAIL=1; fi

echo "== the two cursor shaders differ only in brand constants =="
if python3 tests/test_lemonardo_shader.py; then :; else FAIL=1; fi

echo "== every family a theme names is vendored in fonts/ =="
if python3 tests/test_fonts_are_vendored.py; then :; else FAIL=1; fi

echo "== lemonardo twins carry no midori-only colour =="
if python3 tests/test_lemonardo_twins.py; then :; else FAIL=1; fi

echo "== midori-theme switches every surface =="
# Runs midori-theme for real against a temp HOME, then reads the files back.
#
# ~72s MEASURED, and nearly all of it is process spawn, not work: the run uses
# 0.6s of CPU across 72s of wall clock. midori-theme forks on the order of 60
# commands per switch (cmp, cp, ln, id, dscl, awk, PlistBuddy, command -v) and
# this machine costs ~80ms a fork; `sh -x` with a timestamped PS4 shows no
# single gap over 0.2s, which is what rules out one slow call. So this roughly
# doubles lint. It earns it by being the only check of what gets WRITTEN —
# a dry run proves the decisions and nothing about the files, and the files
# are the job.
if python3 tests/test_midori_theme.py; then :; else FAIL=1; fi

echo "== install-herdr.sh reads the live config correctly =="
# The one installer whose destination the APPLICATION also writes: herdr
# prepends `onboarding = false` when its onboarding overlay is dismissed, and
# no language file has that line, so the `cmp -s` this script used to decide
# "already up to date" could never match. Every run took the conflict branch
# and said "matches neither language" while the config was in fact exactly
# ours. Runs against a sandboxed HOME with a `herdr` recorder on PATH, then
# proves the real ~/.config/herdr is byte-identical -- $HERDR_SOCKET_PATH is
# an absolute path to the live server's socket, so HOME alone is not a sandbox
# here either.
if python3 tests/test_herdr_install.py; then :; else FAIL=1; fi

echo "== claude code token maps =="
if python3 tests/test_claude_themes.py; then :; else FAIL=1; fi

echo "== the claude theme model still reproduces midori =="
# Not the same check as the one above. That one holds the four FILES to each
# other and to the frozen heredoc extraction; this one re-derives Midori from
# the rules in the generator and diffs the result, which is what catches a rule
# edited to suit Lemonardo at Midori's expense. The files would still agree.
if python3 tools/make-claude-theme.py --check; then :; else FAIL=1; fi

echo
[ "$FAIL" -eq 0 ] && echo "LINT: all green" || echo "LINT: failures above"
exit "$FAIL"
