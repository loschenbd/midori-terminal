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

### Theme and style consolidation

Measured 2026-08-17. Re-derive any number here with
`python3 tests/measure_palette_drift.py` — do not trust these figures because they are
written down.

- **301 distinct hex values across 77 files. 43 of them appear in 4+ files** —
  the de-facto shared palette — and there is **no canonical definition of it
  anywhere in the repo.** Sage `#5f6f5e` is hand-copied into 18 files across
  seven areas; paper `#f3f1eb` into 18; slate `#3a5572` into 19. Changing one
  accent today means editing up to nineteen files correctly, with nothing to
  catch the one you miss.
- **40 near-miss values** sit within 8/255 per channel of a core colour without
  equalling it. **Nine are within 3/255**, which is below what anyone can see —
  so those are drift or typos, not design.
- `obsidian/theme.css` itself is NOT the problem and should not be
  restructured: 3 selectors appear 3+ times (`body` x20, which is token
  scoping), and the only declaration blocks shared by 3+ selectors are
  `line-height: var(--midori-row)` and friends, i.e. the grid discipline
  working. The duplication is BETWEEN targets, not inside the stylesheet.

- [x] **Give the palette one definition.** Create `palette.json` holding the 43
      shared values, each with the role name it already carries in comments
      (`--accent-warm`, ANSI slot, etc.). Then write a guard test that every
      hex appearing in 4+ files is present in `palette.json`, and fail on any
      that is not. **Do not regenerate any theme file from it in this pass** —
      the source of truth plus the drift detector is the whole item. Generation
      is a separate, later decision.

- [~] **Resolve the nine sub-visible values.** REJECTED — These are within 3/255 of a core
      colour, which no one can see, so each is a typo or a stale copy:
      `#201f1d` `#282723` `#2a2926` (vscode night), `#282724` `#2b2a27`
      (README), `#2c2b26` `#ebe8e0` (watcher), `#eceae2` (vscode paper),
      `#edeae2` (antinote paper, obsidian, vscode paper).
      For each: check `git log -S<hex>` for when it entered and whether the
      commit intended a distinct colour. Fix only the unambiguous ones; list
      the rest under FINDINGS. `#edeae2` appears in three files and may be a
      deliberate second tint — treat it as a report, not a fix.

- [x] **Report on the 31 remaining near-misses** (delta 4–8). Unlike the nine
      above these ARE visible, so they may be deliberate hover states or raised
      surfaces. Produce a table: value, nearest core colour, files, and whether
      a comment or commit message justifies it. **Report only. Change nothing.**

- [~] **Remove the four unused `--midori-warm-*` tokens.** REJECTED before
      queueing, and recorded here so it is not rediscovered as a good idea.
      `--midori-warm-wash/-light/-deep/-bridge` are defined in
      `obsidian/theme.css` and never read by `var()`, which makes them look
      like dead code. They are not: they complete the warm ramp whose siblings
      `--midori-clay` and `--midori-terracotta` carry `/* --accent-warm */`
      annotations mapping to the website's token set, and this palette is
      deliberately closed and fully named. Deleting them breaks that property
      to save four lines.

- [x] **Report on `body` being declared 20 times** in `obsidian/theme.css`.
      Likely correct — each is a different token scope (colour mode, rhythm
      mode, accent choice, `@supports`). Confirm that, and list any two blocks
      that set the SAME property under the same conditions, which would be real
      drift. **Report only.**

### Shell and structure

- [~] **Shared shell helpers across the installers.** REJECTED — `set -e`, `REPO_DIR=`
      resolution, and running-app detection (`pgrep -x`) are repeated in all
      seven scripts. Extract to `lib/sh-common.sh`, sourced by each.
      DO NOT merge the installers themselves — `install.sh` is already an
      orchestrator that dispatches to per-target scripts, and each target's
      caveats are load-bearing. Only the boilerplate moves.

- [~] **The JSON-patch heredoc is written three times** REJECTED — in
      `obsidian/install-obsidian.sh` (appearance.json, community-plugins.json)
      and once in `vivaldi/install-vivaldi.sh`. Extract one `patch_json`
      helper. Keep each call site's comment explaining *why that file* is
      patched — those differ and are not duplication.

- [x] **`tests/lint.sh` takes ~60s, and most of it is per-file `py_compile`
      subprocesses.** Batch them into one interpreter invocation. Keep the
      count-and-fail-on-empty guard exactly as it is; that is not overhead.

- [x] **Verify every numeric claim in `README.md` against the code.** One pass,
      listing each claim and whether it still holds. Two prior sweeps found
      five false claims and one inverted ratio. Correct what is wrong; where a
      claim is unverifiable, say so rather than deleting it.

- [x] **Verify every numeric claim in `obsidian/theme.css` comments.** Same
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
### theme.css comments: one false arithmetic claim, corrected (iteration 9)

**Found and corrected.** The `.metadata-container` block stated:

> padding-top + padding-bottom + margin-block-end = inset + 24 + (24 - inset)
> = 48, always two rows.

Both terms are wrong. The margin is `calc(var(--midori-row) * 2 - inset)` =
36px, not `24 - inset` = 12px, so the real total is **72px, three rows**.

It was believed because the sentence describes a margin of *one* row minus the
inset. The margin has always been *two* rows minus the inset — it read
`calc(48px - var(--midori-metadata-inset))` before the row refactor and
`calc(var(--midori-row) * 2 - ...)` after, which are the same 36px. **The
refactor was faithful; the sentence was already wrong when it was written.**

The load-bearing part of the claim is TRUE and was kept: the inset cancels, so
the widget cannot push the prose below it off the grid. 0, 12 and 24px of inset
all total 72px. Only the sum and the row count were wrong. **No code changed.**

One boundary marked rather than papered over: the paragraph that follows
describes removing "a whole row" from that margin and a measured 84px hole.
`git log -S` finds no earlier `72px - inset` form, so whether the removed row
came out of this margin or from above it is unrecoverable. That reasoning is
left exactly as written, with a note saying it was not reconciled and why.

**Method and its limits.** Two mechanical passes: 64 `prop: value` claims
inside comments checked against the file's own declarations, and 14 comment
mentions of a declared `--midori-*`/`--dotgrid-*` variable near a number. Both
produced mostly false positives of the matcher — comments describing `app.css`
behaviour, or a number that merely sits near a variable name. Matching a
property by NAME when the claim is about a SCOPE is the trap this repo's own
guard-test skill names, and it appeared here in the checker rather than the
comments. Every flagged item was inspected by hand; exactly one was real.

### README numeric claims: no false ones found (iteration 8)

136 lines carry a number. They split into two kinds, and only one kind is
checkable against the code — stating that boundary is part of the result.

**Checkable against the code, all verified, all hold:**

- 42 distinct backticked CSS tokens and declarations, matched against
  `theme.css` with comments stripped. 16 did not match; every one inspected
  was a false positive of my matcher, not a false claim: Obsidian's own
  variables that the theme reads but never declares (`--font-text-size`,
  `--background-modifier-form-field`), selectors rather than declarations,
  non-CSS examples from the VS Code and Antinote sections, and behaviour
  attributed to `app.css` rather than to the theme. Spot-checked the three
  that could plausibly have been real — `--midori-title-line-box` exists,
  `color: #FAFAFA` is correctly attributed to `app.css`, and the
  `vertical-align: text-top` at README:778 is the *historical* cause in the
  h1 write-up, correctly stated in the past tense.
- 12 load-bearing typographic constants: the 24px row fallback, `1.870em` /
  `1.690em` heading sizes, `ascent-override: 45%`, the `0.83em / 0.30em`
  title slots, `--midori-slot-rise` / `--midori-slot-drop` at 14px / 5px,
  measure 70, leading 1.5, advance `0.4818`, and the `cm-widgetBuffer`
  `vertical-align: baseline` fix. All present and correct.
- No stale counts or timings. README asserts no `theme.css` line count, no
  comment percentage and no lint runtime, so iteration 7's 112s→46s change
  and the growth of the file leave nothing to correct.

**Not checkable against the code, and not re-measured here:** contrast ratios
(`5.00:1`, `10.89:1`, `1.07:1`), hardware observations (81 ppi, stem widths,
`4 of 8` caret frames), and rendered sweep results (`3/49`, `6 of 18`,
`25 of 63`). These are recorded measurements of things outside the source; the
only honest way to verify them is to re-run the instrument, which needs a live
Obsidian and in some cases specific hardware. Flagged as a boundary, not a
defect.

**One correction to the item's own framing.** It cites "two prior sweeps found
five false claims and one inverted ratio" as reason to expect more. Those were
found *and fixed* earlier in this same branch. A clean pass now is the expected
outcome of that work, not evidence the pass was shallow.

### lint.sh: 112s -> 46s, and the "~60s" in the item was wrong (iteration 7)

Done. The item's premise held — per-file `py_compile` was the cost — but its
number did not. Measured end to end:

| | before | after |
|---|---|---|
| whole suite | **112s** | **46s** |
| py_compile section (20 files) | 32s standalone | **1s** |
| shellcheck section (13 files) | 3s | unchanged |

`python3 -m py_compile` in a loop pays full interpreter startup per file. One
invocation compiling all 20 costs 1s. Nothing else in the script was touched.

**The per-file `ok py_compile <path>` lines are kept.** Collapsing 20 lines
into one "python ok" would have saved nothing further and would have traded a
green section for a green section that cannot say what it checked — the exact
blindness the count guard above it exists to prevent. Python prints the lines,
the shell reads only the exit status, because `bad()` cannot be called from
inside the heredoc.

Sabotage-proved, both directions:

- a syntactically broken file added to the tree: `LINT: failures above`,
  exit 1, `FAIL py_compile ./tests/_sabotage_probe.py: PyCompileError`, and
  the count line correctly rose to 21
- `FILES()` pointed at a nonexistent path on a scratch copy: both
  `no .py files found at all` and `no .sh files found at all` still fire,
  so the empty-set guard the item told me to leave alone is intact

### There is no repeated JSON-patch heredoc to extract (iteration 6)

Rejected. The item said "written three times in `obsidian/install-obsidian.sh`
and once in `vivaldi/`". There are not four instances of one thing. There are
four different programs that share `import json`.

| site | lines | container | operation | on unreadable input |
|---|---|---|---|---|
| `obsidian:80` | 11 | dict | set `cssTheme` **only if** legacy or empty | `sys.exit(0)` — write nothing |
| `obsidian:131` | 13 | list | append id if absent | start `[]` and **write** |
| `obsidian:166` | 7 | list | membership test | writes nothing — it is a shell predicate |
| `vivaldi:63` | 100 | — | enumerate profiles, `/dev/tty` menu, patch Preferences | n/a |

`obsidian:166` is not a patch. It exits 0 or 1 so `||` can catch it in the
shell; extracting it into a "patch" helper would misname what it does.
`vivaldi:63` is a hundred-line interactive program that reads `themes.json`
and `keyboard.json`, resolves a profile by directory or display name, and
prompts on `/dev/tty`. It shares one import.

**The one difference that looks like inconsistency is a safety boundary.**
`appearance.json` bails without writing when it cannot parse the file, because
that file holds settings the user owns and a parse failure must never cost
them. `community-plugins.json` initialises an empty list and writes, because
that file legitimately does not exist in a fresh vault. A single helper forces
one policy onto both, and the failure mode is silently rewriting live user
settings in nine real vaults.

**Ledger:** the genuinely identical text is about four lines — `import json`,
`open`, `json.load`, and the `except (OSError, ValueError)` line — shared by
exactly two sites, whose `except` bodies then differ. A helper covering three
operations across two container types with two failure policies is longer than
what it replaces, and it converts inline code you can read in place into a
dependency you have to go look up.

**One real observation, not queued as work.** `tests/dryrun-installers.sh`
asserts `theme.css` lands in each sandbox vault but does not assert the
*contents* of `appearance.json` or `community-plugins.json`, so the two patch
paths are exercised without being checked. That is a gap in the harness, not
an argument for extraction — and deciding whether to close it is a human call.

### Shared installer helpers would add code, not remove it (iteration 5)

Rejected. The shared boilerplate is exactly two lines per script:

```sh
set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
```

**`REPO_DIR` cannot be extracted — it is the bootstrap.** You cannot move
"find the repo root" into a file you need the repo root to find. Every script
would still open with a `dirname "$0"` line, then gain a `source` line:

```sh
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"      # unchanged, still required
. "$REPO_DIR/../lib/sh-common.sh"              # new
```

Two lines become two lines. Only `set -e` genuinely moves, and it is one word.

**The source line is not even uniform.** `install.sh` and `sync.sh` sit at the
repo root; the five installers sit one level down. So the "shared" line is
`$(dirname $0)/lib/...` for two scripts and `$(dirname $0)/../lib/...` for
five — the duplication is preserved, just relocated and made depth-dependent.

**Two scripts do not use the name.** `install.sh` and `sync.sh` declare `REPO`,
not `REPO_DIR` — zero occurrences of `REPO_DIR` in either. Adopting a shared
helper means renaming a variable throughout two working scripts that write
into live user data, purchasing nothing.

**`pgrep` is not shared code.** Three sites, two behaviours: `pgrep -xq Vivaldi`
branches in `install.sh` and `vivaldi/`, while `obsidian/` uses
`pgrep -x Obsidian >/dev/null 2>&1 && x=1 || x=0` to set a variable it reads
much later. A helper covering both is longer than either.

**Ledger:** 0 lines removed, ~10 added (the new file), 1 new dependency, and
every installer stops working if copied out of the repo — which is how they
are distributed to other machines. CLAUDE.md already warns that these scripts
"carry target-specific caveats that look like duplication and are not"; this
is the boilerplate version of the same mistake.

No installer was modified, so no dry-run receipt is needed.

### `body` in theme.css: 20 bare blocks, one real duplicate (iteration 4)

Report only; nothing changed. Parsed by walking braces and keeping the at-rule
stack, so "same conditions" is actually answerable — a split on `}` cannot see
whether two blocks sit inside different `@supports`.

**The item's premise was half wrong, and that is the interesting part.** It
guessed each `body` block is "a different token scope (colour mode, rhythm
mode, accent choice, `@supports`)". True of the *qualified* selectors — 90
blocks start with `body`, and `body.midori-accent-*`, `body.theme-dark`,
`body.is-mobile`, `body.zen-mode` are all genuinely distinct scopes. But the
**20 blocks whose selector is bare `body` at top level are all the SAME
scope**: identical specificity, identical conditions, split across the file by
topic so each can carry its own explanatory comment.

That is a reasonable way to author a token-heavy stylesheet, and it is exactly
why a duplicate is possible — nothing separates block 5 from block 17 except
distance.

**The one real duplicate:**

| property | lines | value | effect |
|---|---|---|---|
| `--inline-title-margin-bottom` | 2068 and 2920 | `0` in both | later wins; line 2068 is dead |

No behaviour differs today, because both say `0`. The hazard is latent: the two
sit 850 lines apart, each under its own comment explaining why the title adds
no margin, and the explanations are different. Line 2068 says the sizer's top
padding already supplies a full grid row. Line 2920 belongs to a later, larger
treatment that hands the air back through `--inline-title-line-height` and a
`margin-block-start` on `.metadata-container`. **Editing either comment's
reasoning and its declaration would silently do nothing if you picked 2068.**

**Not queued as a fix, deliberately.** Both comments record real reasoning and
CLAUDE.md forbids deleting either. Resolving this means deciding which
explanation is current, merging what the other still contributes, and removing
only the redundant declaration — a judgement call about the design record, not
a cleanup. A human should make it.

**Nothing else overlaps.** Across all 90 `body`-rooted blocks, no other
property is set twice under the same selector and same at-rule context.

### The 31 delta-4-8 near-misses: none need changing (iteration 3)

Report only, as the item required; nothing was changed. Classified by the ROLE
each value plays in the file that uses it, which iteration 2 established is the
question that actually decides justification. Distance to the core palette
decides nothing.

**Deliberate subtle surfaces, states and borders (14).** The role name is the
justification — each exists to sit just off its own background.

| value | nearest core | d | role |
|---|---|---|---|
| `#161513` | `#1a1917` | 4 | `--background-secondary`, `--titlebar-background` (dark) |
| `#262421` | `#22211e` | 4 | `--m-card`, `--colorBgIntense` — carries the comment "lifted warm card, not black" |
| `#262521` | `#22211e` | 4 | `userMessageBackground` |
| `#262a20` | `#2a2825` | 5 | `diffAddedDimmed` — "Dimmed" is in the name |
| `#292d2a` | `#2a2825` | 5 | `memoryBackgroundColor` |
| `#2c2520` | `#2a2825` | 5 | `--midori-warm-wash`, `clawd_background` — a wash |
| `#2e2b28` | `#2a2825` | 4 | `--colorBgIntenser` (night) |
| `#2f2e2b` | `#2a2825` | 6 | `activityBar.border`, `button.secondaryBackground` |
| `#302620` | `#2a2825` | 6 | `diffRemovedDimmed` — "Dimmed" is in the name |
| `#4a463f` | `#524d46` | 8 | `promptBorder` |
| `#4b4845` | `#524d46` | 7 | `border-color` |
| `#4f7d75` | `#548373` | 6 | `--stackColorBg` |
| `#64457b` | `#653f7f` | 6 | `bashBorder` |
| `#e6e4dc` | `#ebe8e2` | 6 | `editorRuler.foreground` — same class as iteration 2's `#2a2926` |
| `#f7f5ef` | `#f3f1eb` | 4 | `lock-background`, `textCodeBlock.background` (4 off its own `#f3f1eb`) |
| `#f8f5ed` | `#f3f1eb` | 5 | `breadcrumbPicker`, `debugToolBar`, `editorHover` backgrounds |
| `#fffdf9` | `#faf9f6` | 5 | `--colorBgIntenser` (paper) |

**A different colour family, so proximity is coincidence (7).** These are
foregrounds and syntax colours; being near a *surface* token means nothing.

`#4c473f`, `#744242`, `#a0998b`, `#a0998e`, `#a39c91`, `#e0b364` are
`foreground` / `symbolIcon.*` / `editorBracketHighlight.*` /
`editorLineNumber.activeForeground`. `#d4a574` is `--midori-warm-bridge`, a
declared palette token in its own right.

**README prose (7). Do not touch.** `#262626`, `#e3e1dc`, `#e5e4e2`,
`#f3f3f3`, `#fafafa`, `#fdfdfc` appear inside recorded measurements.
`#232323` is not even a Midori colour — it sits in a list of THIRD-PARTY
values the README notes "have no key".

**Conclusion: 0 of 31 need action**, which is the same verdict as the nine in
iteration 2 and at four times the sample. Taken together, 40 of 40 flagged
values were deliberate. The near-miss heuristic as built has produced no true
positives, and its output should not be treated as a work list until it
compares each value against its own background.


### measure_palette_drift.py compares against the wrong background (iteration 2)

All nine flagged values are deliberate, so the item was rejected rather than
done. The detector's premise — "within 3/255 of a core colour, therefore
invisible, therefore a typo or stale copy" — does not hold, and the reason is
a flaw in the tool, not in these nine.

**It measures distance to the global core palette. These values exist to be a
sub-visible lift off the background of their own file.** `#201f1d` is 2/255
from core `#22211e`, which is what got it flagged — but it is
`editor.lineHighlightBackground` in a theme whose `editor.background` is
`#1a1917`, six steps away. It is doing its job; proximity to an unrelated
palette entry is coincidence.

Evidence, by role:

| value | role | its own background | verdict |
|---|---|---|---|
| `#201f1d` | `editor.lineHighlightBackground` | `#1a1917` | deliberate lift |
| `#282723` | `list.hoverBackground` | `#1a1917` | deliberate lift |
| `#2a2926` | `editorRuler.foreground` | `#1a1917` | a ruler is meant to be faint |
| `#eceae2` | `lineHighlight`, `inlayHint`, `keybindingLabel` | `#f3f1eb` | deliberate lift |
| `#ebe8e0` | `userMessageBackground` | — | one rung of a ladder: `#ebe8e0` / `#e4e0d6` hover / `#edeae2` bash |
| `#2c2b26` | `userMessageBackgroundHover` | — | the night half of that same ladder |
| `#edeae2` | `--background-secondary`, titlebar, sidebar, statusbar | — | a real secondary surface in 4 files |
| `#282724` | README prose | — | **a recorded measurement**: "`#1a1917 → #282724`, ~1.1:1 either way" |
| `#2b2a27` | README prose | — | **a recorded measurement**: "the editor background under a uniform +17 white, ~7.4%" |

The last two are measurements in the design record. Editing them would
falsify what was measured — see CLAUDE.md.

**What a correct detector would do:** compare each value to the background it
is painted on within its own file, not to the global core set. A lift of 6/255
off your own background is design; being 2/255 from an unrelated token is
noise. That is a real tool fix, and it is NOT queued here — a human should
decide whether it is worth building.

**This also undercuts the next item.** "Report on the 31 remaining near-misses
(delta 4-8)" inherits the same comparison basis, so its list is likely to be
mostly deliberate lifts too. It is report-only, so it is safe to run, but read
its output knowing the premise is suspect.

