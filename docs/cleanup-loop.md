# Running the overnight cleanup loop

## Once, before the first night

```sh
git checkout -b cleanup-night-$(date +%Y%m%d)
git rev-parse HEAD > .cleanup-base      # gitignored; the gate needs it
```

`.cleanup-base` must point at a commit where `docs/cleanup-queue.md` already
exists with its items. If you seed the queue *after* this, the gate correctly
reports the loop as inventing work.

**Re-stamp it whenever you add queue items yourself.** The gate cannot tell
your edit from the loop's — it only sees `+- [ ]` lines appearing after BASE,
which is precisely the signal it exists to catch. So after editing the queue:

```sh
git rev-parse HEAD > .cleanup-base
```

Forgetting this is not dangerous; the loop simply refuses to proceed and tells
you which file gained items.

## Launch

```
/ralph-loop "Read docs/cleanup-queue.md and CLAUDE.md. Take the FIRST unchecked
item and do only that item. Follow the 8 steps in the queue's 'How to do an
item' section exactly, including running sh tests/lint.sh and
sh tests/check_cleanup_invariants.sh $(cat .cleanup-base) before committing.
Commit the work and the ticked box together, one commit. Then stop. Do not
start a second item. Do not add items to the queue. If the item is wrong or
unsafe, mark it [~] with one line saying why and stop -- that is a successful
iteration." --completion-promise "Every item in docs/cleanup-queue.md is
marked [x] or [~], and sh tests/check_cleanup_invariants.sh is green."
```

Ralph feeds the same prompt back each iteration; git history and the queue's
tick marks are the memory. One item per iteration is deliberate — it keeps
each commit reviewable and each failure to one item.

## Why the prompt is shaped this way

**"Take the FIRST unchecked item"** — not "find something to improve". A loop
that chooses its own work re-decides what cleanup means every iteration, and
you wake up to renames that were reverted by later renames.

**"Do only that item. Then stop."** — without this, a productive iteration
keeps going and produces one enormous commit. The 400-line cap in the gate
catches it, but after the work is done rather than before.

**"Do not add items to the queue"** — enforced by the gate, stated anyway.
Findings go under FINDINGS FOR REVIEW.

**"a rejected item is a successful iteration"** — otherwise the loop will do a
bad item rather than appear to fail. This is the single most important line
in the prompt.

**The completion promise is checkable.** "The repo is clean" is not, and a
loop cannot be trusted to evaluate it honestly at 4am.

## In the morning

```sh
BASE=$(cat .cleanup-base)
sh tests/check_cleanup_invariants.sh "$BASE"    # first: did it stay in bounds
git log --oneline "$BASE"..HEAD                 # one line per item
git diff --stat "$BASE"..HEAD
sed -n '/FINDINGS FOR REVIEW/,$p' docs/cleanup-queue.md
sh tests/lint.sh
```

Then review commit by commit and `git revert` or `git rebase -i` the ones you
don't want. That is why it is one commit per item.

Before merging, run the checks lint cannot:

```sh
sh tests/dryrun-installers.sh          # if any installer changed
open -a Obsidian --args --remote-debugging-port=9222
python3 tests/check_rendered_headings.py
python3 tests/check_rendered_grid.py
```

## What this cannot protect you from

The gate checks bounds, not correctness. It will not notice a CSS rule that
still exists but now loses a specificity contest, a comment corrected into a
different wrong claim, or a helper extraction that changes behaviour in a case
no test covers. Those need the rendered checks and your eyes.

Do not merge a night's work without reading it.
