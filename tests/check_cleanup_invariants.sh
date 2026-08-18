#!/bin/sh
# The gate an unattended cleanup loop must pass before each commit.
#
# WHY A SEPARATE GATE AND NOT JUST lint.sh. Lint answers "does it still work".
# These answer "is this still the same repo" -- the questions that only matter
# when nobody is watching the diff. An overnight loop optimising for
# "readable, organised, less redundant" has every incentive to delete the
# 2093 lines of comments that are this project's actual deliverable, and
# lint.sh would stay green the whole way down.
#
# Usage:  sh tests/check_cleanup_invariants.sh <BASE_REF>
# BASE_REF is what the night started from (e.g. the branch point).
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
BASE="${1:?usage: check_cleanup_invariants.sh <BASE_REF>}"
FAIL=0
ok()  { printf '  ok   %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*"; FAIL=1; }

# Count comment lines in a CSS/JS file at a given ref. Reads from git, not the
# worktree, so this measures what is COMMITTED rather than what is staged --
# the loop commits per item, and an uncommitted edit is not yet a loss.
comment_lines() {
  git show "$1:$2" 2>/dev/null | python3 -c '
import re, sys
s = sys.stdin.read()
print(sum(c.count(chr(10)) + 1 for c in re.findall(r"/\*.*?\*/", s, flags=re.S)))
' 2>/dev/null || echo 0
}

# A KILLED ITERATION LOOKS EXACTLY LIKE A FINISHED ONE TO EVERY CHECK BELOW.
# All of them read from git, which is correct -- an uncommitted edit is not yet
# a loss of comments and not yet an oversized commit. But it means a loop that
# died mid-item (rate limit, crash, laptop asleep) leaves half an edit in the
# worktree and this gate reports all green over the top of it. Worse, the next
# iteration then starts its item on top of the wreckage and commits both.
# Runs FIRST because every verdict after it is conditional on it.
echo "== the working tree is clean =="
if [ -n "$(git status --porcelain)" ]; then
  bad "uncommitted or untracked changes present -- an iteration was interrupted,
       or one failed to commit. Everything below reads from git and cannot see
       this. Inspect, then either finish the item or restore the files before
       resuming. DO NOT start the next item on top of it:"
  git status --short | sed 's/^/       /'
else
  ok "nothing uncommitted or untracked"
fi

echo "== the design record survives =="
# ONE ESCAPE HATCH, AND IT HAS TO BE ARGUED FOR. A comment can be legitimately
# removed -- when it is false, or when the code it describes is gone. That is a
# real edit and it needs a sentence, so it is spelled in the commit message
# rather than inferred from the diff.
for f in obsidian/theme.css obsidian/plugins/midori-timer/main.js; do
  before=$(comment_lines "$BASE" "$f")
  after=$(comment_lines HEAD "$f")
  if [ "$before" -eq 0 ]; then
    bad "could not read $f at $BASE -- the gate is broken, not the repo"
    continue
  fi
  lost=$((before - after))
  if [ "$lost" -le 0 ]; then
    ok "$f: $after comment lines (was $before)"
  elif git log "$BASE"..HEAD --format=%B | grep -q "ALLOW-COMMENT-LOSS:"; then
    ok "$f: -$lost comment lines, justified in a commit message"
  else
    bad "$f lost $lost comment lines ($before -> $after) with no
       ALLOW-COMMENT-LOSS: <reason> line in any commit message since $BASE.
       These comments are the design record; see CLAUDE.md."
  fi
done

echo "== each commit is reviewable on its own =="
# A NIGHT THAT PRODUCES ONE 4000-LINE COMMIT IS A NIGHT WASTED: it cannot be
# cherry-picked, reverted in part, or read over coffee. The cap is per commit,
# not per night, so a long productive run is fine and a single sprawling one
# is not.
CAP=400
n=0
for sha in $(git rev-list "$BASE"..HEAD); do
  n=$((n + 1))
  changed=$(git show --stat --format= "$sha" | tail -1 | grep -oE '[0-9]+ insertion|[0-9]+ deletion' | grep -oE '[0-9]+' | paste -sd+ - | bc 2>/dev/null || echo 0)
  [ -z "$changed" ] && changed=0
  if [ "$changed" -gt "$CAP" ]; then
    bad "$(git log -1 --format=%h\ %s "$sha") touches $changed lines (cap $CAP)"
  fi
done
[ "$n" -eq 0 ] && bad "no commits since $BASE -- nothing to check, which is not
       the same as everything passing" || ok "$n commit(s) since $BASE, each within $CAP lines"

echo "== the queue was consumed, not invented =="
# THE LOOP MUST NOT WRITE ITS OWN WORK LIST. That is how a cleanup loop drifts:
# iteration 1 renames for clarity, iteration 6 renames back, and both felt
# correct at the time. New findings go in a FINDINGS section for the morning,
# never into the checklist the loop is consuming.
Q=docs/cleanup-queue.md
if [ ! -f "$Q" ]; then
  bad "$Q is missing -- the loop has no queue and will invent one"
else
  added=$(git diff "$BASE"..HEAD -- "$Q" | grep -c '^+- \[ \]' || true)
  if [ "${added:-0}" -gt 0 ]; then
    bad "$added new unchecked item(s) added to $Q since $BASE -- the loop is
       writing its own work list. Findings belong under FINDINGS FOR REVIEW."
  else
    # grep -c PRINTS 0 and EXITS 1 when nothing matches, so `|| echo 0`
    # emitted a SECOND zero and the count read "0\n0", splitting the
    # ok line across two lines. `|| true` absorbs the status only.
    done_n=$(grep -c '^- \[x\]' "$Q" 2>/dev/null || true)
    left_n=$(grep -c '^- \[ \]' "$Q" 2>/dev/null || true)
    ok "queue: $done_n done, $left_n remaining, 0 items invented"
  fi
fi

echo "== installers were never run for real =="
# The dry-run harness proves the real vaults are untouched. This proves the
# loop did not skip it: a change to any installer must be accompanied by a
# dry-run receipt in the commit message.
if git diff --name-only "$BASE"..HEAD | grep -qE '(^|/)install[^/]*\.sh$|^sync\.sh$'; then
  if git log "$BASE"..HEAD --format=%B | grep -q "DRYRUN-OK:"; then
    ok "installer changed, and a DRYRUN-OK: receipt is present"
  else
    bad "an installer changed with no DRYRUN-OK: line in any commit message.
       Run sh tests/dryrun-installers.sh and paste its receipt."
  fi
else
  ok "no installer touched"
fi

echo
[ "$FAIL" -eq 0 ] && echo "INVARIANTS: all green" || echo "INVARIANTS: failures above"
exit "$FAIL"
