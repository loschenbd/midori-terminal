# Palette generation: scope

**Status:** scope only. Nothing here is built. Every number was re-measured on
2026-08-19 against `git ls-files`, excluding `palette.json` and
`docs/cleanup-queue.md` — both quote the values they describe, and including
them inflated an earlier count of this exact kind twice on this branch.

## The finding that should change the plan

The queue framed this as "43 shared values, hand-copied into up to 19 files."
That is true and it is the wrong shape to act on, because the copies are not
evenly spread and the worst offender is not the file anyone worries about.

**`obsidian/theme.css` is already clean and must not be generated.** Each
shared value appears in it exactly once, as a token declaration (twice for the
17 tokens that carry both modes), then reaches the rules through `var()` —
`--midori-sage` has 2 declarations and 6 uses, `--midori-indigo` 2 and 9.
There is no duplication inside the stylesheet to remove. The queue said this
in iteration 4 and it holds: *the duplication is BETWEEN targets, not inside
the stylesheet.*

**Half of all duplication is in two files.** Shared-palette literal
occurrences, repo-wide:

| area | occurrences | share |
|---|---|---|
| `vscode/` | 388 | **50%** |
| `moshi/` | 71 | 9% (already generated from ghostty) |
| `watcher/` | 66 | 8% |
| `obsidian/` | 62 | 8% (already single-definition) |
| `ghostty/` | 50 | 6% |
| `vivaldi/` | 42 | 5% |
| everything else | 89 | 12% |
| **total** | **768** | |

`vscode/midori-theme/themes/midori-{paper,night}-color-theme.json` carry 325
hex literals each. `#5f6f5e` alone is written **24 times** in one file,
because VS Code theme JSON has no variable mechanism — every slot must be a
literal. That is the entire problem, concentrated.

## Why those two files are the right target

- **They are pure data.** 0 comments. Nothing in them is a design record, so
  generating them destroys no understanding — the constraint that governs
  `theme.css` does not apply.
- **They are structurally identical twins.** Both have exactly the same 301
  `colors` keys and 31 `tokenColors`. The light/dark pairing is precisely the
  shape `palette.json` already models.
- **301 keys collapse to 92 distinct (light, dark) pairs.** 602 literals
  express 92 decisions. 95 keys already map to an existing `palette.json`
  role; 104 half-match; 102 match neither. The most repeated unnamed pair,
  `#8f4f38 / #b87d5c`, is used 17 times and is plainly a role that was never
  given a name.
- **Generated assets already ship from this exact directory.**
  `build-icons.py` and `build-product-icons.py` generate files that
  `package.json` references by path, same as the themes. This introduces no
  new idea into the repo.

## Scope

**In:**
1. Extend `palette.json` with the roles the VS Code themes need — chiefly the
   ~30 unnamed but repeated pairs. Names come from the key that uses them, as
   the existing entries do; none invented.
2. A generator, `vscode/build-themes.py`, emitting both theme JSONs from
   `palette.json` plus a key→role map. Follows `build-fonts.py`'s convention:
   regenerate, leave everything else alone, print what it wrote.
3. A round-trip guard: regenerate into a temp file and diff against the
   committed one. Drift fails the build. This is the check that makes the
   generator trustworthy rather than merely present.

**Out, and deliberately:**
- **`obsidian/theme.css`** — already single-definition; generation would put a
  build step between the reader and 2,110 lines of design record for no
  reduction in duplication.
- **`README.md`** (33 occurrences) — documentation quoting values. Must never
  be generated. Worth a *checker* that flags a README hex no longer present in
  any source file, since a stale quoted value is a false record, which this
  repo treats as worse than none.
- **`moshi/`** — already generated from the ghostty themes.
- **`ghostty/`, `antinote/`, `vivaldi/`, `watcher/`** — 1–3 occurrences per
  value each. Real but small, and each has its own format quirks. Revisit only
  after the VS Code generator has proved itself; doing them first spends the
  risk budget on 6% of the problem.

## What this costs

The honest trade: two files stop being hand-editable. Today a colour can be
nudged in the theme JSON and reloaded; afterwards that edit is overwritten by
the next generator run, and the round-trip guard will fail the commit. For
files with no prose and 92 decisions behind 602 literals that is a good trade,
and it is the same trade the icons already made. It would not be a good trade
for `theme.css`, which is why `theme.css` is out of scope.

## Verification, per CLAUDE.md

A generator is exactly the kind of thing that ships green and vacuous here.

- The round-trip guard must **fail on an empty input set** — if it maps zero
  keys, that is a broken generator, not a clean diff.
- Sabotage-proof before trusting: change one role in `palette.json`, confirm
  the guard fails *naming that key*; delete a key from the map, confirm it
  fails naming the missing key.
- Print counts: keys emitted, roles resolved, literals remaining.
- The existing `tests/test_palette_is_defined.py` stays as-is; it answers a
  different question (has a new colour escaped into 4+ files) and would not
  catch generator drift.

## Sizing

One focused session. The generator and its guard are perhaps 150 lines; the
work is in the key→role mapping, where 102 of 301 keys match no existing role
and each needs a judgement about whether it is a role or a genuine one-off.
That mapping is the deliverable — the script is the easy half.
