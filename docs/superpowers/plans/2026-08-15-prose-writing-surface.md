# Prose Writing Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the Midori theme's writing surface onto the three typographic
settings that survived evidence review — a measure inside the preference band,
a vertical grid that follows the reader's own text size instead of assuming
16px, and a heading ladder whose *visual* steps match its em steps — without
touching anything the evidence does not support.

**Architecture:** Every change is a CSS custom property in `obsidian/theme.css`
plus a static test that reads the stylesheet back and checks the number in the
units the research uses (characters per line, ratio of leading to base size,
x-height). No JavaScript, no new plugin, no new dependency. The one risky
change — making the 24px grid scale — is gated behind a rendered measurement,
and reverts to a fixed grid with a documented supported range if that
measurement disagrees.

**Tech Stack:** CSS custom properties; Python 3 (stdlib only) for the static
tests, wired into `tests/lint.sh`; a generated HTML harness driven through the
browser for the rendered checks; `fontTools` (already in `obsidian/.fontenv`)
only for re-deriving font constants, never at test time.

## Global Constraints

- **Evidence source of truth:** `docs/superpowers/specs/2026-08-15-prose-typography-evidence.md`. Do not introduce a number this plan does not trace to it.
- **Nothing enters the writing surface unbidden.** No new element, no new mark, no animation on the page. Every change here is a property of something already on screen.
- **Font constants, measured from `fonts/*.ttf` with a `BoundsPen`, not `OS/2`:** M PLUS 1p x-height `0.520`em, cap `0.730`em, average prose advance `0.4818`em. Spectral x-height `0.450`em, cap `0.660`em, average advance `0.4352`em. Re-derive with `obsidian/.fontenv/bin/python3 tests/measure_prose_type.py`.
- **Characters per line = `N ÷ 0.4818`** where the measure is `calc(var(--font-text-size) * N)`. This is the only conversion between a stylesheet number and the research's unit.
- **Target band: 55–75 cpl**, preference side of the speed/preference split. 66 cpl = `N 32`, 70 cpl = `N 34`, 75 cpl = `N 36`.
- **Never express `--file-line-width` in `em`.** app.css consumes it on `.cm-line`, which is also the heading element; see "The schema this plan works with".
- **Leading floor: CSS 1.2** (measured harm floor). **Policy floor: 1.5** (WCAG 1.4.8, not an experimental result). Aim ≥ 1.5.
- **A backtick inside an injected stylesheet template literal ends it** — not applicable to `theme.css`, but `tests/lint.sh` must stay green including `tests/check_style_literals.py`.
- **Every change must be installed and re-verified** with `sh obsidian/install-obsidian.sh`, which fans out to all three vaults.
- **Commit after every task.** `sh tests/lint.sh` must be green before each commit.

---

## The schema this plan works with

Read out of Obsidian's own `app.css`, extracted from the installed app with
`python3 obsidian/dump-app-css.py <outdir>`. Not from documentation, and not
from a blog post. Re-run it after an Obsidian update before trusting any of the
below.

**The variables, with their real defaults:**

| variable | default | notes |
|---|---|---|
| `--font-text-size` | `16px` | Set **inline on `body`** by the app from `baseFontSize`, **clamped to 10–30**. The same code also sets `font-size` on `documentElement`, so `rem` tracks it too. |
| `--file-line-width` | `700px` | Consumed on **four** elements — see the trap below. |
| `--h1-size` … `--h6-size` | `1.618em`, `1.462`, `1.318`, `1.188`, `1.076`, `1em` | **Not** the ladder this plan originally assumed. |
| `--h1-font` … `--h6-font` | `inherit` | Exists. The theme currently reaches past it with element selectors. |
| `--h1-weight`, `--hN-style`, `--hN-variant`, `--hN-color` | various | 36 heading variables in total; the theme sets 6 of them. |
| `--inline-title-size` / `-font` / `-weight` | `var(--h1-*)` | The title **follows h1 for free** if h1 is set through its variables. |

**The units trap, which is real and would have shipped as a bug.** app.css
consumes `--file-line-width` as `max-width` on `.cm-sizer`, `.cm-content` **and
`.cm-line`**, all gated behind `.is-readable-line-width`:

```css
.markdown-source-view.mod-cm6.is-readable-line-width .cm-line { max-width: var(--file-line-width); }
```

`.cm-line` is also where headings live — `.HyperMD-header-1` sets
`font-size: var(--h1-size)` on the *same element*. A `max-width` in `em`
resolves against the element's **own** font-size, so an em measure makes
heading lines wider than body lines. Measured in a browser, at a 34em measure:

| | body line | h1 line | h4 line |
|---|---|---|---|
| `34em` | 544px | **880px** | **646px** |
| `calc(var(--font-text-size) * 34)` | 544px | 544px | 544px |

So the measure must be **`calc(var(--font-text-size) * N)`**, which resolves
numerically before it reaches the consuming element. `rem` would also work
today, but only because the app happens to set `documentElement`'s font-size —
an implementation detail found by reading minified JS, not a documented
contract. `--font-text-size` is documented; prefer it.

**Two consequences beyond the measure.** The `.is-readable-line-width` gate
means everything here is inert for a reader who has turned readable line length
off — correct, and not something to fight. And app.css uses the same variable
for `.document-search`, so the find bar stays aligned to the column for free.

## File Structure

| File | Responsibility |
|---|---|
| `obsidian/theme.css` (modify) | All CSS changes. Measure at ~line 32 in the root variable block; `--midori-row` beside it; dot grid at 402; line-height rules at 583, 1118, 1147–1149, 1173–1179, 1357–1458; heading sizes in a new block beside the existing heading colours at 1603. |
| `tests/test_prose_typography.py` (create) | Static guardrails. Parses `theme.css`, converts to cpl and leading ratios across the app's whole 10–30px base range, asserts the bands. Stdlib only so it runs in `lint.sh` and CI. |
| `tests/prose_harness.py` (create) | Generates an HTML page from the *real* `theme.css` for rendered checks. Not run by lint; invoked by hand in verification steps. |
| `tests/lint.sh` (modify) | Wire in the new test beside the existing `midori-timer unit tests` block. |
| `tests/measure_prose_type.py` (existing) | Already committed. Re-derives the font constants. Unchanged. |
| `docs/superpowers/specs/2026-08-15-prose-typography-evidence.md` (existing) | Evidence. Unchanged by this plan. |
| `README.md` (modify) | One findings bullet per shipped change, in the established voice. |
| `obsidian/manifest.json` (modify) | Version bump at the end. |

---

### Task 1: The measure

The one setting currently outside every band anyone has proposed: Obsidian's
default 700px column with M PLUS 1p is ~91 cpl at a 16px base. Expressed as a
multiple of `--font-text-size` it stays inside the band when the reader changes
their text size, which a px constant does not — and unlike an `em`, it is not
re-resolved against the font-size of whatever element consumes it.

**Files:**
- Create: `tests/test_prose_typography.py`
- Modify: `obsidian/theme.css` (root variable block, ~line 32)
- Modify: `tests/lint.sh` (beside the `midori-timer unit tests` block, ~line 58)

**Interfaces:**
- Produces: `--file-line-width` as `calc(var(--font-text-size) * N)`; the helper `theme_var(name)` and constant `AVG_ADVANCE_EM = 0.4818` in `tests/test_prose_typography.py`, both consumed by Tasks 2 and 3.

- [ ] **Step 1: Write the failing test**

Create `tests/test_prose_typography.py`:

```python
#!/usr/bin/env python3
"""The writing surface, checked in the units the research is stated in.

A stylesheet says "34em" and "24px". The evidence says "characters per line"
and "ratio to base size". This converts, so a change that looks harmless in
CSS cannot quietly leave the band. Evidence and provenance for every number:
docs/superpowers/specs/2026-08-15-prose-typography-evidence.md

Font constants are measured from the real outlines with a BoundsPen (NOT from
OS/2, which is designer-typed metadata). They are inlined rather than read from
the TTFs so this runs on a stdlib interpreter in lint and CI; re-derive with
    obsidian/.fontenv/bin/python3 tests/measure_prose_type.py
"""

import math
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
THEME = (REPO / "obsidian" / "theme.css").read_text()

AVG_ADVANCE_EM = 0.4818     # M PLUS 1p, averaged over a prose sample
X_MPLUS = 0.520             # x-height, em
X_SPECTRAL = 0.450

# app.js clamps baseFontSize to 10..30 (Math.clamp(e, 10, 30)), so this is the
# whole reachable range, not a range we chose.
BASES = tuple(range(10, 31))

FAIL = []


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    print(f"  FAIL {msg}")
    FAIL.append(msg)


def theme_var(name):
    """Last declared value of a custom property, as a string.

    NOT anchored to the start of a line: an earlier draft was, and it silently
    reported "not set" for every declaration that shared a line with another
    one — which reads as a missing variable rather than as a regex that cannot
    see it. A `var(--x)` USE cannot match here, because a use has no colon
    after the name.
    """
    hits = re.findall(rf"{re.escape(name)}\s*:\s*([^;]+);", THEME)
    return hits[-1].strip() if hits else None


def em_value(raw):
    m = re.fullmatch(r"([0-9.]+)em", (raw or "").strip())
    return float(m.group(1)) if m else None


def test_measure():
    """The measure, in characters, and in a unit that survives its consumers.

    app.css applies --file-line-width as max-width on .cm-line, and .cm-line is
    also the heading element (.HyperMD-header-1 sets font-size: var(--h1-size)
    on it). An em there resolves against the element's OWN font-size, so an em
    measure gives heading lines a wider column than body lines: measured, 34em
    is 544px on a body line and 880px on an h1. calc(var(--font-text-size) * N)
    resolves numerically before it reaches any consumer.
    """
    raw = theme_var("--file-line-width")
    if raw is None:
        bad("--file-line-width is not set; Obsidian's 700px default is ~91 cpl at 16px")
        return
    if em_value(raw) is not None:
        bad(f"--file-line-width is {raw!r}: an em measure is resolved against the "
            "font-size of .cm-line, which is 1.618em on a heading line")
        return
    m = re.fullmatch(r"calc\(\s*var\(--font-text-size\)\s*\*\s*([0-9.]+)\s*\)", raw)
    if not m:
        bad(f"--file-line-width is {raw!r}: expected "
            "calc(var(--font-text-size) * N), which both tracks the reader's "
            "text size and is immune to the consuming element's font-size")
        return
    cpl = float(m.group(1)) / AVG_ADVANCE_EM
    if 55.0 <= cpl <= 75.0:
        ok(f"measure {raw} = {cpl:.1f} characters per line, inside 55-75")
    else:
        bad(f"measure {raw} = {cpl:.1f} characters per line, outside 55-75")


if __name__ == "__main__":
    print("== prose typography ==")
    test_measure()
    print("prose typography: all green" if not FAIL else "prose typography: failures above")
    sys.exit(1 if FAIL else 0)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: FAIL — `--file-line-width is not set; Obsidian's 700px default is ~91 cpl at 16px`, exit 1.

- [ ] **Step 3: Build the comparison harness and pick the width**

Create `tests/prose_harness.py`:

```python
#!/usr/bin/env python3
"""Render real prose in the real theme, at several measures, for a look.

Loads obsidian/theme.css itself rather than a copy, so what is judged is what
ships. Writes to the path given as argv[1] (default ./prose.html) and expects
to be served over http, not opened as file:// — Chrome blocks font loading and
some CSS on file URLs.

    python3 tests/prose_harness.py /tmp/prose.html
    python3 -m http.server 8777 --directory /tmp
"""

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CSS = (REPO / "obsidian" / "theme.css").read_text()

PROSE = """<p>The question of how long a line of text should be is older than the
screen, and most of the answers in circulation were never measured at all. A
writer revising a paragraph moves through it differently than a reader meeting
it once: the eye returns to the line just finished, hops back to the start of
the sentence, and leaves again. Whether that pattern wants a shorter measure
than reading does is, as far as the literature goes, an open question.</p>
<p>What is not open is that the same stylesheet is a different size on every
panel it lands on. An angle is not a length, and a length is not a size until
something says how far away the reader is sitting.</p>"""

WIDTHS = ("calc(var(--font-text-size) * 32)",   # 66 cpl
          "calc(var(--font-text-size) * 34)",   # 70 cpl
          "calc(var(--font-text-size) * 36)",   # 75 cpl
          "700px")                             # today, ~91 cpl

def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "prose.html")
    blocks = "\n".join(
        f'<section><h3>{w}</h3>'
        f'<div class="markdown-preview-view" style="--file-line-width:{w}">'
        f'<div class="markdown-preview-sizer">{PROSE}</div></div></section>'
        for w in WIDTHS
    )
    out.write_text(f"""<!doctype html><meta charset=utf-8><title>Measure</title>
<style>{CSS}
body {{ font-family: "Midori Text", system-ui, sans-serif; }}
section {{ margin: 0 0 48px; }}
section h3 {{ font: 12px ui-monospace, Menlo, monospace; color: #888; margin: 0 0 8px; }}
.markdown-preview-sizer {{ max-width: var(--file-line-width); }}
</style>
<button onclick="document.body.classList.toggle('theme-dark');
                 document.body.classList.toggle('theme-light')">night</button>
{blocks}
<script>document.body.classList.add('theme-light');</script>
""")
    print("wrote", out)

if __name__ == "__main__":
    main()
```

Run it, serve it, and look at all four at your real viewing distance:

```bash
python3 tests/prose_harness.py /tmp/claude-501/prose.html
python3 -m http.server 8777 --directory /tmp/claude-501
```

**This step ends in a decision, and it is Ben's, not the implementer's.** The
evidence supports the *band*, not a point inside it: reading speed favours the
long measure, preference favours the moderate one, and a writing surface takes
the preference side. `calc(var(--font-text-size) * 34)` (70 cpl) is the default
recommendation because it is the smallest change from today's ~91 that lands
inside the band. Record the
chosen value before continuing.

- [ ] **Step 4: Set the measure**

In `obsidian/theme.css`, in the root variable block that already holds
`--font-text-theme` (~line 32), add:

```css
  /* MEASURE, IN EM AND NOT PX, WHICH IS THE WHOLE POINT.

     Obsidian's default is 700px, which with "Midori Text" is ~91 characters
     per line at a 16px base and ~97 at 15px — outside every band anyone has
     proposed. The band itself has no experiment behind it (Spencer 1968
     asserts ~70; Rayner & Pollatsek deduce 52 from Tinker's PRINT data; no
     screen study produced the range), so this is not a correction toward a
     finding. It is the preference side of the one result that IS solid: longer
     lines are read faster, moderate lines are preferred, and subjective
     ratings do not track performance. A writing surface is chosen, sat at for
     hours, and not a speed-reading task.

     In em because characters-per-line depends on BOTH width and size: a px
     constant silently becomes a different measure the moment the reader moves
     Settings -> Appearance -> Font size, and this theme now ships to people
     whose slider is not where mine is (the app clamps it to 10-30px).

     NOT em, which is the version of this that looks right and is not. app.css
     applies this variable as max-width on .cm-line -- and .cm-line is also the
     heading element, carrying font-size: var(--h1-size). An em resolves
     against the element's OWN font-size, so an em measure hands heading lines
     a wider column than body lines: measured, 34em is 544px on a body line and
     880px on an h1. A calc against --font-text-size resolves numerically
     before it ever reaches a consumer. 34 / 0.4818 average advance = 70
     characters, at any base size. See
     docs/superpowers/specs/2026-08-15-prose-typography-evidence.md */
  --file-line-width: calc(var(--font-text-size) * 34);
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 tests/test_prose_typography.py`
Expected: PASS — `ok measure calc(var(--font-text-size) * 34) = 70.6 characters per line, inside 55-75`, exit 0.

- [ ] **Step 6: Wire it into lint**

In `tests/lint.sh`, after the `== midori-timer unit tests ==` block, add:

```sh
echo "== prose typography =="
if python3 tests/test_prose_typography.py; then :; else FAIL=1; fi
```

- [ ] **Step 7: Verify in the app**

```bash
sh tests/lint.sh
sh obsidian/install-obsidian.sh
```

Open a real note. Confirm: the column is narrower, the dot grid still runs edge
to edge (it is painted on the scroller, not the sizer, so it must be
unaffected), and nothing has moved vertically.

- [ ] **Step 8: Commit**

```bash
git add obsidian/theme.css tests/test_prose_typography.py tests/prose_harness.py tests/lint.sh
git commit -m "theme: set the measure in em, inside the preference band

Obsidian's 700px default is ~91 characters per line with Midori Text at
a 16px base. The 45-75 rule has no experiment behind it, so this is not
a correction toward a finding; it is the preference side of the real
speed/preference split. In em rather than px because cpl depends on both
width and size, and the theme now ships to readers whose text-size
slider is not where mine is."
```

---

### Task 2: `--midori-row` as the single source of truth

Twenty-odd rules hardcode `24px`, and so does the dot grid. Before the grid can
follow anything, it has to be one number. **This task changes no pixel** — it
is a pure refactor, and the rendered check exists to prove exactly that.

**Files:**
- Modify: `obsidian/theme.css` (root variable block; then every `line-height: 24px`, the `margin-block` multiples, and `background-size` at 402)
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Consumes: `theme_var()` from Task 1.
- Produces: `--midori-row`, consumed by Tasks 3 and 4.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_prose_typography.py`, and add `test_row_is_one_number()`
to the `__main__` block:

```python
def test_row_is_one_number():
    raw = theme_var("--midori-row")
    if raw is None:
        bad("--midori-row is not defined; the grid is still a literal in every rule")
        return
    ok(f"--midori-row = {raw}")

    # The refactor is only real if the literals are gone. Comments are stripped
    # first: the file explains the grid in prose and those mentions are fine.
    body = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)
    stray = re.findall(r"line-height:\s*24px", body)
    if stray:
        bad(f"{len(stray)} rules still hardcode line-height: 24px")
    else:
        ok("no rule hardcodes line-height: 24px")

    if re.search(r"background-size:\s*24px\s+24px", body):
        bad("the dot grid still hardcodes 24px 24px")
    else:
        ok("the dot grid is expressed in --midori-row")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: FAIL — `--midori-row is not defined; the grid is still a literal in every rule`.

- [ ] **Step 3: Capture the before-state for the no-change check**

```bash
python3 tests/prose_harness.py /tmp/claude-501/prose.html
python3 -m http.server 8777 --directory /tmp/claude-501 &
```

In the browser, on the served page, record every line-box top in the first
block — this exact array is what Step 6 compares against:

```js
JSON.stringify([...document.querySelectorAll('.markdown-preview-sizer p')]
  .map(p => Math.round(p.getBoundingClientRect().top * 100) / 100))
```

- [ ] **Step 4: Define the row and replace the literals**

In the root variable block, above `--dotgrid-offset-y`:

```css
  /* THE GRID ROW. 24px at a 16px base is a leading of exactly 1.50 — above the
     CSS ~1.2 floor that Rello et al. actually measured (their harmful
     condition was CSS ~0.96; the "1.0" in that paper is Firefox's default of
     120%), and on WCAG 1.4.8's 1.5, which is a policy floor and not an
     experimental result. No study distinguishes 1.4 from 1.5 from 1.6, so this
     number is defensible rather than optimal, and it is not going to move on
     evidence. It moves, if at all, because the READER's base size moved. */
  --midori-row: 24px;
```

Then replace, throughout the file:
- every `line-height: 24px` → `line-height: var(--midori-row)`
- every `line-height: 48px` on a heading or the inline title → `line-height: calc(var(--midori-row) * 2)`
- `margin-block: 0 24px` → `margin-block: 0 var(--midori-row)`, and `margin-block: 24px 0` → `margin-block: var(--midori-row) 0`
- `background-size: 24px 24px` → `background-size: var(--midori-row) var(--midori-row)`

Leave every *prose mention* of 24px in the comments alone — they are the
explanation, and the test strips comments before looking.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 tests/test_prose_typography.py`
Expected: PASS on all three row assertions.

- [ ] **Step 6: Prove nothing moved**

Regenerate the harness, reload, and re-run the Step 3 snippet. **Every value
must be identical.** If any differs, a literal was replaced with the wrong
expression — find it before continuing; this task's entire value is that it is
a no-op.

- [ ] **Step 7: Commit**

```bash
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "theme: name the 24px grid row --midori-row

Pure refactor, no rendered change: every line-box top in the harness is
identical before and after. The grid was a literal in twenty-odd rules
and in the dot-grid background-size, which made it impossible to change
in one place and impossible to make follow anything."
```

---

### Task 3: The row follows the reader's text size

The theme assumes a 15–16px base. At 18px the grid is 1.33 leading — above the
measured harm floor, under the WCAG policy floor — and the reader who did that
has no idea the theme had an opinion. **This is the change that matters for
shipping to other people**, and it is the risky one, because the dot grid's
vertical phase was measured against a 24px row.

**Files:**
- Modify: `obsidian/theme.css` (`--midori-row`, `--dotgrid-offset-y`)
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Consumes: `--midori-row` (Task 2), `BASES`, `theme_var()`.
- Produces: a `--midori-row` that is a function of `--font-text-size`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_prose_typography.py` and register in `__main__`:

```python
def row_px(base):
    """Mirror of the CSS: round(up, max(24px, base * 1.5), 1px)."""
    return max(24, math.ceil(base * 1.5))


def test_leading_holds_across_the_slider():
    raw = theme_var("--midori-row")
    if raw is None or "--font-text-size" not in raw:
        bad(f"--midori-row is {raw!r}: fixed, so leading falls below 1.5 "
            "as soon as the reader raises their text size")
        return
    # A LOCAL flag, not the global FAIL: an unrelated earlier failure must not
    # silently swallow this test's own ok line.
    bad_here = False
    worst = min(((base, row_px(base) / base) for base in BASES), key=lambda p: p[1])
    for base in BASES:
        ratio = row_px(base) / base
        if ratio < 1.5 - 1e-9:
            bad(f"base {base}px gives leading {ratio:.2f}, under the 1.5 policy floor")
            bad_here = True
    if not bad_here:
        ok(f"leading >= 1.5 across {BASES[0]}-{BASES[-1]}px "
           f"(worst {worst[1]:.2f} at {worst[0]}px)")


def test_row_stays_whole_pixels():
    """The guarantee is in the CSS, not in row_px().

    row_px() returns whole pixels by construction, so asserting on it proves
    nothing. What can actually regress is the stylesheet dropping the rounding
    — `max(24px, var(--font-text-size) * 1.5)` alone is 25.5px at a 17px base,
    and a fractional row puts the dot lattice on half pixels.
    """
    raw = theme_var("--midori-row") or ""
    if re.search(r"round\(\s*up\s*,.*,\s*1px\s*\)", raw):
        ok("the row is rounded up to whole pixels")
    else:
        bad(f"--midori-row is {raw!r}: no round(..., 1px), so a base size that "
            "is not a multiple of 2 gives a fractional row and blurs the dots")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: FAIL — `--midori-row is '24px': fixed, so leading falls below 1.5 as soon as the reader raises their text size`.

- [ ] **Step 3: Make the row a function of the base**

Replace the `--midori-row` declaration from Task 2 with:

```css
  /* Two declarations, and the first is the fallback: a build whose engine
     lacks CSS round() ignores the second and keeps the theme's historical
     row, rather than inheriting an invalid value and collapsing the grid. */
  --midori-row: 24px;
  --midori-row: round(up, max(24px, var(--font-text-size) * 1.5), 1px);
```

`max()` keeps small bases on the historical 24px row — at 14px, 1.5x would be
21px and at the 10px floor it would be 15px, which is a tighter page than this theme has ever been and is not what
someone reducing their text size is asking for. `round(up, ..., 1px)` keeps the
dot lattice on whole pixels.

**Already verified in a browser**, so the implementer is not testing whether
the CSS is real — applied through `line-height: var(--midori-row)` and read
back from `getComputedStyle`, this expression computes 24, 24, 24, 26, 27, 29,
30px at bases 14–20, which matches `row_px()` exactly. Step 7's in-app check is
what confirms Obsidian's own engine agrees.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 tests/test_prose_typography.py`
Expected: PASS — `ok leading >= 1.5 across 10-30px (worst 1.50 at 16px)`, and
`ok every row is a whole number of pixels`.

- [ ] **Step 5: Re-derive the dot-grid offset, and MEASURE it rather than trusting it**

`--dotgrid-offset-y: 10.98px` was measured against a 24px row. The file's own
comment says to re-tune it by measuring the baseline-to-dot delta, never by
deriving one situation's value from another's. Both halves are done here: the
derivation gives the candidate, the measurement decides whether it is kept.

Under symmetric font metrics every baseline sits at the centre of its line box,
so growing the row by `R - 24` moves each baseline down by half that. Replace
the declaration with:

```css
  /* Was a constant measured against a 24px row. With a row that follows the
     reader's text size, the first baseline moves by half the row's growth —
     the aliases seat every baseline at L/2 — so the constant becomes an
     offset from the historical row. VERIFY BY MEASURING after changing this;
     see the plan's baseline-vs-dot check. */
  --dotgrid-offset-y: calc(10.98px + (var(--midori-row) - 24px) / 2);
```

Then measure, on the served harness, at base sizes 15, 16, 17, 18 and 20 (set
each with `document.documentElement.style.setProperty('--font-text-size', '18px')`):

```js
(() => {
  const row = parseFloat(getComputedStyle(document.body).getPropertyValue('--midori-row'));
  const off = parseFloat(getComputedStyle(document.body).getPropertyValue('--dotgrid-offset-y'));
  const p = document.querySelector('.markdown-preview-sizer p');
  const box = p.getBoundingClientRect();
  const baseline = box.top + row / 2;               // symmetric metrics: baseline at L/2
  const phase = ((baseline - off) % row + row) % row;
  return { row, off, phase: Math.round(phase * 100) / 100,
           aligned: Math.min(phase, row - phase) < 0.5 };
})()
```

**Gate:** `aligned` must be true at every base size tested.

- [ ] **Step 6: If the gate fails, stop and take the documented fallback**

Do not tune the constant per base size — that is the per-device magic number
this theme's history is made of. Instead revert Step 3 and Step 5 to the fixed
`--midori-row: 24px` and `10.98px`, add to the variable's comment:

```css
  /* SUPPORTED BASE RANGE: 15-16px. Above that the grid is tighter than 1.5
     (17px -> 1.41, 18px -> 1.33) and the dots drift off the baseline. Making
     the row follow --font-text-size was tried and the dot phase did not
     survive it; the measurement is in the plan. */
```

then continue to Task 4 having recorded the failure. A documented limitation is
a result; a grid that is subtly off for everyone but me is not.

- [ ] **Step 7: Verify in the app at two sizes**

```bash
sh tests/lint.sh
sh obsidian/install-obsidian.sh
```

In Obsidian, set Settings → Appearance → Font size to 18, look at a note, then
set it back to 16. The dots must sit on the baselines at both.

- [ ] **Step 8: Commit**

```bash
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "theme: let the grid row follow the reader's text size

The 24px row is 1.50 leading at a 16px base and 1.33 at 18px, so the
theme was quietly correct at one setting on the slider and drifting at
the others. round(up, max(24px, base * 1.5), 1px) holds >= 1.5 across
14-20px on whole pixels, and the dot offset becomes an offset from the
historical row rather than a constant measured against it. Baseline-vs-
dot phase measured at 15, 16, 17, 18 and 20px."
```

---

### Task 4: The heading ladder, optically

Headings are Spectral; body is M PLUS 1p; Spectral's x-height is `0.450` against
`0.520`. Obsidian's real h4 of `1.188em` (read from app.css, not assumed)
therefore renders **1.03x body text to the eye** — an h4 is, optically, body
copy in a different colour. The em ladder the app intends is not the ladder the
eye receives.

**Files:**
- Modify: `obsidian/theme.css` (new block beside the heading rules at ~1603)
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Consumes: `X_MPLUS`, `X_SPECTRAL`, `theme_var()`, `--midori-row`.

- [ ] **Step 1: Write the failing test**

Append and register:

```python
# Obsidian's defaults, in em of the base size.
OBSIDIAN_H = {1: 1.618, 2: 1.462, 3: 1.318, 4: 1.188}


def test_heading_ladder_is_optical():
    """Each heading should be as much BIGGER TO THE EYE as its em says.

    Spectral carries 0.450 of x-height per em against Midori Text's 0.520, so
    a heading set at the app's default em is 13.5% smaller optically than the
    ladder claims. The test is on x-height ratio, not on em.
    """
    for level, default in OBSIDIAN_H.items():
        raw = theme_var(f"--h{level}-size")
        em = em_value(raw)
        if em is None:
            bad(f"--h{level}-size is {raw!r}; at Obsidian's default {default}em "
                f"the visual step is {default * X_SPECTRAL / X_MPLUS:.2f}x body, "
                f"not {default:.2f}x")
            continue
        visual = em * X_SPECTRAL / X_MPLUS
        if abs(visual - default) <= 0.02:
            ok(f"h{level} {raw} reads {visual:.2f}x body (intended {default:.2f}x)")
        else:
            bad(f"h{level} {raw} reads {visual:.2f}x body, intended {default:.2f}x")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: four failures, the first being
`--h1-size is None; at Obsidian's default 1.618em the visual step is 1.40x body, not 1.62x`.

- [ ] **Step 3: Set the compensated sizes**

Each is the Obsidian default multiplied by `0.520 / 0.450 = 1.1556`. Add beside
the existing heading rules (~line 1603):

```css
/* HEADING SIZES COMPENSATED FOR SPECTRAL'S X-HEIGHT.

   Headings are "Midori Display" (Spectral, x-height 0.450em); body is
   "Midori Text" (M PLUS 1p, 0.520em). Apparent size follows x-height, not em
   — which is why every print-size result in the vision literature is stated in
   x-height rather than points. Set at Obsidian's default em ladder, an h4
   lands 1.03x body to the eye instead of the 1.19x it claims, and the bottom
   of the hierarchy stops reading as hierarchy.

   x 1.1556 = 0.520 / 0.450 restores the intended ladder optically. The em
   numbers now look large; that is the correction, not a mistake.

   Only h1-h4 — h5/h6 are Midori Text and already correct, and are uppercase,
   where cap-height rather than x-height carries the size.

   The 2-row line box absorbs this: h1 at 1.870em is 29.9px at a 16px base
   against a 48px box, and the box is now calc(var(--midori-row) * 2), so the
   headroom scales with the reader's text size rather than being spent by it. */
body {
  --h1-size: 1.870em;   /* app.css 1.618 x 1.1556 */
  --h2-size: 1.690em;   /* app.css 1.462 */
  --h3-size: 1.523em;   /* app.css 1.318 */
  --h4-size: 1.373em;   /* app.css 1.188 */
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 tests/test_prose_typography.py`
Expected: PASS — e.g. `ok h1 1.870em reads 1.62x body (intended 1.62x)`.

- [ ] **Step 5: Prove the line boxes still land on the grid**

On the served harness, with headings present, at base sizes 16 and 20:

```js
[...document.querySelectorAll('h1,h2,h3,h4')].map(h => {
  const row = parseFloat(getComputedStyle(document.body).getPropertyValue('--midori-row'));
  const box = h.getBoundingClientRect().height;
  return { tag: h.tagName, box, rows: box / row, whole: Math.abs(box / row - Math.round(box / row)) < 0.02 };
})
```

**Gate:** `whole` true for every heading. A heading's line box is
`max(strut, natural box)`, so if a compensated size outgrows its 2-row strut the
box silently becomes fractional and every line below it leaves the grid. If one
fails, raise that heading's box to 3 rows rather than shrinking the size.

- [ ] **Step 6: Verify in the app**

```bash
sh tests/lint.sh
sh obsidian/install-obsidian.sh
```

Open a note with h1–h4. The hierarchy should read as evenly stepped; an h4
should now be unmistakably a heading.

- [ ] **Step 7: Commit**

```bash
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "theme: compensate heading sizes for Spectral's x-height

Apparent size follows x-height, not em — which is why the vision
literature states print size that way. Spectral carries 0.450 per em
against Midori Text's 0.520, so at Obsidian's real ladder (1.618 down to
1.188, read out of app.css) an h4 rendered 1.03x body to the eye while
claiming 1.19x, and the bottom of the hierarchy stopped reading as
hierarchy at all. x1.1556 restores the ladder
optically; line boxes re-measured against the grid at 16 and 20px."
```

---

### Task 4b: Move heading typography onto the variables Obsidian already has

Not a visual change — a **contract** change, and the reason the schema was
researched. app.css has 36 heading variables and consumes every one of them
(`font-family: var(--h1-font)`, `font-weight: var(--h1-weight)`,
`letter-spacing: var(--h1-letter-spacing)`). The theme currently sets six of
them — the colours — and reaches past the rest with element selectors, which is
why it needs *two* rules per level (`.markdown-preview-view h1` for Reading
view and `.HyperMD-header-1` for Live Preview), a separate `--inline-title-font`
declaration, and an `!important` on `.inline-title`.

**Files:**
- Modify: `obsidian/theme.css` (~1603–1690: the heading font rules, the `--inline-title-font` block, the `.inline-title` rule)

**Interfaces:**
- Consumes: `--h1-size`…`--h4-size` from Task 4.
- Produces: `--hN-font`, `--hN-weight`, `--hN-letter-spacing` set on `body`.

- [ ] **Step 1: Confirm the variables are consumed, in this Obsidian version**

```bash
python3 obsidian/dump-app-css.py /tmp/midori-appcss
grep -o -- "--h[1-4]-\(font\|weight\|letter-spacing\|size\)" /tmp/midori-appcss/app.css | sort | uniq -c
```

Expected: each name appears at least twice — once declared, once consumed. If
`--hN-letter-spacing` appears only as a consumer with no default, that is
normal and it still works.

- [ ] **Step 2: Replace the element rules with variable declarations**

Delete the `.markdown-preview-view h1, .HyperMD-header-1 { … }` pairs for h1–h4
and the `body { --inline-title-font: … }` block, and declare instead:

```css
/* HEADINGS THROUGH OBSIDIAN'S OWN VARIABLES, NOT AROUND THEM.

   app.css already reads --hN-font, --hN-weight and --hN-letter-spacing on
   every heading, in BOTH panes: .HyperMD-header-N in Live Preview and h1-h6 in
   Reading view are the same declaration block. Setting the variables therefore
   replaces two rules per level with one, and it is the supported path rather
   than a specificity fight that has to be re-won every time app.css changes.

   The inline title comes free: app.css defaults --inline-title-font,
   --inline-title-size and --inline-title-weight to their --h1-* counterparts,
   so the title follows h1 without a rule of its own. */
body {
  --h1-font: "Midori Display", ui-serif, Georgia, serif;
  --h2-font: "Midori Display", ui-serif, Georgia, serif;
  --h3-font: "Midori Display", ui-serif, Georgia, serif;
  --h4-font: "Midori Display", ui-serif, Georgia, serif;
  --h1-weight: 600;
  --h2-weight: 600;
  --h3-weight: 500;
  --h4-weight: 500;
  --h1-letter-spacing: -0.01em;
  --h2-letter-spacing: -0.01em;
}
```

- [ ] **Step 3: Try removing the `!important` on the inline title**

The existing `.inline-title { font-family: var(--inline-title-font) !important }`
was added because a per-vault Font override in Settings → Appearance drives the
title off `--font-text` and a plain rule lost. With `--h1-font` set, the title
takes its face from the variable chain instead. Remove the `!important`, then
**verify with a vault font override actually set** — Settings → Appearance →
Font → pick any face. If the title reverts to that face, restore the
`!important` and leave the existing comment explaining why.

- [ ] **Step 4: Verify both panes and the title**

```bash
sh tests/lint.sh && sh obsidian/install-obsidian.sh
```

Open a note with h1–h4 in Live Preview, switch to Reading view, and check the
inline title. All three must be Spectral at the compensated sizes. This is the
step that catches a variable name typo, because a wrong name fails silently to
`inherit` rather than erroring.

- [ ] **Step 5: Commit**

```bash
git add obsidian/theme.css
git commit -m "theme: set headings through Obsidian's own --hN-* variables

app.css consumes 36 heading variables and the theme was setting six of
them, reaching past the rest with element selectors -- which is why it
carried two rules per level, one for .HyperMD-header-N and one for h1-h6,
plus a separate --inline-title-font and an !important. The variables are
read in both panes from a single app.css declaration block, so setting
them replaces the pairs with one block and the inline title follows h1
for free."
```

---

### Task 5: Confirm the body text holds at 1×

The primary display here is an 800×340mm panel at 2560×1080 running 1×, i.e.
81 ppi — the regime where a WCAG ratio overstates legibility, because only ~9%
of a glyph's pixels carry full ink. Nothing in Tasks 1–4 was a colour change, so
**this is a verification task**, and it may correctly end with no code change.

**Files:**
- Modify: `README.md` only if the measurement finds something.

- [ ] **Step 1: Render the writing surface at deviceScaleFactor 1**

Serve the harness and load it with the browser at a 1× device scale, then
screenshot the prose block at its natural size (no zoom, no retina scaling).

- [ ] **Step 2: Measure ink coverage of body text**

Project every pixel in the prose region onto the background→foreground axis and
report the distribution. Paper is `--background-primary: #f3f1eb`, body ink is
`--text-normal: #33302b`:

```python
BG = np.array([243., 241., 236.])
FG = np.array([51., 48., 43.])
d = FG - BG
cov = ((reg - BG) @ d) / (d @ d)
res = np.linalg.norm((reg - BG) - np.outer(cov, d), axis=1)
glyph = cov[(cov > 0.10) & (res < 10)]
print(glyph.mean(), np.median(glyph), np.percentile(glyph, 90), (glyph >= 0.9).mean())
```

- [ ] **Step 3: Judge by the p90 pixel, not the nominal ratio**

Nominal contrast here is ~11:1, which is not the question. Compute the ratio at
the p90-coverage colour and compare against the 5–8:1 body-text budget.

**Gate:** p90 ratio ≥ 5:1. If it clears, record the number and change nothing —
Task 1's narrower measure and Task 3's larger rows both help legibility and
neither touched a colour. If it fails, the lever is weight or lightness, never
saturation.

- [ ] **Step 4: Commit only if something changed**

If the measurement passes, there is nothing to commit; note the number in
Task 6's README bullet. If it fails, fix and commit with the measured
before/after ratios in the message.

---

### Task 6: Documentation, version, install

**Files:**
- Modify: `README.md` (findings bullets, in the established voice)
- Modify: `obsidian/manifest.json` (version)
- Modify: `docs/superpowers/specs/2026-08-15-prose-typography-evidence.md` (status line)

- [ ] **Step 1: Add the findings bullets to README.md**

In the Obsidian findings list, add one bullet per shipped change. Each must say
what was believed, what was measured, and what changed — matching the existing
entries. Required content:

- **The measure was outside every band and the band has no experiment behind it.** ~91 cpl at a 16px base; the rule traces to Spencer asserting and Rayner & Pollatsek deducing from print; what is real is the speed/preference split, and a writing surface takes the preference side. In `em`, so it survives the reader's text-size slider.
- **A grid tuned to one base size is tuned to one person.** 24px is exactly 1.5 leading at 16px and 1.33 at 18px. The row now follows `--font-text-size`; the dot offset became an offset from the historical row rather than a constant measured against it, and the baseline-vs-dot phase was measured at five base sizes.
- **Apparent size follows x-height, not em.** Spectral 0.450 against M PLUS 1p 0.520 meant an h4 read 1.10× body while claiming 1.27×.
- **What was deliberately not changed**, and why: leading (no experiment separates 1.4/1.5/1.6, and the much-cited Chaparro result is a null), letter-spacing, serif-vs-sans (unresolved, not a proven null — the claim that it is settled was itself refuted), and anything about the caret or focus mode (no evidence exists at all).

- [ ] **Step 2: Bump the theme version**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('obsidian/manifest.json')
m = json.loads(p.read_text())
major, minor, patch = m['version'].split('.')
m['version'] = f"{major}.{int(minor) + 1}.0"
p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
print(m['version'])
PY
```

- [ ] **Step 3: Mark the evidence doc as acted upon**

Change its status line to:

```markdown
**Status:** evidence review — acted on in `docs/superpowers/plans/2026-08-15-prose-writing-surface.md`
```

- [ ] **Step 4: Full verification**

```bash
sh tests/lint.sh
sh obsidian/install-obsidian.sh
```

Expected: `LINT: all green`, including `== prose typography ==`, and the
installer reporting all three vaults.

- [ ] **Step 5: Commit**

```bash
git add README.md obsidian/manifest.json docs/superpowers/specs/2026-08-15-prose-typography-evidence.md
git commit -m "docs: record the prose typography changes and what was left alone"
```

---

## Explicitly out of scope

Named because each is a plausible next idea that the evidence does not support,
and re-litigating them costs more than writing them down once.

- **Letter-spacing / tracking on body text.** No surviving evidence, on screen or off.
- **Serif vs sans for the body face.** Unresolved by citable evidence — the claim that it is a settled null was itself refuted 0–3. Not a reason to switch, and not a reason to defend the current choice on legibility grounds.
- **Changing the leading ratio.** Nothing distinguishes 1.4 from 1.5 from 1.6.
- **Raising the base size.** The recommendation to do so came from arithmetic on a Retina laptop; on this 81 ppi panel 16px clears the 0.2° critical-print-size floor out to ~72cm. The base is the reader's setting, and Task 3 makes the theme follow it rather than argue with it.
- **Typewriter scrolling, focus mode, paragraph-indent instead of blank line, centred column, caret size.** No evidence exists in either direction; they are design choices, and [[nothing-enters-the-writing-surface-unbidden]] governs them, not this plan.
- **Revision-specific leading.** The one genuinely decision-relevant unknown — whether extra leading is *costly* when the eye hops between lines to revise — and untested by anyone. Worth an experiment of our own someday; not a stylesheet change today.
