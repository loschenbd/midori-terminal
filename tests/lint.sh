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
FILES() { find . -name '.*' -prune -o -name "$1" -print; }

echo "== python compiles =="
for py in $(FILES '*.py'); do
  if python3 -m py_compile "$py" 2>/dev/null; then ok "py_compile $py"; else bad "py_compile $py"; fi
done

echo "== shell scripts =="
for sh in $(FILES '*.sh'); do
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
if python3 tests/test_patch_claude_diffs.py; then :; else FAIL=1; fi

echo "== moshi themes are current =="
if python3 tests/test_moshi_themes.py; then :; else FAIL=1; fi

echo "== midori-timer unit tests =="
if command -v node >/dev/null 2>&1; then
  if node tests/test_midori_timer.js; then :; else FAIL=1; fi
  if node tests/test_caret_writes.js; then :; else FAIL=1; fi
else
  echo "  skip (node not found)"
fi

# A BACKTICK INSIDE THE INJECTED STYLESHEET ENDS IT. Every plugin here injects
# its CSS as a template literal, and every one documents the CSS in prose above
# the rules — where it is natural to quote a selector or a property `like this`,
# which terminates the string and turns the rest of the file into syntax errors
# far from the cause. Hit three times in one session before this check existed.
# node --check does catch it, but only afterwards and pointing at the wrong
# line; this names the actual mistake.
echo "== no backticks inside injected stylesheets =="
if python3 tests/check_style_literals.py; then :; else FAIL=1; fi

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

echo
[ "$FAIL" -eq 0 ] && echo "LINT: all green" || echo "LINT: failures above"
exit "$FAIL"
