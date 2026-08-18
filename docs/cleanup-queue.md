# Cleanup queue

**This file is the loop's only source of work.** One item per iteration, in
order. The loop MUST NOT add items here — `tests/check_cleanup_invariants.sh`
fails the run if it does. Anything new goes under FINDINGS FOR REVIEW at the
bottom, for a human to promote into the checklist later.

Why that rule exists: a loop that writes its own work list re-decides what
"cleanup" means every iteration. Iteration 1 renames for clarity, iteration 6
renames back, and both felt correct at the time. That is drift being
manufactured by the thing hired to remove it.

## How to do an item

1. Read the item and `CLAUDE.md`. The item is the whole scope — do not widen it.
2. Make the change. Prefer the smallest edit that fully does the item.
3. `sh tests/lint.sh` — must be green, and must report a non-zero file count.
4. If an installer changed: `sh tests/dryrun-installers.sh`, and paste its
   `DRYRUN-OK:` line into the commit message.
5. Commit, one commit per item, message explaining *why* not *what*.
6. `sh tests/check_cleanup_invariants.sh <BASE>` — must be green.
7. Tick the box here and commit that tick with the work.
8. If the item turns out to be wrong or unsafe, DO NOT do it. Tick it as
   `- [~]` and write one line under it saying why. A rejected item is a
   successful iteration.

---

## Queue

- [ ] **Shared shell helpers across the installers.** `set -e`, `REPO_DIR=`
      resolution, and running-app detection (`pgrep -x`) are repeated in all
      seven scripts. Extract to `lib/sh-common.sh`, sourced by each.
      DO NOT merge the installers themselves — `install.sh` is already an
      orchestrator that dispatches to per-target scripts, and each target's
      caveats are load-bearing. Only the boilerplate moves.

- [ ] **The JSON-patch heredoc is written three times** in
      `obsidian/install-obsidian.sh` (appearance.json, community-plugins.json)
      and once in `vivaldi/install-vivaldi.sh`. Extract one `patch_json`
      helper. Keep each call site's comment explaining *why that file* is
      patched — those differ and are not duplication.

- [ ] **`tests/lint.sh` takes ~60s, and most of it is per-file `py_compile`
      subprocesses.** Batch them into one interpreter invocation. Keep the
      count-and-fail-on-empty guard exactly as it is; that is not overhead.

- [ ] **Verify every numeric claim in `README.md` against the code.** One pass,
      listing each claim and whether it still holds. Two prior sweeps found
      five false claims and one inverted ratio. Correct what is wrong; where a
      claim is unverifiable, say so rather than deleting it.

- [ ] **Verify every numeric claim in `obsidian/theme.css` comments.** Same
      method. Do not delete comments — correct them, and when correcting, say
      what was wrong and why it was believed.

- [ ] **Guards without a sabotage proof.** For each test in
      `tests/test_prose_typography.py`, check whether a sabotage proof is
      recorded in its docstring. List the ones that lack one. Do not
      write the proofs in this pass — just produce the list.

- [ ] **`obsidian/plugins/midori-timer/main.js` is 2,119 lines.** Identify
      natural seams (parsing, formatting, caret colour, settings) and report
      whether a split is worth it. Report only; do not split in this pass.

- [ ] **Dead files.** Find tracked files referenced by nothing — no import, no
      script, no doc link. Each candidate must ship with the grep that proves
      it. Report only; delete nothing in this pass.

---

## FINDINGS FOR REVIEW

The loop appends here. These are NOT work items until a human moves them up.

<!-- loop appends below this line -->
