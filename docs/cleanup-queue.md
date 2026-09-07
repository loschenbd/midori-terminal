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

- [x] **Guards without a sabotage proof.** For each test in
      `tests/test_prose_typography.py`, check whether a sabotage proof is
      recorded in its docstring. List the ones that lack one. Do not
      write the proofs in this pass — just produce the list.

- [x] **`obsidian/plugins/midori-timer/main.js` is 2,119 lines.** Identify
      natural seams (parsing, formatting, caret colour, settings) and report
      whether a split is worth it. Report only; do not split in this pass.

- [x] **Dead files.** Find tracked files referenced by nothing — no import, no
      script, no doc link. Each candidate must ship with the grep that proves
      it. Report only; delete nothing in this pass.

---

## FINDINGS FOR REVIEW

The loop appends here. These are NOT work items until a human moves them up.

<!-- loop appends below this line -->
### Guards without a sabotage proof: 18 of 21 (iteration 10)

Report only; no proofs written, per the item.

**Three guards carry a concrete recorded proof** — a specific break, and what
the suite did when it was applied:

- `test_snapped_vars_all_have_plain_fallbacks` — deleting the plain fallback
- `test_rhythm_modes_all_exist` — `calc(var(--midori-row) / 2)`, the near-miss
  that kept the token being matched on and changed its meaning
- `test_accent_derived_roles_follow_the_accent` — "stayed green"

`test_row_is_an_even_number_of_pixels` uses break-language but names no
specific sabotage, so it is counted as unproven.

**Ranked by the failure shapes this branch actually hit**, not alphabetically.
Every shape below has produced a real vacuous guard in this repo already.

| priority | guard | risk shape |
|---|---|---|
| 1 | `test_row_is_one_number` | **no docstring at all** + `theme_var` + unscoped regex |
| 2 | `test_row_is_an_even_number_of_pixels` | `theme_var` + unscoped regex |
| 2 | `test_leading_setting_is_snapped` | substring match + unscoped regex |
| 3 | `test_measure`, `test_leading_stays_above_the_measured_harm_floor`, `test_heading_ladder_is_optical`, `test_settings_defaults_match_the_css`, `test_dot_alpha_is_split_in_both_modes` | `theme_var` — last-match-wins |
| 4 | `test_blank_line_keeps_the_grid`, `test_indent_excludes_non_prose` | substring match |
| 5 | `test_no_stray_grid_literals`, `test_settings_block_parses` | unscoped regex / name-not-scope |
| — | `test_zen_header_rules_are_gated`, `test_settings_ids_are_real`, `test_inputs_are_never_read_by_a_real_property`, `test_space_rhythm_zeroes_the_indent_variable`, `test_accent_options_are_palette_tokens` | no known-bad shape, still unproven |

Why those shapes: `theme_var()` returns the **textually last** declaration, so
it cannot see an earlier one being deleted — that is how a deleted plain
fallback stayed green here. Substring matching is how
`calc(var(--midori-row) / 2)` passed a whole-row check. Both are recorded in
`~/.claude/skills/guard-tests-need-a-sabotage-proof-not-a-reading`.

**One of these is mine, from this session.**
`test_widget_buffer_is_baseline_anchored` WAS sabotage-proved both directions
— reverted to `text-top`, and the declaration deleted — but the proof went
into the commit message, not the docstring. A future reader opening the test
sees no proof. That is a real gap even though the work was done, and it is the
cheapest one on this list to close.

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


### midori-timer split: not viable, and the 2,119 is misleading (iteration 11)

**Verdict: do not split.** Not because the seams are bad — they are unusually
clean — but because the packaging forbids it, and the failure mode if you did
it anyway is silent.

`CLAUDE.md` and `obsidian/install-obsidian.sh:118-126` agree: only
`manifest.json` and `main.js` are copied into a vault. A sibling
`parsing.js` would resolve fine from the repo (`tests/test_caret_writes.js:58`
`require()`s `main.js` in place, so the test suite would stay green) and would
be **absent** in all nine vaults. `require('./parsing')` there throws at plugin
load, which Obsidian reports as a disabled plugin, not as a missing file. Green
tests, dead plugin, no message naming the cause — the same shape as the drift
the installer's own header warns about.

The two ways out are both larger than cleanup: teach the installer to copy a
directory (giving up the audited "one self-contained file" property that also
keeps a third-party `styles.css` out), or add a bundler (so the file installed
stops being the file you read, which is the property this repo's comments
depend on). Either is a packaging decision for a human, not a tidy-up.

**The line count overstates the logic.** Of 2,119 lines:

| span | what | lines |
|---|---|---|
| L1-161 | header comment block | 161 |
| L164-436 | pure logic: `parseDuration`, `formatClock`, `caretColor`, `parseClockTime`, `secondsUntil`, `endsAtClock`, `formatHuman`, `chime` | 273 |
| L437-931 | the `STYLE` template literal — injected CSS, not JS | **495** |
| L937-1275 | display widgets: `Drum`, `FlapBoard`, and their helpers | 339 |
| L1276-1604 | `DurationModal` | 329 |
| L1605-2004 | `module.exports = class MidoriTimer` | 400 |
| L2005-2119 | `MidoriTimerSettings` | 115 |

555 lines match a comment prefix. Between the comments and the CSS literal,
roughly half the file is not JavaScript logic at all. The largest single
"unit" of actual code is the plugin class at 400 lines.

**The seams, recorded for whoever revisits the packaging question.** L164-436
is the one genuinely portable block: no `obsidian` import, no DOM, pure
functions — which is exactly why `tests/test_midori_timer.js` can strip the
`require('obsidian')` line and run it. The widget classes (L937-1275) depend
only on the DOM and on `DRUM_ITEM`, which `STYLE` must agree with — the comment
at L937 says so, and splitting those two apart would put a stated invariant
across a file boundary with nothing checking it. That pairing is an argument
against one of the more obvious cuts, not for it.

### Dead files: 5 candidates, and 25 false positives worth more than them (iteration 12)

Scanned all 178 tracked files, reading every one as a haystack (178 read, 0
skipped — an empty corpus would have aborted). A file counted as referenced if
its path or basename appeared in any *other* tracked file. That produced 30
unreferenced files. **25 of the 30 are alive.** The false positives are the
finding; the 5 survivors are almost an afterthought.

**Why a name-grep dead-file detector is wrong here, in four distinct ways:**

| mechanism | example | files it hid |
|---|---|---|
| glob copy | `install.sh:30` `cp "$REPO/fonts/"*.ttf` | 7 fonts |
| glob copy | `vivaldi/install-vivaldi.sh:58` `cp "$REPO_DIR/css-mods/"*.css` | 8 css-mods |
| **constructed name** | `install.sh:46-47` builds `midori-$m-$k@2x.png` from two loop variables | 8 backgrounds |
| **variable-interpolated path** | `install.sh:102` `render "$REPO/watcher/$LABEL.plist.template"` | 1 plist template |
| **convention, never named** | `.vscodeignore` is read by `vsce` at package time; nothing in the repo mentions it, and nothing should | 1 |

The last three are the dangerous ones: no amount of improving the *pattern*
finds them, because the referencing string does not exist anywhere in the repo
— it is assembled at runtime or known only to an external tool. Any future
"unused file" tooling here must treat a glob or an interpolated path as a
reference to everything it can match, and must have a convention allowlist.
Deleting on this detector's raw output would have removed all eight terminal
backgrounds and the launchd template.

**The 5 genuine candidates.** Each proof is
`git grep -I -l -F -- "<basename>" -- ":!<path>"` returning zero files:

| file | size | verdict |
|---|---|---|
| `serif-top.png` | 184K | **DELETED 2026-08-19.** A screenshot committed to the repo root by `74368ce` ("notices were Obsidian's dark toast on a paper page"). Debugging evidence for a fix that shipped; the commit message already carries the finding. The only file at the root that is not a script, a config, or a doc. |
| `vivaldi/icons/moon.svg` | 4K | **Keep.** `midori-dark-mode-icon.css:18` inlines this exact path as a `data:` URI, and `install-vivaldi.sh:58` copies only `css-mods/*.css`, never `icons/`. So nothing loads the file — but it is the readable source of an unreadable percent-encoded blob. That is the design record, not dead weight. |
| `docs/cleanup-loop.md` | 8K | **Keep, and link it.** The runbook for this loop. Written to be found by a human, and currently findable only by knowing it exists. `README.md:526` links a spec under `docs/`, so docs here are linked when someone remembers to. |
| `docs/superpowers/plans/2026-08-17-theme-settings.md` | 60K | **Keep.** A completed implementation plan. Plans are historical records; being unlinked is their normal end state. |
| `docs/superpowers/specs/2026-07-15-installer-wizard-design.md` | 8K | **Needs a human.** A design for an installer wizard, unlinked and — unlike the plan above — with no obvious shipped counterpart. Either it was never built (in which case it is an open idea, not dead) or it was and nothing records that. Do not delete on the strength of a zero-reference count; find out which. |

**Net: one file (184K) is safely deletable, and the item's premise — that
unreferenced means dead — held for 1 of 30 hits.**

### Sabotage proofs written for 6 guards, and one was vacuous (2026-08-19)

Worked the iteration-10 list from the top. Every sabotage ran against a
`git archive HEAD` copy in a scratch directory; the real theme was never
edited.

**One real defect, in `test_leading_setting_is_snapped`.** Its floor check was
the substring `"max(24px" not in raw`, and it was wrong in both directions:
`max(24px * 0, ...)` destroys the floor and kept the whole suite green, while
merely wrapping the declaration across lines makes it `max( 24px,` and failed
correct CSS. Fixed with `max_operands()`, which splits the argument list with
depth tracking. Re-proved after the fix in all four directions.

**Sound, now with their proofs recorded:** `test_row_is_one_number` (had no
docstring at all), `test_row_is_an_even_number_of_pixels`,
`test_dot_alpha_is_split_in_both_modes`, `test_widget_buffer_is_baseline_anchored`
(proof existed, but only in a commit message).

**The iteration-10 ranking was itself wrong, in the shape this repo keeps
producing.** It flagged five guards as priority 3 for "`theme_var` —
last-match-wins". The condition that makes `theme_var` dangerous is the
property being declared **more than once**. Checked against the stylesheet:

| guard | reads via theme_var | declared >1x |
|---|---|---|
| `test_leading_stays_above_the_measured_harm_floor` | `--midori-row` | **yes (x2)** |
| `test_measure` | `--file-line-width`, `--midori-avg-advance` | no |
| `test_heading_ladder_is_optical` | — uses `theme_vars` | n/a |
| `test_settings_defaults_match_the_css` | — uses `theme_vars` | n/a |
| `test_dot_alpha_is_split_in_both_modes` | — uses `theme_vars` | n/a |

Three of the five do not call `theme_var` at all. I ranked them by grepping
for the helper's NAME instead of checking whether the risk condition was
present — the same error as matching a property by name when the contract is
per-scope, which this branch has now produced four times. The remaining
priority-4/5 entries were ranked the same way and should be re-derived, not
trusted.

**A trap for anyone sabotaging theme.css:** lines 25 and 232 quote these
declarations in prose. A `replace(..., 1)` edit hits the COMMENT, the real
declaration survives, and the suite is correctly green — which reads exactly
like the guard missing the break. It cost me one false "confirmed exploit"
here. Any sabotage against this file must assert which line it edited.

---

## Queue — guard sabotage proofs (added 2026-09-01)

`tests/test_prose_typography.py` holds 21 guards. **Nine carry a sabotage
proof; twelve do not.** This queue is those twelve, one per iteration.

A proof here means what the skill means: a specific break, applied to a
scratch copy, and a record of what the suite did — not a reading of the
assertion, and not a note that some *earlier version* of the test was green
under it. Five of the twelve already name their break in the docstring; for
those the sabotage is chosen and only the outcome is missing.

### The iteration-10 ranking is NOT used here

That ranking is discredited in its own follow-up: it was built by grepping
for the helper's NAME rather than checking whether the risk condition was
present. This ordering was re-derived from the stylesheet on 2026-09-01.
Re-derive it again rather than trusting the table below.

`theme_var()` returns the textually last declaration, so it cannot see an
earlier one being deleted. **The risk condition is the property being
declared more than once** — not the call appearing. Measured:

| guard | reads via `theme_var` | declared >1x |
|---|---|---|
| `test_row_is_one_number` | `--midori-row` | **yes (2x)** — proved |
| `test_row_is_an_even_number_of_pixels` | `--midori-row` | **yes (2x)** — proved |
| `test_leading_stays_above_the_measured_harm_floor` | `--midori-row` | **yes (2x)** — item 1 below |
| `test_measure` | `--file-line-width`, `--midori-avg-advance` | no (1x each) |
| `test_heading_ladder_is_optical` | `--h1..h4-size` (f-string) | no (1x each) |
| `test_settings_defaults_match_the_css` | `--{id}` (f-string, every control) | no — see below |

Two corrections to the earlier account, both found by measurement:

- `test_measure` **does** call `theme_var`; the earlier note said the
  priority-3 group did not call it at all. It does — harmlessly, on two
  singly-declared properties. "Does not call it" and "calls it without
  exposure" are different findings and only the second is true here.
- `test_settings_defaults_match_the_css` and `test_heading_ladder_is_optical`
  call `theme_var` through an **f-string**, which a literal-argument grep
  cannot see. Both are clean anyway: the heading sizes are declared once
  each, and the defaults guard filters to `variable-*` controls, all five of
  which are declared exactly once. `--midori-accent` is declared 10x but is a
  `class-select` and is skipped.

So exactly **one** unproved guard carries the last-match-wins exposure, not
five. The rest are ranked by the other shapes this repo has actually shipped:
substring matching (which produced the one real defect found so far, in
`test_leading_setting_is_snapped`), unscoped regex, and rule-exists-but-does-
not-take-effect (the specificity-contest shape, hit at least twice).

### The trap that costs a false "confirmed exploit"

`obsidian/theme.css` quotes whole declarations in its own prose. Measured:
`--midori-row:` matches **4** times in the raw file and **2** with comments
stripped — half the textual matches are commentary. A `replace(..., 1)`
sabotage edits the comment, the real declaration survives, the suite is
correctly green, and it reads exactly like the guard missing the break.

**Every sabotage in this queue must assert which line it edited**, and must
re-read the file after editing to confirm the live declaration changed.

### Extra rules for this queue

The 8 steps in "How to do an item" apply unchanged. Three additions:

- Sabotage a `git archive HEAD` copy in a scratch directory. **Never edit the
  real theme**, and never `git checkout` over an edit to undo it.
- Prove in **both** directions: the break must FAIL *naming what broke*, and
  the unmodified copy must pass. A break that fails with an unrelated message
  is a different defect, not a proof.
- Record the proof in the **docstring**, not only the commit message. A future
  reader opens the test, not the log. That gap is why
  `test_widget_buffer_is_baseline_anchored` was counted unproven for a week
  after the work was done.
- If a guard turns out to be vacuous, **fix it and re-prove all four
  directions** — that is still one item, and it is the outcome that makes this
  queue worth running.

### Tier 1 — the measured last-match-wins exposure

- [ ] **`test_leading_stays_above_the_measured_harm_floor` (L436).** The only
      unproved guard reading a property declared twice. `theme_var` returns
      the `@supports` `round(up, max(24px, ...), 2px)` form, so the plain
      `--midori-row: 24px` fallback above it is invisible to this guard.
      Sabotage: (a) delete the plain fallback declaration only — record
      whether this guard notices, and if it does not, say so plainly rather
      than treating another guard's coverage as this one's; (b) set the
      leading slider's `min` in @settings below the Rello floor (0.9) — must
      FAIL naming the floor and the computed leading; (c) remove the `max(24px,
      ...)` clamp so the row can collapse. State which line each edit hit.

### Tier 2 — substring matching and unscoped regex

- [ ] **`test_settings_ids_are_real` (L870).** Three substring operations, and
      its docstring makes a testable claim: that matching `THEME_NC` rather
      than `THEME` stops a comment from satisfying the check. Sabotage: (a)
      typo one control's `id` — must FAIL naming that id; (b) point a control
      at an id that appears **only inside a comment** in theme.css — must
      still FAIL. (b) is the one that proves the docstring, and it is the one
      a reading cannot verify.

- [ ] **`test_no_stray_grid_literals` (L273).** Substring plus the only
      unscoped regex left among the unproved. Sabotage: (a) replace one
      `line-height: var(--midori-row)` consumer with a literal `48px` — must
      FAIL naming the selector; (b) put `48px` inside a **comment** — must NOT
      fail. Then record the guard's real boundary: it checks 24/48/72/96 only,
      so a grid literal at another multiple passes. That is documented intent,
      but it has never been demonstrated — demonstrate it.

- [ ] **`test_measure` (L162).** Three substring operations against the
      @settings block. Sabotage: (a) change `--file-line-width` from the
      `calc(var(--font-text-size) * N)` form to a bare `34em` — must FAIL
      naming the em-resolves-against-own-font-size trap the docstring
      describes; (b) widen the measure slider's bounds past the evidence band
      — must FAIL naming the bound. Note whether (a) actually fails: the
      docstring says the subject changed when measure became a setting, and a
      guard that now asserts only default-and-bounds may no longer look at the
      unit at all.

### Tier 3 — the break is already named; only the outcome is missing

These four are the cheapest on the list. The sabotage is written in the
docstring; apply it verbatim and record what the suite did.

- [ ] **`test_accent_options_are_palette_tokens` (L1198).** Apply the exact
      break its docstring names: `body.midori-accent-wine { --midori-accent:
      var(--midori-clay); }` — a class and token that both exist, pointing at
      each other wrongly. Must FAIL naming the mismatched pair.

- [ ] **`test_zen_header_rules_are_gated` (L757).** Apply both halves the
      docstring names: gate on `.show-view-header` alone (satisfied by
      `body.zen-mode.show-view-header`, which is how the earlier version
      passed), then gate on `.is-phone` alone. Each must FAIL naming the
      missing condition — a single failure for both is not a proof that the
      guard distinguishes them.

- [ ] **`test_settings_block_parses` (L794).** Apply the break its docstring
      names: set the heading-scale slider's `max` to `3`, which shipped green
      under the old version. Must FAIL naming the cap. Then delete a
      `default:` from one control and confirm the well-formedness half still
      fires — the docstring claims two independent jobs and only one has ever
      been exercised.

- [ ] **`test_space_rhythm_zeroes_the_indent_variable` (L1106).** Apply the
      break its docstring names: replace the `--midori-indent` override with a
      plain `text-indent: 0` on a body class, which loses the specificity
      contest against the eleven-component Live Preview selector and shipped
      green. Must FAIL naming the property. This is the repo's signature
      failure shape; a proof here is worth more than the item's size suggests.

### Tier 4 — rule-exists-but-may-not-take-effect, no break named anywhere

- [ ] **`test_blank_line_keeps_the_grid` (L706).** Five-line docstring, and it
      scans for one specific bad declaration: `.cm-line` with `line-height:
      normal`. Sabotage: (a) add exactly that — must FAIL; (b) add
      `line-height: 1.2` on `.cm-line` instead, which leaves the grid just as
      surely — record whether it passes. If it does, this guard proves the
      absence of one known pattern, not that the blank line keeps the grid,
      and the docstring should say which of the two it is.

- [ ] **`test_inputs_are_never_read_by_a_real_property` (L961).** Seven-line
      docstring, no break named, and it carries the branch's central promise —
      "no setting can break the grid" — as an enforceable rule. Sabotage: make
      a real property read `var(--midori-set-leading)` directly, bypassing the
      derived variable where the clamping lives. Must FAIL naming the
      property. Try it once in a rule and once inside a `calc()`.

- [ ] **`test_settings_defaults_match_the_css` (L910).** Verified clean of the
      `theme_var` exposure above, so this is about the comparison itself.
      Sabotage: (a) change one control's `default:` without touching the CSS —
      must FAIL naming which; (b) change it to a numerically equal but
      differently written value (`1` vs `1.0`) — must NOT fail, which is what
      the numeric-compare branch exists for and has never been shown to do;
      (c) delete a `variable-*` control's CSS declaration entirely — must FAIL
      with "declared nowhere".

- [ ] **`test_heading_ladder_is_optical` (L664).** Five-line docstring.
      `OBSIDIAN_H` covers levels 1–4 only; `--h5-size` and `--h6-size` are
      declared nowhere, which is consistent, not a gap — confirm that before
      anything else so the item is not spent on a false alarm. Sabotage: (a)
      change one `--hN-size` so the optical step moves more than 0.02 — must
      FAIL naming the level and both ratios; (b) wrap a size in
      `calc(... * var(--midori-set-heading-scale))` — must still pass, which is
      what `em_value()` unwrapping is for and has never been demonstrated.
