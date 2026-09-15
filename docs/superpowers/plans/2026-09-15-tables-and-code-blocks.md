# Midori Tables and Code Blocks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tables that are readable and hand the grid back intact, and code blocks whose text never runs into the edge of its own background — in both live preview and reading view.

**Architecture:** All rendering changes are CSS in the single file `obsidian/theme.css`, added to or replacing the existing Tables and Code-blocks regions. Two guards land beside them: a stdlib static test that reads the stylesheet (wired into `tests/lint.sh`), and a rendered checker driven over CDP against a running Obsidian (deliberately not in lint). The rendered checker is built FIRST, against the unfixed theme, where it must fail naming the known defects — that is its sabotage proof, earned rather than staged.

**Tech Stack:** CSS (custom properties, `color-mix()`, `:has()`, container query units), Python 3 stdlib for the static test, Python 3 + `websocket-client` in a throwaway venv for the rendered checker, POSIX `sh` for the lint wiring.

**Spec:** `docs/superpowers/specs/2026-09-15-tables-and-code-blocks-design.md`

## Global Constraints

- **Comments are the deliverable.** Never delete a comment recording a measurement, a rejected alternative, or a warning. Correcting a false one is required, and the correction must say what was wrong and why it was believed (`CLAUDE.md`).
- **A passing check is evidence only if you know what it examined.** Print counts, fail on an empty input set, and sabotage-prove every new guard before trusting it.
- **Run `sh tests/lint.sh` before every commit.** It takes ~60s; that is normal.
- **Never run an installer to test a change to it.** Use `tests/dryrun-installers.sh`. No task in this plan needs to run `install.sh`.
- **`tests/` is stdlib-only** for anything wired into `tests/lint.sh`. `python3 -c "import yaml"` fails on the interpreter lint uses. The rendered checker is NOT in lint and may import `websocket`.
- **Shell is POSIX `sh`**, not bash.
- **Every rendered measurement in this plan was taken on:** Obsidian 1.13.7, Mud & Silicon vault, `Midori Block Reference.md`, base 16px, `--midori-set-measure: 85`, row 24px, prose column 655.2px, pane 1428px, window 1728×1084. Re-deriving on another machine will give different absolute numbers; the invariants (whole rows, ≥16px gap) are what the checks assert.
- **End every commit message with:**
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_013rhw75dhAvgnscSB9GHixV
  ```

---

## Measured mechanisms this plan is built on

Each was measured in the running app over CDP, applied and then reverted. Do not re-derive these to start; do re-measure them as the per-task verification steps say.

| # | Mechanism | Measurement |
|---|-----------|-------------|
| 1 | **The 2px.** Four Obsidian variables (`--table-header-border-width`, `--table-row-last-border-width`, `--table-column-first-border-width`, `--table-column-last-border-width`), all `1px`, feed app.css rules (`thead tr > th`, `tbody tr:last-child > td`, `td:first-child`, `td:last-child`) that out-specify the theme's `border-width: 0` | Five-row table **122px** (wanted 120) in live preview **and 122px in reading view**; dense four-column table 410 (wanted 408). Setting the four to `0px` gave exactly 120 and 408 in both views. |
| 2 | **Pane width in CSS.** `container-type: inline-size` on each view's scroller, read with `100cqi` | `100cqi` = **1364px** with the container on `.cm-scroller` (live preview) and **1364px** with it on `.markdown-preview-view` (reading view) — the 1428px pane less 32px of scroller padding each side — against **1728px** (the window) with no container. Layout byte-identical before/during/after in both views; scrolling moved exactly the 120px asked of it; a `position: fixed` child anchored at 300/40 with and without the container, because `.workspace-leaf`'s `contain: strict` is already its containing block. |
| 3 | **Reading-view breakout does not clip.** The block wrapper is `div.el-table`, the sizer's direct child, which already carries `overflow-x: auto` | Widening `.el-table` to 1040px centred it at 494→1534 inside the 1428px view (grew 384.8px), cells 101.2 → 216.1px, height unchanged, no sideways scroll on the view (1428/1428) or document (1728/1728), both far edges hit-tested as `th`. The inner `table` is content-sized (487.7 of a 655.2 column) and must be told to fill the new width or the widening is invisible. |
| 4 | **Air.** A blank `.cm-line` given `line-height: var(--midori-row)` through `:has()`, which looks forward | 0 → 24px above and below both code blocks and table widgets; block height, corner radius and background untouched. |
| 5 | **Hanging indent.** `padding-inline-start: calc(16px + 2ch)` + `text-indent: -2ch` on `.cm-line.HyperMD-codeblock:not(.HyperMD-list-line)` | First line at 16px, continuations at 30px (2ch = 14px in the code face), right gap ≥21px, every line still a whole number of rows. **`:not(.HyperMD-list-line)` is load-bearing:** app.css's own selector carries it, so without it the padding loses the specificity contest — measured, the padding never applied (computed 16px) while `text-indent` did, moving the FIRST line left to 2px and leaving continuations at 16. |

---

## File Structure

| File | Responsibility |
|------|----------------|
| `obsidian/theme.css` | Every rendering change. Two regions: **Tables** (currently lines 1886–1946) and **Code blocks** (currently lines 1795–1835), plus one new `body` token block for each. |
| `tests/check_rendered_blocks.py` | **New.** The instrument. Measures tables and code blocks in the running app, in both views, on seven named axes. Selects its window by content and refuses a window that cannot show the defect. Not in lint. |
| `tests/test_block_geometry.py` | **New.** Stdlib static guards on the stylesheet, reusing `tests/test_prose_typography.py`'s documented helpers by import. Wired into `tests/lint.sh`. |
| `tests/lint.sh` | One new section calling `tests/test_block_geometry.py`. |

Why a new static test file rather than growing `test_prose_typography.py` (already 1364 lines): tables and code blocks are blocks, not prose, and that file is at the size where focus starts to pay. Why import its helpers instead of copying them: `rules()` carries a documented performance trap (the obvious rule regex is polynomial and does not finish against this 90KB stylesheet) and `theme_var()` carries a documented correctness trap (comments in this file quote whole CSS declarations, so a guard that scans unstripped text can be satisfied by prose discussing the real thing). Copying either would fork those lessons.

---

### Task 1: The instrument — a rendered checker that fails on the known defects

**Files:**
- Create: `tests/check_rendered_blocks.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the command `/tmp/cdpenv/bin/python tests/check_rendered_blocks.py`, which prints one line per axis and exits non-zero if any axis fails. Every later task re-runs it and names the axis it turns green. Axis names, used verbatim in later tasks: `table-rows`, `code-rows`, `paragraph-phase`, `code-right-gap`, `label-overlap`, `cell-opacity`, `breakout`.

- [ ] **Step 1: Start Obsidian with the debugging port and open the reference note**

```bash
pgrep -x Obsidian >/dev/null || open -a Obsidian --args --remote-debugging-port=9222
# Wait for the port, rather than guessing at a sleep:
for i in $(seq 60); do curl -s --max-time 2 http://127.0.0.1:9222/json/version >/dev/null && break; sleep 1; done
curl -s http://127.0.0.1:9222/json | python3 -c 'import json,sys
for t in json.load(sys.stdin):
    if t["type"] == "page": print(" ", t["title"])'
```

Open `Midori Block Reference.md` (in the `Mud & Silicon` vault, at
`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Mud & Silicon/`) in
**live preview**, and scroll so a table and a fenced code block are both on
screen. CodeMirror virtualizes: a block that has scrolled away is not in the
DOM, and the checker refuses a window that cannot show the defect.

- [ ] **Step 2: Create the venv the checker needs**

```bash
python3 -m venv /tmp/cdpenv && /tmp/cdpenv/bin/pip install -q websocket-client
```

- [ ] **Step 3: Write the checker**

Create `tests/check_rendered_blocks.py`:

```python
#!/usr/bin/env python3
"""Measure tables and code blocks in the RUNNING app, in BOTH views.

WHY THIS EXISTS. A static test reads the stylesheet; it cannot see what the
browser laid out. This repo has paid for that difference more than once -- a
16-of-16-green suite beside a Live Preview with 6 of 31 lines off the row, and
a table rule that lost a specificity contest while its guard stayed green. The
defects this measures are all of that kind: Obsidian re-adds table borders from
variables the theme does not set, and code text lands 2.2px from the edge of
its own background. Neither is visible in the source.

WHAT IT REFUSES. A window with no rendered table widget and no rendered code
line cannot show any of these defects, so it is a hard error rather than a
quiet pass -- the failure mode of check_rendered_grid.py's first live run,
which graded a twelve-line note and printed a confident all-clear.

Run:
    open -a Obsidian --args --remote-debugging-port=9222
    python3 -m venv /tmp/cdpenv && /tmp/cdpenv/bin/pip install websocket-client
    /tmp/cdpenv/bin/python tests/check_rendered_blocks.py

Open a note with a table and a fenced code block in Live Preview first, and
scroll so both are on screen: CodeMirror only keeps visible lines in the DOM.

Not stdlib and deliberately not wired into tests/lint.sh: it imports websocket
and needs a running app to talk to, the same split as check_rendered_grid.py.
"""
import json
import sys
import urllib.request

import websocket   # not stdlib; see the module docstring

TOL = 0.5        # px; half a pixel of rounding slack on a whole-row assertion
MIN_GAP = 16.0   # px; the spec's floor for code text against its background


def evaluate(ws, expr, await_promise=False, _id=[0]):
    _id[0] += 1
    ws.send(json.dumps({"id": _id[0], "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True,
                                   "awaitPromise": await_promise}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == _id[0]:
            res = msg.get("result", {})
            if "exceptionDetails" in res:
                sys.exit(f"page error: {res['exceptionDetails'].get('text')}")
            return res["result"].get("value")


def pick_window():
    """The window with the most rendered blocks, chosen by CONTENT not title.

    Titles shift with focus, and CDP's /json order is not "the window the
    operator meant". Ranking by blocks and REFUSING a window with none is the
    part that matters: every axis below measures a table or a code block, so a
    window without either would print a clean sheet it did not earn.
    """
    targets = [t for t in json.load(urllib.request.urlopen("http://localhost:9222/json"))
               if t.get("type") == "page"]
    if not targets:
        sys.exit("no page target; is Obsidian running with "
                 "--remote-debugging-port=9222?")
    rows = []
    for t in targets:
        ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=40,
                                         suppress_origin=True)
        try:
            title = evaluate(ws, "document.title")
            tables = evaluate(ws, "document.querySelectorAll('.cm-table-widget').length")
            code = evaluate(ws, "document.querySelectorAll("
                                "'.cm-line.HyperMD-codeblock').length")
        finally:
            ws.close()
        rows.append((tables, code, title, t))

    print(f"{'tables':>6} {'code':>5}  title")
    for tables, code, title, _ in sorted(rows, key=lambda r: (-r[0], -r[1])):
        print(f"{tables:>6} {code:>5}  {title}")
    print()

    tables, code, title, target = max(rows, key=lambda r: (min(r[0], 1) + min(r[1], 1),
                                                           r[0] + r[1]))
    if not tables or not code:
        sys.exit(f"selected window {title!r} has {tables} rendered table widget(s) "
                 f"and {code} rendered code line(s); both are required. Open a note "
                 "with a table AND a fenced code block in Live Preview and scroll "
                 "so both are on screen -- CodeMirror only keeps visible lines in "
                 "the DOM, so a window that cannot show the defect must not be "
                 "allowed to pass.")
    print(f"measuring: {title!r} ({tables} tables, {code} code lines)\n")
    return websocket.create_connection(target["webSocketDebuggerUrl"],
                                       timeout=40, suppress_origin=True)


# The row is a token stream until a real property consumes it, so every probe
# reads a consumer rather than getPropertyValue -- the same reason
# check_rendered_grid.py builds a hidden div.
LIVE = r"""
(() => {
  const view = document.querySelector('.markdown-source-view.mod-cm6');
  if (!view) return {error: 'no live preview view'};
  const p = document.createElement('div');
  p.style.cssText = 'position:absolute;visibility:hidden;line-height:var(--midori-row)';
  view.appendChild(p);
  const row = parseFloat(getComputedStyle(p).lineHeight);
  p.remove();
  const content = view.querySelector('.cm-content');
  const contentTop = content.getBoundingClientRect().top;
  const kids = [...content.children];
  const textRects = (el) => { const r = document.createRange(); r.selectNodeContents(el);
    return [...r.getClientRects()].filter((x) => x.width > 0 && x.height > 0); };
  const off = (h) => +Math.min(h % row, row - (h % row)).toFixed(2);
  const phase = (el) => { const d = (el.getBoundingClientRect().top - contentTop) % row;
    return +Math.min(Math.abs(d), Math.abs(row - d)).toFixed(2); };

  // Tables: the widget is one element, so its own box is the block.
  const tables = kids.filter((el) => el.classList.contains('cm-table-widget')).map((el) => {
    const b = el.getBoundingClientRect(), after = el.nextElementSibling;
    const cell = el.querySelector('td'), head = el.querySelector('th');
    const alpha = (c) => { const m = /rgba?\(([^)]+)\)/.exec(c);
      return m ? (m[1].split(',').length > 3 ? parseFloat(m[1].split(',')[3]) : 1) : null; };
    return {h: +b.height.toFixed(2), rows: +(b.height / row).toFixed(3), off: off(b.height),
            width: +b.width.toFixed(1), left: +b.left.toFixed(1), right: +b.right.toFixed(1),
            cellBg: cell ? getComputedStyle(cell).backgroundColor : null,
            cellAlpha: cell ? alpha(getComputedStyle(cell).backgroundColor) : null,
            headBg: head ? getComputedStyle(head).backgroundColor : null,
            afterPhase: after && textRects(after).length ? phase(after) : null};
  });

  // Code: consecutive .HyperMD-codeblock lines are one block.
  const blocks = [];
  for (const el of kids) {
    const isCode = el.classList.contains('HyperMD-codeblock');
    if (!isCode) { if (blocks.length && blocks[blocks.length - 1].open) blocks[blocks.length - 1].open = false; continue; }
    if (!blocks.length || !blocks[blocks.length - 1].open) blocks.push({open: true, lines: []});
    blocks[blocks.length - 1].lines.push(el);
  }
  const code = blocks.map((blk) => {
    const first = blk.lines[0], last = blk.lines[blk.lines.length - 1];
    const top = first.getBoundingClientRect().top, bottom = last.getBoundingClientRect().bottom;
    const h = bottom - top;
    let minGap = Infinity, worst = null;
    for (const line of blk.lines) {
      const b = line.getBoundingClientRect(), t = textRects(line);
      if (!t.length) continue;
      const gap = b.right - Math.max(...t.map((x) => x.right));
      if (gap < minGap) { minGap = gap; worst = (line.textContent || '').trim().slice(0, 32); }
    }
    // The language label sits in the fence row; it must overlap no code text.
    const flair = first.querySelector('.code-block-flair')
      || (first.parentElement && first.parentElement.querySelector('.code-block-flair'));
    let overlap = null;
    if (flair) {
      const f = flair.getBoundingClientRect();
      overlap = 0;
      for (const line of blk.lines) for (const t of textRects(line)) {
        const dx = Math.min(f.right, t.right) - Math.max(f.left, t.left);
        const dy = Math.min(f.bottom, t.bottom) - Math.max(f.top, t.top);
        if (dx > 0.5 && dy > 0.5) overlap = Math.max(overlap, +Math.min(dx, dy).toFixed(2));
      }
    }
    const after = last.nextElementSibling;
    const cs = getComputedStyle(first);
    return {lines: blk.lines.length, h: +h.toFixed(2), rows: +(h / row).toFixed(3), off: off(h),
            minGap: minGap === Infinity ? null : +minGap.toFixed(2), worstLine: worst,
            padStart: cs.paddingInlineStart, padEnd: cs.paddingInlineEnd, indent: cs.textIndent,
            flair: !!flair, flairH: flair ? +flair.getBoundingClientRect().height.toFixed(2) : null,
            flairOverlap: overlap,
            afterPhase: after && textRects(after).length ? phase(after) : null};
  });

  const scroller = view.querySelector('.cm-scroller');
  const sb = scroller.getBoundingClientRect();
  return {row, tables, code,
          column: +content.getBoundingClientRect().width.toFixed(1),
          pane: +sb.width.toFixed(1),
          sideways: scroller.scrollWidth > scroller.clientWidth + 1,
          scrollerBox: {left: +sb.left.toFixed(1), right: +sb.right.toFixed(1)}};
})()
"""

READ = r"""
(async () => {
  const leaf = app.workspace.getLeavesOfType('markdown')
    .find((l) => l.view.containerEl.ownerDocument === document && l.view.getMode
                 && l.view.file);
  if (!leaf) return {error: 'no markdown leaf'};
  const settle = () => new Promise((r) => requestAnimationFrame(
    () => requestAnimationFrame(() => setTimeout(r, 300))));
  const original = JSON.parse(JSON.stringify(leaf.view.getState()));
  const out = {error: null, original};
  try {
    await leaf.view.setState({...original, mode: 'preview'}, {history: false});
    await settle(); await settle();
    const pv = leaf.view.containerEl.querySelector('.markdown-reading-view .markdown-preview-view')
      || leaf.view.containerEl.querySelector('.markdown-preview-view');
    const sizer = pv && pv.querySelector('.markdown-preview-sizer');
    if (!sizer) { out.error = 'no sizer'; throw new Error(out.error); }
    const p = document.createElement('div');
    p.style.cssText = 'position:absolute;visibility:hidden;line-height:var(--midori-row)';
    pv.appendChild(p);
    const row = parseFloat(getComputedStyle(p).lineHeight);
    p.remove();
    const off = (h) => +Math.min(h % row, row - (h % row)).toFixed(2);
    const alpha = (c) => { const m = /rgba?\(([^)]+)\)/.exec(c);
      return m ? (m[1].split(',').length > 3 ? parseFloat(m[1].split(',')[3]) : 1) : null; };
    // Scroll the whole note so lazily-rendered sections exist, then measure.
    const seenT = [], seenP = [];
    for (let y = 0; y <= pv.scrollHeight; y += pv.clientHeight / 2) {
      pv.scrollTop = y; await settle();
      for (const el of pv.querySelectorAll('.markdown-preview-sizer > .el-table')) {
        if (seenT.some((r) => r.el === el)) continue;
        const b = el.getBoundingClientRect(), t = el.querySelector('table');
        const cell = el.querySelector('td'), head = el.querySelector('th');
        seenT.push({el, h: +b.height.toFixed(2), off: off(b.height),
                    width: +b.width.toFixed(1), left: +b.left.toFixed(1),
                    right: +b.right.toFixed(1),
                    inner: t ? +t.getBoundingClientRect().width.toFixed(1) : null,
                    cellAlpha: cell ? alpha(getComputedStyle(cell).backgroundColor) : null,
                    headBg: head ? getComputedStyle(head).backgroundColor : null});
      }
      for (const el of pv.querySelectorAll('pre')) {
        if (seenP.some((r) => r.el === el)) continue;
        const b = el.getBoundingClientRect(), cs = getComputedStyle(el);
        const btn = el.querySelector('button.copy-code-button');
        const bb = btn ? btn.getBoundingClientRect() : null;
        seenP.push({el, h: +b.height.toFixed(2), off: off(b.height),
                    padLeft: cs.paddingLeft, padRight: cs.paddingRight,
                    button: !!btn, buttonBox: bb ? +bb.height.toFixed(2) : null});
      }
    }
    const view = pv.getBoundingClientRect();
    out.row = row;
    out.tables = seenT.map(({el, ...r}) => r);
    out.pres = seenP.map(({el, ...r}) => r);
    out.column = +sizer.getBoundingClientRect().width.toFixed(1);
    out.view = {left: +view.left.toFixed(1), right: +view.right.toFixed(1),
                width: +view.width.toFixed(1)};
    out.sideways = pv.scrollWidth > pv.clientWidth + 1;
  } catch (e) { out.error = out.error || String(e.message || e); }
  try { await leaf.view.setState(original, {history: false});
        await new Promise((r) => setTimeout(r, 400)); }
  catch (e) { out.error = (out.error || '') + ' | restore: ' + String(e.message || e); }
  out.restoredMode = leaf.view.getMode();
  return out;
})()
"""

FAIL = []


def ok(axis, msg):
    print(f"  ok   [{axis}] {msg}")


def bad(axis, msg):
    print(f"  FAIL [{axis}] {msg}")
    FAIL.append(axis)


def main():
    ws = pick_window()
    live = evaluate(ws, LIVE)
    if live.get("error"):
        sys.exit(f"live preview: {live['error']}")
    read = evaluate(ws, READ, await_promise=True)
    ws.close()
    if read.get("error"):
        sys.exit(f"reading view: {read['error']}")

    row = live["row"]
    print(f"live preview: row {row}px, column {live['column']}px, pane {live['pane']}px, "
          f"{len(live['tables'])} table(s), {len(live['code'])} code block(s)")
    print(f"reading view: row {read['row']}px, column {read['column']}px, "
          f"view {read['view']['width']}px, {len(read['tables'])} table(s), "
          f"{len(read['pres'])} pre(s)\n")

    if not live["tables"] or not live["code"]:
        sys.exit("live preview measured no blocks; nothing was checked")
    if not read["tables"] or not read["pres"]:
        sys.exit("reading view measured no blocks; nothing was checked")

    # table-rows -- both views
    for where, items in (("live", live["tables"]), ("read", read["tables"])):
        for i, t in enumerate(items):
            if t["off"] > TOL:
                bad("table-rows", f"{where} table {i} is {t['h']}px, "
                                  f"{t['off']}px off the {row}px row")
            else:
                ok("table-rows", f"{where} table {i} is {t['h']}px = "
                                 f"{round(t['h'] / row)} rows")

    # code-rows -- live preview blocks and reading-view <pre>
    for i, cb in enumerate(live["code"]):
        if cb["off"] > TOL:
            bad("code-rows", f"live code block {i} ({cb['lines']} lines) is "
                             f"{cb['h']}px, {cb['off']}px off the row")
        else:
            ok("code-rows", f"live code block {i} is {cb['h']}px = "
                            f"{round(cb['h'] / row)} rows")
    for i, pre in enumerate(read["pres"]):
        if pre["off"] > TOL:
            bad("code-rows", f"reading-view pre {i} is {pre['h']}px, "
                             f"{pre['off']}px off the row")
        else:
            ok("code-rows", f"reading-view pre {i} is {pre['h']}px = "
                            f"{round(pre['h'] / row)} rows")

    # paragraph-phase -- what follows a block must be back on the lattice
    seen = 0
    for kind, items in (("table", live["tables"]), ("code", live["code"])):
        for i, b in enumerate(items):
            if b["afterPhase"] is None:
                continue
            seen += 1
            if b["afterPhase"] > TOL:
                bad("paragraph-phase", f"the line after {kind} {i} is "
                                       f"{b['afterPhase']}px off the lattice")
            else:
                ok("paragraph-phase", f"the line after {kind} {i} is on the lattice")
    if not seen:
        bad("paragraph-phase", "no block had a following line to measure; scroll so "
                               "a block with text under it is on screen")

    # code-right-gap
    for i, cb in enumerate(live["code"]):
        if cb["minGap"] is None:
            bad("code-right-gap", f"live code block {i} had no measurable text")
        elif cb["minGap"] < MIN_GAP:
            bad("code-right-gap", f"live code block {i} text comes within "
                                  f"{cb['minGap']}px of the right edge "
                                  f"(floor {MIN_GAP}px) on {cb['worstLine']!r}; "
                                  f"padding-inline-end is {cb['padEnd']}")
        else:
            ok("code-right-gap", f"live code block {i} keeps {cb['minGap']}px "
                                 f"(padding-inline-end {cb['padEnd']})")

    # label-overlap
    for i, cb in enumerate(live["code"]):
        if not cb["flair"]:
            ok("label-overlap", f"live code block {i} has no language label")
        elif cb["flairOverlap"]:
            bad("label-overlap", f"the language label on live code block {i} "
                                 f"overlaps code text by {cb['flairOverlap']}px "
                                 f"(label is {cb['flairH']}px tall in a {row}px row)")
        else:
            ok("label-overlap", f"the language label on live code block {i} "
                                f"({cb['flairH']}px) overlaps no code text")
    for i, pre in enumerate(read["pres"]):
        if not pre["button"]:
            ok("label-overlap", f"reading-view pre {i} has no copy button in the DOM")
        else:
            ok("label-overlap", f"reading-view pre {i} copy button is "
                                f"{pre['buttonBox']}px tall; pre pads "
                                f"{pre['padLeft']}/{pre['padRight']}")

    # cell-opacity -- no dots may show through a cell
    for where, items in (("live", live["tables"]), ("read", read["tables"])):
        for i, t in enumerate(items):
            if t["cellAlpha"] is None:
                bad("cell-opacity", f"{where} table {i} had no cell to measure")
            elif t["cellAlpha"] < 1:
                bad("cell-opacity", f"{where} table {i} cell background is "
                                    f"alpha {t['cellAlpha']}; the dot grid shows through")
            else:
                ok("cell-opacity", f"{where} table {i} cells are opaque")

    # breakout -- wider than the column is allowed; clipped or scrolling is not
    if live["sideways"]:
        bad("breakout", "the live-preview scroller scrolls sideways")
    else:
        ok("breakout", f"no sideways scroll in live preview (pane {live['pane']}px)")
    if read["sideways"]:
        bad("breakout", "the reading view scrolls sideways")
    else:
        ok("breakout", f"no sideways scroll in reading view "
                       f"(view {read['view']['width']}px)")
    for where, items, box in (("live", live["tables"], live["scrollerBox"]),
                              ("read", read["tables"], read["view"])):
        for i, t in enumerate(items):
            if t["left"] < box["left"] - TOL or t["right"] > box["right"] + TOL:
                bad("breakout", f"{where} table {i} spans {t['left']}-{t['right']}, "
                                f"outside the pane {box['left']}-{box['right']}")
            else:
                ok("breakout", f"{where} table {i} is {t['width']}px inside the pane")

    print()
    if FAIL:
        axes = sorted(set(FAIL))
        print(f"RENDERED BLOCKS: {len(FAIL)} failure(s) across {len(axes)} axis/axes: "
              f"{', '.join(axes)}")
        sys.exit(1)
    print("RENDERED BLOCKS: all axes hold")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run it and verify it FAILS on the defects that are present**

Run: `/tmp/cdpenv/bin/python tests/check_rendered_blocks.py`

Expected: exit 1. This is the checker's sabotage proof, and it is earned rather
than staged — the defects are in the shipped theme right now, so a checker that
passes here is broken. Specifically expect:

- `table-rows` FAIL naming a table 2px off the row (122px against 120) in
  **both** views.
- `code-right-gap` FAIL naming a live code block whose text comes within a few
  px of the right edge, reporting `padding-inline-end: 0px`.
- `label-overlap` FAIL naming a 32px language label in a 24px row, **if** the
  window's code block has a language and a long first line. A block with no
  language prints `has no language label` and that is not a failure.

If `table-rows` and `code-right-gap` do NOT fail, stop: the instrument is not
measuring what it claims. Check that `pick_window` selected the note (it prints
the window it chose and the block counts) before changing anything else.

- [ ] **Step 5: Record the failing output in the commit message**

```bash
/tmp/cdpenv/bin/python tests/check_rendered_blocks.py > /tmp/blocks-before.txt 2>&1; echo "exit $?"
```

Keep `/tmp/blocks-before.txt` — later tasks diff against it.

- [ ] **Step 6: Lint and commit**

```bash
cd /Users/benjaminloschen/Projects/midori-terminal
sh tests/lint.sh
git add tests/check_rendered_blocks.py
git commit -m "$(cat <<'EOF'
test: measure tables and code blocks in the running app

A static test cannot see a specificity contest it lost or text landing 2.2px
from the edge of its own background. This measures seven axes in both views,
selects its window by content, and refuses a window with no rendered table or
code line -- the failure mode check_rendered_grid.py shipped on its first run.

Its first run fails, which is the point: table-rows reports 122px against a
wanted 120 in both views, and code-right-gap reports padding-inline-end: 0px.
The proof is earned from the shipped defects rather than staged.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013rhw75dhAvgnscSB9GHixV
EOF
)"
```

---

### Task 2: Zero the four border variables, and correct the comment that says this is already fixed

**Files:**
- Create: `tests/test_block_geometry.py`
- Modify: `tests/lint.sh` (one new section, after the `no backticks inside injected stylesheets` section)
- Modify: `obsidian/theme.css:1886-1905` (the Tables comment) and insert a `body` block before `.markdown-rendered td`

**Interfaces:**
- Consumes: `tests/check_rendered_blocks.py` from Task 1, axis `table-rows`.
- Produces: `tests/test_block_geometry.py` with module-level `REPO`, `THEME`, `THEME_NC`, `rules`, `theme_var`, `ok`, `bad`, `FAIL` imported from `test_prose_typography`, and a `__main__` block listing every test in this plan. Later tasks append tests and register them there. Test names produced here: `test_table_border_vars_are_zero`.

- [ ] **Step 1: Write the failing static test**

Create `tests/test_block_geometry.py`:

```python
#!/usr/bin/env python3
"""Static guards for table and code-block geometry.

SEPARATE FROM test_prose_typography.py BY SUBJECT, NOT BY ACCIDENT. That file
is 1300+ lines about prose -- measure, leading, the heading ladder, the indent
rhythm. Tables and code blocks are blocks, and they now carry enough geometry
of their own to be worth their own file.

HELPERS ARE IMPORTED, NOT COPIED. rules() carries a documented performance trap
(the obvious rule regex has two unbounded quantifiers around a literal and does
not finish against this 90KB stylesheet) and theme_var() carries a documented
correctness trap (this stylesheet's comments quote whole CSS declarations, so a
guard scanning unstripped text can be satisfied by prose discussing the real
thing). Copying either would fork those lessons away from their explanation.

WHAT THESE GUARDS CANNOT DO. Every defect here was a rendered one -- a
specificity contest lost to app.css, text 2.2px from an edge. These prove the
declarations exist; tests/check_rendered_blocks.py proves they take effect.
"""
import re
import sys

from test_prose_typography import FAIL, bad, ok, rules, theme_var

# Obsidian 1.13.7 re-adds a collapsed table's outer edges from these, all 1px,
# through app.css rules that out-specify the theme's own border-width: 0.
BORDER_VARS = ("--table-header-border-width",
               "--table-row-last-border-width",
               "--table-column-first-border-width",
               "--table-column-last-border-width")


def test_table_border_vars_are_zero():
    """All four of Obsidian's table edge widths must be zeroed by the theme.

    MEASURED: with them at their 1px default a five-row table is 122px against
    a wanted 120 and a dense four-column one is 410 against 408 -- in live
    preview AND in reading view -- because each 1px edge adds half its width to
    its row and half to the table in a collapsed-border table. At 0px the same
    tables measure exactly 120 and 408.

    SABOTAGE-PROVED: restoring any one of the four to 1px fails this test
    naming that variable, and deleting the body block fails it naming all four.
    """
    missing = [v for v in BORDER_VARS if theme_var(v) is None]
    if missing:
        bad("the theme never sets " + ", ".join(missing) + "; Obsidian's 1px "
            "default puts a collapsed table 2px off the grid in both views")
        return
    wrong = [(v, theme_var(v)) for v in BORDER_VARS
             if not re.fullmatch(r"0(px)?", theme_var(v).strip())]
    if wrong:
        for name, value in wrong:
            bad(f"{name} is {value!r}, not 0px; a 1px table edge adds half a "
                "pixel to its row and half to the table")
        return
    ok(f"all {len(BORDER_VARS)} Obsidian table edge widths are zeroed")


if __name__ == "__main__":
    print("== block geometry ==")
    test_table_border_vars_are_zero()
    print("block geometry: all green" if not FAIL else "block geometry: failures above")
    sys.exit(1 if FAIL else 0)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_block_geometry.py`
Expected: FAIL naming all four variables — `the theme never sets --table-header-border-width, --table-row-last-border-width, --table-column-first-border-width, --table-column-last-border-width`, exit 1.

- [ ] **Step 3: Wire it into lint**

In `tests/lint.sh`, immediately after the `no backticks inside injected stylesheets` section and before `== obsidian plugins parse ==`, add:

```sh
echo "== block geometry =="
if python3 tests/test_block_geometry.py; then :; else FAIL=1; fi
```

- [ ] **Step 4: Add the variables to the theme**

In `obsidian/theme.css`, immediately before `.markdown-rendered td,` (currently
line 1906), insert:

```css
/* THE LAST TWO PIXELS ARE OBSIDIAN'S, NOT THE BORDER WE ALREADY REMOVED.
   Four variables, all 1px in 1.13.7, feed app.css rules -- `thead tr > th`,
   `tbody tr:last-child > td`, `td:first-child`, `td:last-child` -- whose
   specificity beats the `border-width: 0` below, so the outer edges come back
   however thoroughly the cell rule zeroes its own border. In a collapsed
   table each 1px edge adds half its width to its row and half to the table.
   Measured: 122px against a wanted 120 on a five-row table and 410 against
   408 on a dense four-column one, in BOTH views; at 0px, exactly 120 and 408.
   Zeroing the variables is better than out-specifying four app.css selectors,
   which is what the previous attempt did and lost. */
body {
  --table-header-border-width: 0px;
  --table-row-last-border-width: 0px;
  --table-column-first-border-width: 0px;
  --table-column-last-border-width: 0px;
}
```

- [ ] **Step 5: Correct the false comment**

In `obsidian/theme.css`, replace this text at the end of the Tables comment
(currently lines 1900–1905):

```
   The border is the part that makes this awkward: a real border adds height
   per row, so no combination of line-height and padding can reach a whole
   multiple while it is in the layout. So paint it instead of laying it out —
   an inset box-shadow draws the same 1px rule at zero layout cost, and an
   outline (also layout-free) closes the outer edge. Cell height is then
   exactly 24n. Verified: the widget went 7.042 -> 8.000 rows. */
```

with:

```
   The border is the part that makes this awkward: a real border adds height
   per row, so no combination of line-height and padding can reach a whole
   multiple while it is in the layout. So paint it instead of laying it out —
   an inset box-shadow draws the same 1px rule at zero layout cost, and an
   outline (also layout-free) closes the outer edge.

   THE LINE THAT USED TO END THIS COMMENT WAS FALSE, AND CONFIDENTLY SO. It
   read: "Cell height is then exactly 24n. Verified: the widget went
   7.042 -> 8.000 rows." The measurement was almost certainly real when it was
   taken; the conclusion does not hold on Obsidian 1.13.7, where a five-row
   table measures 122px against a wanted 120 and a dense four-column one 410
   against 408 — in reading view as well as live preview. Zeroing the cell's
   own border-width is not sufficient, because the app re-adds the outer edges
   from four variables of its own; see the block below. Whether those variables
   existed when that line was written and this regressed, or whether the
   original measurement was of something else, is NOT established — what is
   measured is the behaviour on 1.13.7. The lesson is the one this repo keeps
   paying for: the number was checked and the mechanism beside it was not. */
```

- [ ] **Step 6: Run the static test to verify it passes**

Run: `python3 tests/test_block_geometry.py`
Expected: `ok   all 4 Obsidian table edge widths are zeroed`, exit 0.

- [ ] **Step 7: Sabotage-prove the static test**

```bash
cd /Users/benjaminloschen/Projects/midori-terminal
cp obsidian/theme.css /tmp/theme.css.bak
# (a) one variable back to 1px
sed -i '' 's/--table-header-border-width: 0px;/--table-header-border-width: 1px;/' obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming --table-header-border-width)"
cp /tmp/theme.css.bak obsidian/theme.css
# (b) the whole block deleted
python3 - <<'PY'
import pathlib, re
p = pathlib.Path("obsidian/theme.css"); s = p.read_text()
s = re.sub(r"body \{\n  --table-header-border-width.*?\n\}\n", "", s, flags=re.S, count=1)
p.write_text(s)
PY
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming all four)"
cp /tmp/theme.css.bak obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 0 -- theme restored)"
```

Expected: (a) exit 1 naming `--table-header-border-width`; (b) exit 1 naming all
four; restored exit 0. If either sabotage passes, the guard is not a guard.

- [ ] **Step 8: Verify the rendered axis went green**

Run: `/tmp/cdpenv/bin/python tests/check_rendered_blocks.py`
Expected: every `table-rows` line is now `ok`, reporting 120px (5 rows) rather
than 122px, in **both** views. `code-right-gap` still fails — Task 7 owns it.

- [ ] **Step 9: Lint and commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_block_geometry.py tests/lint.sh
git commit -m "$(cat <<'EOF'
fix(obsidian): tables were 2px tall from Obsidian's own border variables

Four variables, all 1px, feed app.css rules that out-specify the theme's
border-width: 0, so a collapsed table's outer edges came back and each added
half a pixel to its row and half to the table. Measured 122px against a wanted
120 on a five-row table and 410 against 408 on a dense four-column one, in
reading view as well as live preview; at 0px, exactly 120 and 408.

The comment above these rules claimed this was already fixed ("the widget went
7.042 -> 8.000 rows"). It is corrected in place, saying what is measured and
what is not established, rather than replaced silently.

Static guard sabotage-proved both ways: one variable back to 1px fails naming
it, the block deleted fails naming all four.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013rhw75dhAvgnscSB9GHixV
EOF
)"
```

---

### Task 3: Cell geometry — half a row of padding on all four sides

**Files:**
- Modify: `obsidian/theme.css:1906-1931` (the `td`/`th` rule and the `.cm-table-widget` cell rule)
- Modify: `tests/test_block_geometry.py` (add `test_cells_pad_half_a_row`, register it)

**Interfaces:**
- Consumes: the `body` token block from Task 2 (extended here with `--midori-cell-pad`); `check_rendered_blocks.py` axes `table-rows`, `cell-opacity`.
- Produces: the custom property `--midori-cell-pad: calc(var(--midori-row) / 2)`, read by Task 4's look rules and asserted by later static tests.

- [ ] **Step 1: Write the failing static test**

Append to `tests/test_block_geometry.py`, before the `__main__` block:

```python
def test_cells_pad_half_a_row():
    """A cell pads half a row on all four sides, in both views.

    A cell of n lines is then row x n + 2 x (row / 2) = row x (n + 1), so a
    table totals whole rows however its cells wrap -- which is the property the
    old 8px padding lacked: it held on a desktop where every cell is one line
    and broke on a phone where the same cells wrap to two, because the
    line-height term scales with wrapping while a constant does not.

    Half a row is always a whole pixel: the theme rounds the row UP TO 2px (see
    "TWO PIXELS, NOT ONE" in theme.css), so the row is always even.

    THE LIVE-PREVIEW RULE MUST RESTATE IT. .cm-table-widget's own cell rule is
    (0,3,1) and beats the (0,1,1) reading-view rule, so a single declaration
    silently applies to reading view only -- the trap the existing comment in
    theme.css records with !important.

    SABOTAGE-PROVED: changing --midori-cell-pad to 0 fails naming the token;
    deleting the padding from the widget rule fails naming live preview.
    """
    pad = theme_var("--midori-cell-pad")
    if pad is None:
        bad("--midori-cell-pad is not set; a cell needs half a row of padding "
            "on all four sides for a table to total whole rows")
        return
    if not re.fullmatch(r"calc\(\s*var\(--midori-row\)\s*/\s*2\s*\)", pad.strip()):
        bad(f"--midori-cell-pad is {pad!r}; it must be "
            "calc(var(--midori-row) / 2) so it follows the reader's row")
        return

    def pads(selector_needle, extra=None):
        hits = []
        for sel, decls in rules():
            if selector_needle not in sel:
                continue
            if extra and extra not in sel:
                continue
            if re.search(r"(^|;)\s*padding:\s*var\(--midori-cell-pad\)", decls):
                hits.append(sel)
        return hits

    reading = [sel for sel in pads(".markdown-rendered td")]
    if not reading:
        bad("no .markdown-rendered td rule pads var(--midori-cell-pad); "
            "reading-view cells keep Obsidian's 8px and fall off the row")
    widget = [sel for sel in pads(".cm-table-widget td")]
    if not widget:
        bad("no .cm-table-widget td rule pads var(--midori-cell-pad); the "
            "widget's own (0,3,1) cell rule wins and live preview is unfixed")
    if not reading or not widget:
        return
    for sel in widget:
        for one in sel.split(","):
            if ".cm-table-widget" in one and "td" in one and "*" not in one:
                break
        else:
            bad(f"a widget padding rule targets no bare cell: {sel[:70]}")
            return
    ok(f"cells pad half a row in both views ({len(reading)} reading-view rule(s), "
       f"{len(widget)} live-preview rule(s))")
```

and register it in `__main__`:

```python
    test_table_border_vars_are_zero()
    test_cells_pad_half_a_row()
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_block_geometry.py`
Expected: FAIL — `--midori-cell-pad is not set; a cell needs half a row of padding on all four sides for a table to total whole rows`, exit 1.

- [ ] **Step 3: Add the token**

In `obsidian/theme.css`, extend the `body` block added in Task 2 so it reads:

```css
body {
  --table-header-border-width: 0px;
  --table-row-last-border-width: 0px;
  --table-column-first-border-width: 0px;
  --table-column-last-border-width: 0px;

  /* Half a row on all four sides of a cell, so a cell of n lines is
     row x (n + 1) and a table totals whole rows however its cells wrap. Always
     a whole pixel: the row is rounded up to 2px (see "TWO PIXELS, NOT ONE"),
     so it is always even. */
  --midori-cell-pad: calc(var(--midori-row) / 2);
}
```

- [ ] **Step 4: Replace the reading-view cell rule**

Replace (currently lines 1906–1914):

```css
.markdown-rendered td,
.markdown-rendered th {
  line-height: var(--midori-row);
  padding-block: 0;
  border-width: 0;
  box-shadow:
    inset 0 -1px 0 var(--table-border-color),
    inset -1px 0 0 var(--table-border-color);
}
```

with:

```css
.markdown-rendered td,
.markdown-rendered th {
  line-height: var(--midori-row);
  padding: var(--midori-cell-pad);
  border-width: 0;
  box-shadow:
    inset 0 -1px 0 var(--table-border-color),
    inset -1px 0 0 var(--table-border-color);
}
```

- [ ] **Step 5: Replace the live-preview cell rule**

Replace (currently lines 1924–1931):

```css
.markdown-source-view.mod-cm6 .cm-table-widget td,
.markdown-source-view.mod-cm6 .cm-table-widget th,
.markdown-source-view.mod-cm6 .cm-table-widget td *,
.markdown-source-view.mod-cm6 .cm-table-widget th * {
  line-height: var(--midori-row) !important;
  padding-block: 0 !important;
  margin-block: 0 !important;
}
```

with:

```css
.markdown-source-view.mod-cm6 .cm-table-widget td,
.markdown-source-view.mod-cm6 .cm-table-widget th {
  line-height: var(--midori-row) !important;
  padding: var(--midori-cell-pad) !important;
  margin-block: 0 !important;
}
/* The cell's INNER wrapper keeps zero block padding and zero margin. It is a
   separate rule because the cell now pads half a row and the wrapper must not
   double it — the two used to share one declaration block, which is why the
   padding had to be 0 for both. */
.markdown-source-view.mod-cm6 .cm-table-widget td *,
.markdown-source-view.mod-cm6 .cm-table-widget th * {
  line-height: var(--midori-row) !important;
  padding-block: 0 !important;
  margin-block: 0 !important;
}
```

- [ ] **Step 6: Run the static test to verify it passes**

Run: `python3 tests/test_block_geometry.py`
Expected: `ok   cells pad half a row in both views (1 reading-view rule(s), 1 live-preview rule(s))`, exit 0.

- [ ] **Step 7: Sabotage-prove it**

```bash
cd /Users/benjaminloschen/Projects/midori-terminal
cp obsidian/theme.css /tmp/theme.css.bak
sed -i '' 's|--midori-cell-pad: calc(var(--midori-row) / 2);|--midori-cell-pad: 0px;|' obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming --midori-cell-pad)"
cp /tmp/theme.css.bak obsidian/theme.css
python3 - <<'PY'
import pathlib
p = pathlib.Path("obsidian/theme.css"); s = p.read_text()
s = s.replace("""  line-height: var(--midori-row) !important;
  padding: var(--midori-cell-pad) !important;
  margin-block: 0 !important;""", """  line-height: var(--midori-row) !important;
  margin-block: 0 !important;""", 1)
p.write_text(s)
PY
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming live preview)"
cp /tmp/theme.css.bak obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 0)"
```

Expected: exit 1 naming `--midori-cell-pad`; exit 1 naming the widget rule; then 0.

- [ ] **Step 8: Verify in the app**

Run: `/tmp/cdpenv/bin/python tests/check_rendered_blocks.py`
Expected: `table-rows` still `ok` in both views, with the tables now TALLER by
one row per table (a five-row table becomes 6 rows = 144px, because every cell
gained half a row top and bottom). The number must still be a whole multiple of
the row; that is the assertion. `paragraph-phase` must stay `ok`.

- [ ] **Step 9: Lint and commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_block_geometry.py
git commit -m "$(cat <<'EOF'
feat(obsidian): table cells pad half a row on all four sides

A cell of n lines is now row x (n + 1), so a table totals whole rows however
its cells wrap -- the property the old 8px padding lacked, which held on a
desktop where every cell is one line and broke where they wrap to two. Half a
row is always a whole pixel because the row is rounded up to 2px.

The widget's inner-wrapper rule is split out: the cell pads half a row now, and
the wrapper must not double it.

Cell text therefore sits half a row off the dots, which was seen and accepted
in the rendered mockup this design was chosen from.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013rhw75dhAvgnscSB9GHixV
EOF
)"
```

---

### Task 4: The look — visible rules, a header band, and cells the dots do not show through

**Files:**
- Modify: `obsidian/theme.css` (the `body` token block; add a `th` rule after the cell rules in both views)
- Modify: `tests/test_block_geometry.py` (add `test_table_colours_derive_from_theme_vars`, register it)

**Interfaces:**
- Consumes: `--midori-cell-pad` from Task 3.
- Produces: `--table-border-color` (redefined) and `--midori-table-header-bg`, both `color-mix()` over `var(--text-normal)` / `var(--background-primary)`.

- [ ] **Step 1: Write the failing static test**

Append to `tests/test_block_geometry.py`, before `__main__`:

```python
def test_table_colours_derive_from_theme_vars():
    """Rules and the header band derive from theme variables, not literals.

    Both modes then follow for free -- --text-normal and --background-primary
    are already per-mode -- so there is no second copy to forget. theme_vars()
    exists because this stylesheet declares most colour tokens twice, once per
    mode, and a guard built on the last one proves at most one mode is wired;
    deriving instead means there is only ever one declaration to check.

    Cells must also be OPAQUE. --background-primary is the paper the dot grid
    is painted on, so an opaque cell hides the dots inside the table; a
    transparent or alpha cell lets them show through every cell, which is the
    single biggest reason the old tables read as noisy.

    SABOTAGE-PROVED: replacing either token with a hex literal fails naming it.
    """
    for name, needles in (("--table-border-color", ("color-mix", "var(--text-normal)")),
                          ("--midori-table-header-bg", ("color-mix", "var(--text-normal)",
                                                        "var(--background-primary)"))):
        value = theme_var(name)
        if value is None:
            bad(f"{name} is not set; the table rules and header band have no "
                "derived colour and dark mode needs a second copy")
            return
        missing = [n for n in needles if n not in value]
        if missing:
            bad(f"{name} is {value!r}, which does not derive from "
                + ", ".join(missing) + "; a literal here needs a dark-mode copy")
            return

    # A SUBSTRING TEST WOULD NOT BE A CELL TEST. "th" appears in .theme-light,
    # .theme-dark, body.theme-dark and a dozen .mermaid selectors: measured on
    # this stylesheet, 16 selectors contain "td" or "th" and only 3 are cell
    # selectors. None of the other 13 sets a cell background today, so a
    # substring guard would pass for the right reason BY LUCK -- exactly the
    # shape of check this repo has been burned by. Match the element as a token.
    CELL = re.compile(r"(^|[ ,>+~])(td|th)\b")
    HEAD = re.compile(r"(^|[ ,>+~])th\b")
    opaque = [sel for sel, decls in rules()
              if CELL.search(sel)
              and re.search(r"background:\s*var\(--background-primary\)", decls)]
    if not opaque:
        bad("no cell rule sets background: var(--background-primary); the dot "
            "grid shows through every cell")
        return
    banded = [sel for sel, decls in rules()
              if HEAD.search(sel)
              and re.search(r"background:\s*var\(--midori-table-header-bg\)", decls)]
    if not banded:
        bad("no th rule sets background: var(--midori-table-header-bg); the "
            "header differs from the body by weight alone")
        return
    ok(f"table colours derive from theme variables; cells opaque in "
       f"{len(opaque)} rule(s), header banded in {len(banded)}")
```

and register it in `__main__` after `test_cells_pad_half_a_row()`.

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_block_geometry.py`
Expected: FAIL — `--midori-table-header-bg is not set; ...`, exit 1. (`--table-border-color` is an Obsidian variable the theme may already reference but does not define; the test names whichever is missing first.)

- [ ] **Step 3: Add the colour tokens**

In `obsidian/theme.css`, extend the same `body` block so it reads:

```css
body {
  --table-header-border-width: 0px;
  --table-row-last-border-width: 0px;
  --table-column-first-border-width: 0px;
  --table-column-last-border-width: 0px;

  /* Half a row on all four sides of a cell, so a cell of n lines is
     row x (n + 1) and a table totals whole rows however its cells wrap. Always
     a whole pixel: the row is rounded up to 2px (see "TWO PIXELS, NOT ONE"),
     so it is always even. */
  --midori-cell-pad: calc(var(--midori-row) / 2);

  /* The rules were rgba(60,58,54,0.1) — nearly invisible, so the dot grid read
     as the table's structure instead. 28% of the text colour is a rule you can
     see without it becoming the loudest thing in the block.

     REDEFINING OBSIDIAN'S OWN TOKEN, not adding a parallel one: every app.css
     rule that paints a table edge reads --table-border-color, so one
     definition moves the drag handles and insertion markers with the rules,
     and the theme's inset box-shadows keep reading the same name.

     DERIVED, SO DARK MODE NEEDS NO SECOND COPY. --text-normal and
     --background-primary are already per-mode; color-mix() over them means
     there is one declaration rather than two to keep in step. Still checked by
     eye in both modes — derived is not the same as verified. */
  --table-border-color: color-mix(in srgb, var(--text-normal) 28%, transparent);
  --midori-table-header-bg: color-mix(in srgb, var(--text-normal) 9%,
                                      var(--background-primary));
}
```

- [ ] **Step 4: Make cells opaque and band the header, reading view**

Replace the reading-view cell rule from Task 3 with:

```css
.markdown-rendered td,
.markdown-rendered th {
  line-height: var(--midori-row);
  padding: var(--midori-cell-pad);
  border-width: 0;
  /* Opaque, so the dot grid stops showing through the table. The paper colour,
     not a tint: the table is on the page, not floating over it. */
  background: var(--background-primary);
  box-shadow:
    inset 0 -1px 0 var(--table-border-color),
    inset -1px 0 0 var(--table-border-color);
}
/* The header keeps the body face — a band and weight 600 separate it, not a
   different family or small caps, both of which were tried in the rendered
   mockups and read as a different document. */
.markdown-rendered th {
  background: var(--midori-table-header-bg);
  font-weight: 600;
}
```

- [ ] **Step 5: Make cells opaque and band the header, live preview**

Immediately after the widget inner-wrapper rule from Task 3, add:

```css
/* Live preview again needs its own copy at the widget's specificity, and the
   header band must come AFTER the cell background at equal specificity and
   equal !important, or `th` loses to `td, th`. */
.markdown-source-view.mod-cm6 .cm-table-widget td,
.markdown-source-view.mod-cm6 .cm-table-widget th {
  background: var(--background-primary) !important;
}
.markdown-source-view.mod-cm6 .cm-table-widget th {
  background: var(--midori-table-header-bg) !important;
  font-weight: 600;
}
```

- [ ] **Step 6: Run the static test to verify it passes**

Run: `python3 tests/test_block_geometry.py`
Expected: `ok   table colours derive from theme variables; cells opaque in 2 rule(s), header banded in 2`, exit 0.

- [ ] **Step 7: Sabotage-prove it**

```bash
cd /Users/benjaminloschen/Projects/midori-terminal
cp obsidian/theme.css /tmp/theme.css.bak
sed -i '' 's|--midori-table-header-bg: color-mix(in srgb, var(--text-normal) 9%,|--midori-table-header-bg: #f0efe9; /*|' obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming --midori-table-header-bg)"
cp /tmp/theme.css.bak obsidian/theme.css
python3 - <<'PY'
import pathlib
p = pathlib.Path("obsidian/theme.css"); s = p.read_text()
s = s.replace("  background: var(--background-primary);\n", "", 1)
p.write_text(s)
PY
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming the dot grid showing through)"
cp /tmp/theme.css.bak obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 0)"
```

- [ ] **Step 8: Verify in the app**

Run: `/tmp/cdpenv/bin/python tests/check_rendered_blocks.py`
Expected: `cell-opacity` turns `ok` in both views (it reports the measured
alpha, which must be 1). `table-rows` and `paragraph-phase` stay `ok` — a
background and a font weight change no geometry.

If `cell-opacity` still fails in live preview, the widget's own cell background
is out-specifying the rule: add `!important` to the `background` declaration in
the reading-view rule too and re-run. (Reading view has no competing rule, so
this is only ever needed on the widget copy, which already has it.)

- [ ] **Step 9: Lint and commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_block_geometry.py
git commit -m "$(cat <<'EOF'
feat(obsidian): visible table rules, a header band, and opaque cells

The rules were rgba(60,58,54,0.1) and the cells transparent, so the dot grid
read as the table's structure and the header differed from the body by weight
alone. Rules are now 28% of the text colour, the header band 9% over the paper,
and cells take the paper colour so no dots show inside a table.

Both values are color-mix() over --text-normal and --background-primary, so
dark mode follows from one declaration instead of a second copy. Obsidian's own
--table-border-color is redefined rather than shadowed, so the drag handles and
insertion markers move with the rules.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013rhw75dhAvgnscSB9GHixV
EOF
)"
```

---

### Task 5: A row of air above and below every block

**Files:**
- Modify: `obsidian/theme.css` (new rules after the table rules; a reading-view `.el-table` margin)
- Modify: `tests/test_block_geometry.py` (add `test_blocks_get_a_row_of_air`, register it)

**Interfaces:**
- Consumes: nothing new.
- Produces: the four `:has()` selectors that give a blank editor line its row back, and `.markdown-reading-view .markdown-preview-sizer > .el-table { margin-block: var(--midori-row) }`.

- [ ] **Step 1: Write the failing static test**

Append to `tests/test_block_geometry.py`, before `__main__`:

```python
def test_blocks_get_a_row_of_air():
    """A blank line next to a block gets its row back, in live preview.

    The paragraph-indent rhythm collapses blank lines to nothing, so a table or
    a code block sat directly against the heading or paragraph either side. A
    CodeMirror line cannot take a margin, so the air has to come from the blank
    line that is already in the document -- and :has() is what lets a rule see
    a block that comes AFTER the blank line.

    MEASURED: 0 -> 24px above and below both code blocks and table widgets,
    with block height, corner radius and background untouched.

    FOUR SELECTORS, NOT TWO. Forward (:has(+ x)) and backward (x + y) are
    different selectors, and code blocks and table widgets are different
    elements, so all four combinations are needed; dropping one leaves a block
    touching its neighbour on exactly one side, which reads as a rendering bug
    rather than a missing rule.

    SABOTAGE-PROVED: deleting any one of the four selectors fails this test
    naming which neighbour and which side.
    """
    WANT = (("codeblock-begin", "before a code block",
             lambda s: ":has(> br:only-child)" in s and "+ .cm-line.HyperMD-codeblock-begin" in s),
            ("codeblock-end", "after a code block",
             lambda s: "HyperMD-codeblock-end + .cm-line" in s and ":has(> br:only-child)" in s),
            ("table-before", "before a table",
             lambda s: ":has(> br:only-child)" in s and "+ .cm-table-widget" in s),
            ("table-after", "after a table",
             lambda s: "cm-table-widget + .cm-line" in s and ":has(> br:only-child)" in s))
    selectors = []
    for sel, decls in rules():
        if re.search(r"line-height:\s*var\(--midori-row\)", decls):
            selectors.extend(" ".join(one.split()) for one in sel.split(","))
    missing = [where for _, where, match in WANT
               if not any(match(one) for one in selectors)]
    if missing:
        for where in missing:
            bad(f"no rule gives the blank line {where} a row of air; the block "
                "sits directly against its neighbour")
        return

    # theme.css ALREADY MENTIONS .el-table, and it is not this. At
    # theme.css:1688 a heading-spacing rule reads
    # `div:is(.el-blockquote, .el-p, .el-pre, .el-table, .el-ul, .el-ol) + div
    # > :is(h5, h6)` and sets margin-TOP on the heading that FOLLOWS a block,
    # not on the block. A grep for .el-table hits both; they are unrelated.
    # Requiring the sizer-child shape keeps this guard from being answered by
    # that rule. The two also interact harmlessly: reading view collapses
    # adjacent margins, so a table's new bottom row and a following heading's
    # own top row come to one row, not two.
    el_table = [sel for sel, decls in rules()
                if ".markdown-preview-sizer > .el-table" in " ".join(sel.split())
                and re.search(r"margin-block:\s*var\(--midori-row\)", decls)]
    if not el_table:
        bad("no .markdown-preview-sizer > .el-table rule sets "
            "margin-block: var(--midori-row); reading view has no air around "
            "a table")
        return
    ok(f"all 4 live-preview air selectors present, and reading view pads "
       f"{len(el_table)} table block rule(s)")
```

and register it in `__main__` after `test_table_colours_derive_from_theme_vars()`.

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_block_geometry.py`
Expected: four FAIL lines, one per missing neighbour, exit 1.

- [ ] **Step 3: Add the live-preview air rules**

In `obsidian/theme.css`, immediately after the `.markdown-rendered table` rule
(currently lines 1941–1946), add:

```css
/* AIR AROUND A BLOCK, TAKEN FROM THE BLANK LINE THAT IS ALREADY THERE.
   The paragraph-indent rhythm collapses a blank line to nothing, which is
   right between paragraphs and wrong either side of a block: a table or a code
   block ended up touching the heading above it. A CodeMirror line cannot take
   a margin — it is a line, not a box the theme owns — so the row has to come
   from the blank line in the document, and :has() is what lets a rule see the
   block that follows it.

   Measured: 0 -> 24px above and below both code blocks and table widgets, with
   block height, corner radius and background untouched.

   FOUR SELECTORS BECAUSE THERE ARE FOUR CASES. Forward (:has(+ x)) and
   backward (x + y) are different selectors, and a code block and a table
   widget are different elements. Dropping one leaves a block touching its
   neighbour on one side only, which reads as a rendering bug rather than a
   missing rule. Only a line that is ACTUALLY blank qualifies —
   :has(> br:only-child) — so a line with text keeps the prose rhythm. */
.markdown-source-view.mod-cm6 .cm-line:has(> br:only-child):has(+ .cm-line.HyperMD-codeblock-begin),
.markdown-source-view.mod-cm6 .cm-line.HyperMD-codeblock-end + .cm-line:has(> br:only-child),
.markdown-source-view.mod-cm6 .cm-line:has(> br:only-child):has(+ .cm-table-widget),
.markdown-source-view.mod-cm6 .cm-table-widget + .cm-line:has(> br:only-child) {
  line-height: var(--midori-row);
}

/* Reading view has real boxes, so it gets a real margin. One row above and
   below; adjacent margins collapse with the neighbouring paragraph's own row,
   so the gap is one row rather than two — either way a whole number. */
.markdown-reading-view .markdown-preview-sizer > .el-table {
  margin-block: var(--midori-row);
}
```

- [ ] **Step 4: Run the static test to verify it passes**

Run: `python3 tests/test_block_geometry.py`
Expected: `ok   all 4 live-preview air selectors present, and reading view pads 1 table block rule(s)`, exit 0.

- [ ] **Step 5: Sabotage-prove it**

```bash
cd /Users/benjaminloschen/Projects/midori-terminal
cp obsidian/theme.css /tmp/theme.css.bak
python3 - <<'PY'
import pathlib
p = pathlib.Path("obsidian/theme.css"); s = p.read_text()
s = s.replace(".markdown-source-view.mod-cm6 .cm-table-widget + .cm-line:has(> br:only-child),\n", "", 1)
s = s.replace(".markdown-source-view.mod-cm6 .cm-table-widget + .cm-line:has(> br:only-child) {", ".markdown-source-view.mod-cm6 .cm-line:has(> br:only-child):has(+ .cm-table-widget) {", 1)
p.write_text(s)
PY
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming 'after a table')"
cp /tmp/theme.css.bak obsidian/theme.css
python3 - <<'PY'
import pathlib
p = pathlib.Path("obsidian/theme.css"); s = p.read_text()
s = s.replace("""(.markdown-reading-view .markdown-preview-sizer > .el-table {
  margin-block: var(--midori-row);
})""".strip("()"), "", 1)
p.write_text(s)
PY
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming reading view)"
cp /tmp/theme.css.bak obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 0)"
```

- [ ] **Step 6: Verify in the app, and check the caret**

Run: `/tmp/cdpenv/bin/python tests/check_rendered_blocks.py`
Expected: `table-rows`, `code-rows` and `paragraph-phase` all still `ok`. The
air lives in the blank line, not in the block, so the block's own height must be
unchanged from Task 3's numbers; if `code-rows` or `table-rows` moved, the
padding landed on the block instead of the blank line.

By eye, in the app: click on the blank line directly above a code block. The
caret must be a full row tall and sit in the gap, not on the block's edge.

- [ ] **Step 7: Lint and commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_block_geometry.py
git commit -m "$(cat <<'EOF'
feat(obsidian): a row of air above and below tables and code blocks

The paragraph rhythm collapses blank lines, which is right between paragraphs
and wrong either side of a block -- a table ended up touching the heading above
it. A CodeMirror line cannot take a margin, so the row comes from the blank
line already in the document, with :has() looking forward to the block.

Four selectors, because forward and backward are different selectors and a code
block and a table widget are different elements. Measured 0 -> 24px on all four
sides, with block height, radius and background untouched. Reading view has
real boxes and gets a real margin on .el-table.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013rhw75dhAvgnscSB9GHixV
EOF
)"
```

---

### Task 6: Width — a table may break out wider than the prose column

**Files:**
- Modify: `obsidian/theme.css` (the `body` token block; the `.cm-table-widget` rule; new `.el-table` width rules; one `container-type` rule)
- Modify: `tests/test_block_geometry.py` (add `test_block_width_has_a_query_container`, register it)

**Interfaces:**
- Consumes: `--file-line-width` (declared at `obsidian/theme.css:195`).
- Produces: `--midori-block-max`, used by both views' block width rules.

- [ ] **Step 1: Write the failing static test**

Append to `tests/test_block_geometry.py`, before `__main__`:

```python
def test_block_width_has_a_query_container():
    """A cqi unit is only meaningful with a query container, so prove there is one.

    --midori-block-max reads 100cqi to learn the pane width. A container query
    unit with NO container does not fail loudly -- it silently resolves against
    the small viewport, which here is the whole 1728px window rather than the
    1428px pane, so a table would break out past the edge of its own pane and
    the only symptom would be a clipped last column.

    MEASURED: 100cqi is 1364px with container-type: inline-size on .cm-scroller
    (live preview) and 1364px with it on .markdown-preview-view (reading view)
    -- the 1428px pane less 32px of scroller padding each side -- against
    1728px, the window, with no container. Layout was byte-identical before,
    during and after in both views.

    BOTH VIEWS NEED THEIR OWN CONTAINER: they have different scrollers, and a
    container on one says nothing about the other.

    SABOTAGE-PROVED: dropping either scroller from the container-type rule fails
    this test naming that view.
    """
    value = theme_var("--midori-block-max")
    if value is None:
        bad("--midori-block-max is not set; blocks have no width ceiling")
        return
    if "100cqi" not in value:
        bad(f"--midori-block-max is {value!r} and never reads 100cqi, so it "
            "cannot know the pane width")
        return
    for needle in ("var(--file-line-width)", "min(", "max("):
        if needle not in value:
            bad(f"--midori-block-max is {value!r}, missing {needle}; it must be "
                "floored at the prose column and capped at the pane less 96px")
            return

    containers = []
    for sel, decls in rules():
        if re.search(r"container-type:\s*inline-size", decls):
            containers.extend(" ".join(one.split()) for one in sel.split(","))
    for needle, view in ((".cm-scroller", "live preview"),
                         (".markdown-preview-view", "reading view")):
        if not any(needle in one for one in containers):
            bad(f"no rule makes {needle} a query container, so 100cqi in "
                f"{view} resolves against the window instead of the pane")
            return
    ok(f"--midori-block-max reads 100cqi and both views declare a query "
       f"container ({len(containers)} selector(s))")
```

and register it in `__main__` after `test_blocks_get_a_row_of_air()`.

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_block_geometry.py`
Expected: FAIL — `--midori-block-max is not set; blocks have no width ceiling`, exit 1.

- [ ] **Step 3: Add the width token and the query containers**

In `obsidian/theme.css`, extend the same `body` block with:

```css
  /* HOW WIDE A BLOCK MAY GET. At least the prose column, so a table is never
     narrower than the paragraph beside it. Past that it grows symmetrically
     about the column to 1.6x the column, capped at the pane less 96px so it
     never reaches the pane's edge; and when that cap is BELOW the column — a
     pane narrower than the column plus 96px — the column wins, which is what
     the outer max() is for. Past the ceiling, Obsidian's own sideways scroll
     inside the block applies.

     100cqi IS THE PANE, BUT ONLY WITH A CONTAINER. A container query unit with
     no query container does not fail loudly: it resolves against the small
     viewport, which is the whole window, and a table would break out past the
     edge of its own pane with a clipped column as the only symptom. Hence the
     container-type rule below, on BOTH views' scrollers.

     Measured: 100cqi = 1364px in each view (the 1428px pane less 32px of
     scroller padding each side) against 1728px — the window — with no
     container; layout byte-identical before, during and after; scrolling
     intact; and no new re-anchoring of fixed descendants, because
     .workspace-leaf is already contain: strict and was their containing block
     already.

     THE cqi RESOLVES AT THE USE SITE, NOT HERE. A custom property is a token
     stream, so the unit is resolved when a real property substitutes it —
     which is inside the container, on the block. That is also the constraint:
     only elements inside a container may read this. */
  --midori-block-max: max(var(--file-line-width),
                          min(calc(var(--file-line-width) * 1.6),
                              calc(100cqi - 96px)));
```

Then, immediately after that `body` block, add:

```css
/* One query container per view's scroller. Measured on both: the layout is
   byte-identical with and without it, and scrolling is unaffected. */
.markdown-source-view.mod-cm6 .cm-scroller,
.markdown-reading-view .markdown-preview-view {
  container-type: inline-size;
}
```

- [ ] **Step 4: Widen the block in live preview**

Replace (currently lines 1937–1940):

```css
.markdown-source-view.mod-cm6 .cm-table-widget {
  padding-block: 0;
  margin-block: 0;
}
```

with:

```css
.markdown-source-view.mod-cm6 .cm-table-widget {
  padding-block: 0;
  margin-block: 0;
  /* The widget is the block: it takes the ceiling width and is pulled out
     symmetrically, so its centre stays the column's centre whatever the
     ceiling resolves to. Obsidian sets `margin: 0 calc(-1 * var(--size-4-4))
     !important` here, so the inline margins need !important to replace it at
     all. The widget paints nothing, so a widget wider than its table is
     invisible. */
  width: var(--midori-block-max);
  margin-inline: calc((var(--file-line-width) - var(--midori-block-max)) / 2) !important;
}
/* The table inside is content-sized — measured 487.7px in a 655.2px column —
   so without this it ignores the room the widget just gained and the breakout
   is invisible. At least the column, as wide as its content needs, never wider
   than the widget. */
.markdown-source-view.mod-cm6 .cm-table-widget table {
  width: max-content;
  min-width: var(--file-line-width);
  max-width: 100%;
  margin-inline: auto;
}
```

- [ ] **Step 5: Widen the block in reading view**

Replace the `.el-table` rule added in Task 5 with:

```css
.markdown-reading-view .markdown-preview-sizer > .el-table {
  margin-block: var(--midori-row);
  /* Reading view's block wrapper is .el-table — the sizer's direct child, not
     .table-wrapper and not the table itself. It already carries
     overflow-x: auto, which is where Obsidian's own sideways scroll comes from
     once a table passes the ceiling.

     Measured: widened to 1040px it centred at 494-1534 inside the 1428px view,
     grew 384.8px, cells went 101.2 -> 216.1px, height unchanged, no sideways
     scroll on the view or the document, and both far edges hit-tested as th —
     nothing clips a block wider than the column here. */
  width: var(--midori-block-max);
  margin-inline: calc((var(--file-line-width) - var(--midori-block-max)) / 2);
}
.markdown-reading-view .markdown-preview-sizer > .el-table > table {
  width: max-content;
  min-width: var(--file-line-width);
  max-width: 100%;
  margin-inline: auto;
}
```

- [ ] **Step 6: Run the static test to verify it passes**

Run: `python3 tests/test_block_geometry.py`
Expected: `ok   --midori-block-max reads 100cqi and both views declare a query container (2 selector(s))`, exit 0.

- [ ] **Step 7: Sabotage-prove it**

```bash
cd /Users/benjaminloschen/Projects/midori-terminal
cp obsidian/theme.css /tmp/theme.css.bak
python3 - <<'PY'
import pathlib
p = pathlib.Path("obsidian/theme.css"); s = p.read_text()
s = s.replace(".markdown-source-view.mod-cm6 .cm-scroller,\n.markdown-reading-view .markdown-preview-view {\n  container-type: inline-size;\n}",
              ".markdown-source-view.mod-cm6 .cm-scroller {\n  container-type: inline-size;\n}", 1)
p.write_text(s)
PY
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming reading view)"
cp /tmp/theme.css.bak obsidian/theme.css
sed -i '' 's|calc(100cqi - 96px)|calc(100vw - 96px)|' obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming 100cqi)"
cp /tmp/theme.css.bak obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 0)"
```

- [ ] **Step 8: Verify in the app, both views**

Run: `/tmp/cdpenv/bin/python tests/check_rendered_blocks.py`
Expected: `breakout` `ok` in both views — every table inside the pane and no
sideways scroll — and `table-rows` and `paragraph-phase` unchanged. The printed
table widths show a dense table wider than the 655.2px column; a short table
stays at the column.

Then measure the centring directly, which the checker does not assert:

```bash
cat > /tmp/centre.mjs <<'EOF'
const page = (await (await fetch('http://127.0.0.1:9222/json')).json())
  .find((t) => t.type === 'page' && t.title.includes('Obsidian'));
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
const send = (method, params) => new Promise((r) => {
  const id = Math.floor(Math.random() * 1e6);
  const on = (e) => { const m = JSON.parse(e.data);
    if (m.id === id) { ws.removeEventListener('message', on); r(m); } };
  ws.addEventListener('message', on);
  ws.send(JSON.stringify({ id, method, params }));
});
const m = await send('Runtime.evaluate', { returnByValue: true, expression: `
  (() => {
    const content = document.querySelector('.markdown-source-view.mod-cm6 .cm-content');
    const out = [];
    for (const w of document.querySelectorAll('.cm-table-widget')) {
      const b = w.getBoundingClientRect(), c = content.getBoundingClientRect();
      const t = w.querySelector('table').getBoundingClientRect();
      out.push({widget: +b.width.toFixed(1), table: +t.width.toFixed(1),
                column: +c.width.toFixed(1),
                centreMiss: +(((t.left + t.right) / 2) - ((c.left + c.right) / 2)).toFixed(2)});
    }
    return out;
  })()` });
console.log(JSON.stringify(m.result.result.value, null, 1));
ws.close();
EOF
node /tmp/centre.mjs
```

Expected: `centreMiss` within 0.5px of 0 for every table — the table's centre is
the column's centre whether or not it broke out. A non-zero miss means the
negative margin and the width disagree.

- [ ] **Step 9: Lint and commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_block_geometry.py
git commit -m "$(cat <<'EOF'
feat(obsidian): a table may break out wider than the prose column

Prose keeps its measure; a table that needs more room grows symmetrically about
the column to 1.6x it, capped at the pane less 96px, floored at the column
itself so it is never narrower than the paragraph beside it. Past the ceiling
Obsidian's own sideways scroll inside the block applies.

The pane width comes from 100cqi against a query container on each view's
scroller. Measured 1364px in both views against 1728px -- the window -- with no
container, which is the silent failure this guards: a cqi with no container
resolves against the viewport and a table would break out past its own pane.

Reading view's block wrapper is .el-table, and nothing there clips a block
wider than the column: widened to 1040px it centred at 494-1534 in a 1428px
view with no sideways scroll and both far edges hit-testing as th.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013rhw75dhAvgnscSB9GHixV
EOF
)"
```

---

### Task 7: Code text stops at its padding, and a wrapped line hangs

**Files:**
- Modify: `obsidian/theme.css:1795-1835` (the Code-blocks region)
- Modify: `tests/test_block_geometry.py` (add `test_code_lines_pad_both_sides` and `test_hanging_indent_keeps_the_list_exclusion`, register both)

**Interfaces:**
- Consumes: `check_rendered_blocks.py` axis `code-right-gap`.
- Produces: `--midori-code-pad: 16px`.

- [ ] **Step 1: Write the failing static tests**

Append to `tests/test_block_geometry.py`, before `__main__`:

```python
CODE_LINE = ".cm-line.HyperMD-codeblock"


def code_padding_rules():
    """Every rule that pads a live-preview code line, selector by selector."""
    out = []
    for sel, decls in rules():
        if CODE_LINE not in sel:
            continue
        if re.search(r"padding-inline-(start|end):", decls):
            out.append((sel, decls))
    return out


def test_code_lines_pad_both_sides():
    """A code line pads BOTH sides, and the wrap hangs by two characters.

    MEASURED before this rule: padding-left 16px, padding-right 0, and wrapped
    text ending 2.2px from the right edge of its own background -- which is what
    "the text overruns" turned out to mean. Nothing overflows; it wraps and then
    touches the edge. A wrapped line also continued flush left, so a
    continuation read as a new line of code.

    MEASURED after: first line at 16px, continuations at 30px (2ch = 14px in the
    code face), right gap >= 21px, every line still a whole number of rows.

    SABOTAGE-PROVED: deleting padding-inline-end fails naming the right edge;
    dropping the negative text-indent fails naming the hang.
    """
    pad = theme_var("--midori-code-pad")
    if pad is None:
        bad("--midori-code-pad is not set; a code line's right padding has no "
            "value to match its left")
        return
    found = code_padding_rules()
    if not found:
        bad(f"no rule sets padding-inline-start/end on {CODE_LINE}; wrapped "
            "code text lands against the right edge of its background")
        return
    for sel, decls in found:
        end = re.search(r"padding-inline-end:\s*([^;]+)", decls)
        start = re.search(r"padding-inline-start:\s*([^;]+)", decls)
        indent = re.search(r"text-indent:\s*([^;]+)", decls)
        if not end:
            bad(f"a code-line rule pads only one side: {sel[:70]}")
            return
        if "var(--midori-code-pad)" not in end.group(1):
            bad(f"padding-inline-end is {end.group(1).strip()!r}, not "
                "var(--midori-code-pad); the two sides must match")
            return
        if not start or "2ch" not in start.group(1):
            bad("padding-inline-start does not add 2ch, so a wrapped line has "
                "nothing to hang from")
            return
        if not indent or "-2ch" not in indent.group(1).replace(" ", ""):
            bad("text-indent is not -2ch, so the FIRST line is pushed in with "
                "the continuations instead of hanging")
            return
    ok(f"code lines pad both sides and hang wrapped lines by 2ch "
       f"({len(found)} rule(s))")


def test_hanging_indent_keeps_the_list_exclusion():
    """:not(.HyperMD-list-line) is load-bearing on every code-padding selector.

    app.css sets padding-inline-start on
    `.markdown-source-view.mod-cm6 .cm-line.HyperMD-codeblock:not(.HyperMD-list-line)`,
    which is ONE CLASS more specific than the same selector without the :not().
    MEASURED without it: the padding never applied (computed 16px) while
    text-indent did, so the first line moved LEFT to 2px and continuations
    stayed at 16 -- worse than no rule, and invisible to any guard that only
    checks the declaration exists.

    CHECK EACH SELECTOR, NOT THE RULE: rules() hands back a comma-separated
    list as one string, so asking whether the exclusion appears anywhere in it
    asks whether ANY selector carries it -- the trap
    test_indent_excludes_non_prose documents.

    SABOTAGE-PROVED: removing the :not() from the selector fails this test.
    """
    found = code_padding_rules()
    if not found:
        bad("no code-line padding rule to check for the list exclusion")
        return
    for sel, _ in found:
        for one in sel.split(","):
            if CODE_LINE not in one:
                continue
            if ":not(.HyperMD-list-line)" not in one:
                bad("a code-line padding selector omits "
                    ":not(.HyperMD-list-line), so app.css out-specifies it and "
                    f"the padding silently does nothing: {' '.join(one.split())[:80]}")
                return
    ok(f"every code-line padding selector keeps :not(.HyperMD-list-line) "
       f"({len(found)} rule(s))")
```

and register both in `__main__` after `test_block_width_has_a_query_container()`.

- [ ] **Step 2: Run them to make sure they fail**

Run: `python3 tests/test_block_geometry.py`
Expected: FAIL — `--midori-code-pad is not set; ...` and `no code-line padding rule to check for the list exclusion`, exit 1.

- [ ] **Step 3: Add the code padding and the hanging indent**

In `obsidian/theme.css`, immediately after the `.markdown-rendered pre code`
rule (currently lines 1833–1835), add:

```css
/* CODE TEXT STOPS AT ITS PADDING, AND A WRAPPED LINE HANGS.
   "The text overruns" turned out to be four separate things, none of them an
   overflow — code wraps in both views. Measured in live preview: a code line
   pads 16px on the left and NOTHING on the right, so wrapped text ended 2.2px
   from the edge of its own background; a wrapped line continued flush left, so
   a continuation read as a new line of code; long tokens break anywhere; and
   the language label overlapped the first line (that last one is the rule
   below this).

   Right padding matches the left. The hang is two characters of the code face:
   padding-inline-start carries it and a negative text-indent pulls the FIRST
   line back out, which is the standard hanging-indent pair. Measured after:
   first line at 16px, continuations at 30px (2ch = 14px here), right gap
   >= 21px, every line still a whole number of rows.

   :not(.HyperMD-list-line) IS LOAD-BEARING, NOT DECORATION. app.css sets
   padding-inline-start on exactly this selector WITH the :not(), which is one
   class more specific than the same selector without it. Measured without it:
   the padding never applied (computed 16px) while text-indent did, so the
   first line moved LEFT to 2px and the continuations stayed at 16 — a worse
   result than no rule at all, and invisible to any check that only asks
   whether the declaration is present.

   Reading view needs none of this: its `pre` already pads both sides, and it
   renders a block as one run of text with no element per line, so there is
   nothing to hang. */
body {
  /* Matches app.css's own padding-inline-start on a code line, so the two
     sides agree by construction rather than by coincidence. */
  --midori-code-pad: 16px;
}
.markdown-source-view.mod-cm6 .cm-line.HyperMD-codeblock:not(.HyperMD-list-line) {
  padding-inline-start: calc(var(--midori-code-pad) + 2ch);
  padding-inline-end: var(--midori-code-pad);
  text-indent: -2ch;
}
```

- [ ] **Step 4: Run the static tests to verify they pass**

Run: `python3 tests/test_block_geometry.py`
Expected: `ok   code lines pad both sides and hang wrapped lines by 2ch (1 rule(s))` and `ok   every code-line padding selector keeps :not(.HyperMD-list-line) (1 rule(s))`, exit 0.

- [ ] **Step 5: Sabotage-prove both**

```bash
cd /Users/benjaminloschen/Projects/midori-terminal
cp obsidian/theme.css /tmp/theme.css.bak
python3 - <<'PY'
import pathlib
p = pathlib.Path("obsidian/theme.css"); s = p.read_text()
s = s.replace("  padding-inline-end: var(--midori-code-pad);\n", "", 1)
p.write_text(s)
PY
python3 tests/test_block_geometry.py; echo "exit $? (want 1, 'pads only one side')"
cp /tmp/theme.css.bak obsidian/theme.css
sed -i '' 's|  text-indent: -2ch;||' obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming the hang)"
cp /tmp/theme.css.bak obsidian/theme.css
sed -i '' 's|.cm-line.HyperMD-codeblock:not(.HyperMD-list-line) {|.cm-line.HyperMD-codeblock {|' obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming the :not())"
cp /tmp/theme.css.bak obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 0)"
```

- [ ] **Step 6: Verify in the app**

The reference note has no code line long enough to wrap at the default measure,
so narrow the measure temporarily to force it, then restore:

```bash
cat > /tmp/wrapcheck.mjs <<'EOF'
const page = (await (await fetch('http://127.0.0.1:9222/json')).json())
  .find((t) => t.type === 'page' && t.title.includes('Obsidian'));
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
const send = (method, params) => new Promise((r) => {
  const id = Math.floor(Math.random() * 1e6);
  const on = (e) => { const m = JSON.parse(e.data);
    if (m.id === id) { ws.removeEventListener('message', on); r(m); } };
  ws.addEventListener('message', on);
  ws.send(JSON.stringify({ id, method, params }));
});
const run = async (measure) => (await send('Runtime.evaluate', {
  returnByValue: true, awaitPromise: true, expression: `
  (async () => {
    const b = document.body;
    const saved = b.style.getPropertyValue('--midori-set-measure');
    if (${measure}) b.style.setProperty('--midori-set-measure', '${measure}');
    await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 400)));
    const p = document.createElement('div');
    p.style.cssText = 'position:absolute;visibility:hidden;line-height:var(--midori-row)';
    b.appendChild(p); const row = parseFloat(getComputedStyle(p).lineHeight); p.remove();
    const out = [];
    for (const l of document.querySelectorAll('.cm-line.HyperMD-codeblock')) {
      if (!l.textContent.trim()) continue;
      const r = document.createRange(); r.selectNodeContents(l);
      const t = [...r.getClientRects()].filter((x) => x.width > 0);
      if (!t.length) continue;
      const bb = l.getBoundingClientRect(), cs = getComputedStyle(l);
      const firsts = t.filter((x, i, a) => i === 0 || Math.round(x.top) !== Math.round(a[i-1].top));
      out.push({text: l.textContent.trim().slice(0, 22),
                rows: +(bb.height / row).toFixed(3),
                first: +(t[0].left - bb.left).toFixed(1),
                cont: firsts.length > 1 ? +(firsts[1].left - bb.left).toFixed(1) : null,
                gap: +(bb.right - Math.max(...t.map((x) => x.right))).toFixed(1)});
    }
    if (${measure}) { if (saved) b.style.setProperty('--midori-set-measure', saved);
                      else b.style.removeProperty('--midori-set-measure'); }
    await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 300)));
    return {row, measure: b.style.getPropertyValue('--midori-set-measure') || '(unset)', out};
  })()` })).result.result.value;
console.log('narrowed:', JSON.stringify(await run(28), null, 1));
console.log('restored:', JSON.stringify(await run(0), null, 1));
ws.close();
EOF
node /tmp/wrapcheck.mjs
```

Expected, with the measure narrowed: every wrapped line has `first: 16`,
`cont: 30`, `gap >= 16`, and `rows` a whole number. And `measure: (unset)` on
the restored run, so the app is left as it was found.

Then: `/tmp/cdpenv/bin/python tests/check_rendered_blocks.py` — `code-right-gap`
turns `ok`, reporting `padding-inline-end: 16px`.

By eye, in the app: click into the middle of a wrapped code line and use the
arrow keys. The caret must follow the hanging indent rather than landing in the
2ch gutter, and the fence lines must still select normally.

- [ ] **Step 7: Lint and commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_block_geometry.py
git commit -m "$(cat <<'EOF'
fix(obsidian): code text stops at its padding, and wrapped lines hang

"The text overruns" was four things, none of them an overflow: a code line
padded 16px left and nothing right, so wrapped text ended 2.2px from the edge
of its own background; a wrapped line continued flush left; long tokens break
anywhere; and the language label overlapped the first line. This fixes the
first two -- right padding matching the left, and a 2ch hanging indent.

:not(.HyperMD-list-line) on the selector is load-bearing: app.css carries it,
so without it the padding loses the specificity contest. Measured without it,
the padding never applied while text-indent did, moving the first line left to
2px -- worse than no rule, and invisible to a guard that only checks the
declaration exists. The static test therefore checks every selector for it.

Measured after: first line 16px, continuations 30px, right gap >= 21px, every
line a whole number of rows.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013rhw75dhAvgnscSB9GHixV
EOF
)"
```

---

### Task 8: The language label and the copy button fit the empty row

**Files:**
- Modify: `obsidian/theme.css` (after the code padding rule)
- Modify: `tests/test_block_geometry.py` (add `test_code_furniture_fits_a_row`, register it)

**Interfaces:**
- Consumes: `--midori-row`, `--midori-code-pad`; `check_rendered_blocks.py` axis `label-overlap`.
- Produces: nothing later tasks read.

- [ ] **Step 1: Write the failing static test**

Append to `tests/test_block_geometry.py`, before `__main__`:

```python
def test_code_furniture_fits_a_row():
    """The language label and the copy button are one row tall and top-aligned.

    MEASURED: .code-block-flair is 32px tall (6px top + 4px vertical padding
    each side on a 24px row) inside a 24px fence row, so it hung 8px into the
    first line of code and overlapped the end of a long one. The reading-view
    copy button does the same over the first line of a <pre>.

    Both blocks already have an empty row for them: the fence row carries no
    code text in live preview, and reading view's <pre> pads a whole row top and
    bottom. Constraining the furniture to one row and pinning it to the top puts
    it in that row instead of over the code.

    THE FENCE LINE IS MADE position: relative DELIBERATELY. `top: 0` is only
    meaningful against a known containing block, and an absolutely positioned
    label resolves against its nearest positioned ancestor -- which, left to
    chance, may be .cm-content and would put the label at the top of the
    document. Positioning the fence line makes the containing block the row we
    mean.

    SABOTAGE-PROVED: removing the height, or the position: relative, fails this
    test naming what went missing.
    """
    needed = {"flair-height": False, "flair-top": False, "fence-relative": False,
              "button-height": False, "button-top": False}
    for sel, decls in rules():
        one_row = re.search(r"height:\s*var\(--midori-row\)", decls)
        top0 = re.search(r"(^|;)\s*top:\s*0", decls)
        if "code-block-flair" in sel:
            needed["flair-height"] |= bool(one_row)
            needed["flair-top"] |= bool(top0)
        if "copy-code-button" in sel:
            needed["button-height"] |= bool(one_row)
            needed["button-top"] |= bool(top0)
        if "HyperMD-codeblock-begin" in sel and re.search(r"position:\s*relative", decls):
            needed["fence-relative"] = True
    missing = [k for k, v in needed.items() if not v]
    if missing:
        for k in missing:
            bad(f"code furniture is unconstrained: {k} is missing; a 32px label "
                "in a 24px row hangs over the first line of code")
        return
    ok("the language label and the copy button are one row tall, top-aligned, "
       "against a positioned fence line")
```

and register it in `__main__` after the two code tests.

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_block_geometry.py`
Expected: five FAIL lines (one per missing key), exit 1.

- [ ] **Step 3: Constrain the furniture**

In `obsidian/theme.css`, immediately after the code padding rule from Task 7,
add:

```css
/* THE LABEL AND THE COPY BUTTON GO IN THE EMPTY ROW, NOT OVER THE CODE.
   Measured: .code-block-flair is 32px tall — 6px from the top plus 4px of
   vertical padding each side — inside a 24px fence row, so it hung 8px into
   the first line and overlapped the end of a long one. Reading view's hover
   copy button does the same over the first line of a <pre>.

   Both blocks already have an empty row for it: the fence row carries no code
   text in live preview, and a reading-view <pre> pads a whole row top and
   bottom (see the code block above). So constrain the furniture to one row and
   pin it to the top of that row.

   THE FENCE LINE IS POSITIONED ON PURPOSE. `top: 0` means nothing without a
   known containing block, and an absolutely positioned label resolves against
   its nearest positioned ancestor — left to chance that could be .cm-content,
   which would put the label at the top of the document rather than the top of
   its block. */
.markdown-source-view.mod-cm6 .cm-line.HyperMD-codeblock-begin {
  position: relative;
}
.markdown-source-view.mod-cm6 .code-block-flair {
  top: 0;
  right: var(--midori-code-pad);
  height: var(--midori-row);
  line-height: var(--midori-row);
  padding-block: 0;
}
.markdown-rendered button.copy-code-button {
  top: 0;
  right: 0;
  margin: 0;
  height: var(--midori-row);
  line-height: var(--midori-row);
  padding-block: 0;
}
```

- [ ] **Step 4: Run the static test to verify it passes**

Run: `python3 tests/test_block_geometry.py`
Expected: `ok   the language label and the copy button are one row tall, top-aligned, against a positioned fence line`, exit 0.

- [ ] **Step 5: Sabotage-prove it**

```bash
cd /Users/benjaminloschen/Projects/midori-terminal
cp obsidian/theme.css /tmp/theme.css.bak
python3 - <<'PY'
import pathlib
p = pathlib.Path("obsidian/theme.css"); s = p.read_text()
s = s.replace(""".markdown-source-view.mod-cm6 .cm-line.HyperMD-codeblock-begin {
  position: relative;
}
""", "", 1)
p.write_text(s)
PY
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming fence-relative)"
cp /tmp/theme.css.bak obsidian/theme.css
python3 - <<'PY'
import pathlib
p = pathlib.Path("obsidian/theme.css"); s = p.read_text()
s = s.replace("""  top: 0;
  right: var(--midori-code-pad);
  height: var(--midori-row);""", """  top: 0;
  right: var(--midori-code-pad);""", 1)
p.write_text(s)
PY
python3 tests/test_block_geometry.py; echo "exit $? (want 1, naming flair-height)"
cp /tmp/theme.css.bak obsidian/theme.css
python3 tests/test_block_geometry.py; echo "exit $? (want 0)"
```

- [ ] **Step 6: Verify in the app**

Run: `/tmp/cdpenv/bin/python tests/check_rendered_blocks.py`
Expected: `label-overlap` `ok` for every code block, with the label now reported
at 24px rather than 32px and no measured overlap. `code-rows` must not move —
the label is absolutely positioned, so it contributes no height.

By eye: hover a code block in reading view and confirm the copy button sits in
the padding row above the code rather than over the first line.

- [ ] **Step 7: Lint and commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_block_geometry.py
git commit -m "$(cat <<'EOF'
fix(obsidian): the language label and copy button sit in the empty row

The flair is 32px tall in a 24px fence row, so it hung 8px into the first line
of code and overlapped the end of a long one; reading view's hover copy button
does the same over the first line of a <pre>. Both blocks already have an empty
row for it -- the fence row carries no code text, and a <pre> pads a whole row
-- so the furniture is now one row tall and pinned to the top of it.

The fence line is made position: relative deliberately: top: 0 is meaningless
without a known containing block, and left to chance the label would resolve
against .cm-content and land at the top of the document.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013rhw75dhAvgnscSB9GHixV
EOF
)"
```

---

### Task 9: Dark mode, a narrow pane, and the whole-suite proof

**Files:**
- Modify: `docs/superpowers/specs/2026-09-15-tables-and-code-blocks-design.md` (mark the open mechanisms resolved, with their measurements)

**Interfaces:**
- Consumes: every rule from Tasks 2–8 and both guards.
- Produces: nothing; this is the closing verification.

- [ ] **Step 1: Prove the rendered checker still fails on a sabotaged stylesheet**

The checker earned its proof in Task 1 against the shipped defects. Now that
every axis is green, prove it again from the other direction — a green checker
that cannot fail is the failure mode this repo keeps hitting:

```bash
cd /Users/benjaminloschen/Projects/midori-terminal
cp obsidian/theme.css /tmp/theme.css.bak
# (a) the four border variables back to 1px
sed -i '' 's/--table-header-border-width: 0px;/--table-header-border-width: 1px;/' obsidian/theme.css
```

Reload the theme in Obsidian (Settings → Appearance → toggle the theme off and
on, or `Cmd+R` to reload the window), then:

```bash
/tmp/cdpenv/bin/python tests/check_rendered_blocks.py; echo "exit $? (want 1, table-rows)"
```

Expected: `table-rows` FAILs naming a table off the row. Then:

```bash
cp /tmp/theme.css.bak obsidian/theme.css
python3 - <<'PY'
import pathlib
p = pathlib.Path("obsidian/theme.css"); s = p.read_text()
s = s.replace("  padding-inline-end: var(--midori-code-pad);\n", "", 1)
p.write_text(s)
PY
```

Reload the theme again, then:

```bash
/tmp/cdpenv/bin/python tests/check_rendered_blocks.py; echo "exit $? (want 1, code-right-gap)"
cp /tmp/theme.css.bak obsidian/theme.css
```

Reload once more and confirm a clean run: `/tmp/cdpenv/bin/python tests/check_rendered_blocks.py; echo "exit $? (want 0)"`

**Note:** the theme file Obsidian reads is the installed copy in each vault, not
this repo's working tree. If editing `obsidian/theme.css` changes nothing in the
app, the vault has its own copy — sabotage the vault's copy at
`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Mud & Silicon/.obsidian/themes/Midori/theme.css`
instead, keeping a backup, and restore it the same way. Do NOT run the installer
to push the change (`CLAUDE.md`: never run an installer to test a change).

- [ ] **Step 2: Check dark mode by eye**

In Obsidian: Settings → Appearance → Base color scheme → Dark. Then look at a
note with a table and a code block and confirm:

- the table rules are visible but not louder than the text;
- the header band is distinguishable from the body rows;
- no dot grid shows through any cell;
- code text is clear of both edges of its background.

Every colour derives from `--text-normal` and `--background-primary`, so the
values follow automatically — this step is checking that the derivation *looks*
right, which derivation alone does not prove. Set the scheme back to Light (or
whatever it was) afterwards.

- [ ] **Step 3: Check a narrow pane**

Open a second pane beside the note (`Cmd+Option+→`, or drag a note to the right
edge) so each pane is roughly half the window, then re-run:

```bash
/tmp/cdpenv/bin/python tests/check_rendered_blocks.py
```

Expected: all axes still hold. Specifically, `breakout` must still report every
table inside its pane: when the pane is narrower than the column plus 96px, the
`max()` in `--midori-block-max` makes the column win and the table stops
breaking out rather than overflowing. Close the second pane afterwards.

- [ ] **Step 4: Run the full suite**

```bash
sh tests/lint.sh
```

Expected: `LINT: all green`, including the `== block geometry ==` section with
every test from this plan.

- [ ] **Step 5: Record the outcome in the spec**

In `docs/superpowers/specs/2026-09-15-tables-and-code-blocks-design.md`, replace
the `## Open for the plan` heading and its intro line:

```markdown
## Open for the plan

These need a measurement before code is written, not a guess:
```

with:

```markdown
## Open for the plan — all resolved by measurement

Each was measured in the running app before the code was written:

- **Pane width in CSS:** `container-type: inline-size` on each view's scroller,
  read with `100cqi`. Measured 1364px in live preview (`.cm-scroller`) and
  1364px in reading view (`.markdown-preview-view`) — the 1428px pane less 32px
  of scroller padding each side — against 1728px, the window, with no
  container. Layout byte-identical before/during/after in both views, scrolling
  intact, and no new re-anchoring of fixed descendants.
- **Reading-view breakout:** nothing clips. The block wrapper is `div.el-table`,
  the sizer's direct child, already carrying `overflow-x: auto`. Widened to
  1040px it centred at 494–1534 in the 1428px view, grew 384.8px, cells went
  101.2 → 216.1px, height unchanged, no sideways scroll, both far edges
  hit-tested as `th`. The inner `table` is content-sized and needs telling to
  fill the new width.
- **Spacing around code in live preview:** the row comes from the blank line
  already in the document, given `line-height: var(--midori-row)` through
  `:has()`. Measured 0 → 24px on all four sides, with block height, corner
  radius and background untouched.
- **Hanging indent mechanics:** `padding-inline-start: calc(16px + 2ch)` plus
  `text-indent: -2ch`, on a selector that keeps `:not(.HyperMD-list-line)` —
  load-bearing, because app.css carries it and out-specifies the rule without
  it. Measured first line 16px, continuations 30px, right gap ≥21px, all lines
  whole rows.
- **Dark mode and a narrow pane:** checked by eye and by re-running the
  rendered checker in a split pane; the narrow case is what the `max()` floor in
  `--midori-block-max` exists for.

The original wording of this section follows, for the record:

These need a measurement before code is written, not a guess:
```

- [ ] **Step 6: Lint and commit**

```bash
sh tests/lint.sh
git add docs/superpowers/specs/2026-09-15-tables-and-code-blocks-design.md
git commit -m "$(cat <<'EOF'
spec: the four open mechanisms, resolved by measurement

Pane width via a query container on each view's scroller (1364px measured in
both, against 1728px with no container); reading view clips nothing (a table
widened to 1040px centred at 494-1534 with no sideways scroll); air from the
blank line via :has(); and the hanging indent, whose :not(.HyperMD-list-line)
is load-bearing. The original wording is kept below the resolutions rather than
replaced.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013rhw75dhAvgnscSB9GHixV
EOF
)"
```

- [ ] **Step 7: Report, and leave installing to the user**

Print the final state for the user: the last `check_rendered_blocks.py` output,
the `LINT: all green` line, and the commit list (`git log --oneline` for this
plan's commits).

Do NOT install into the vaults. The spec ends "Installing into the vaults
happens after the checks pass, through the unchanged `install.sh` /
`obsidian/install-obsidian.sh`" — that writes into nine real vaults and is the
user's call. Offer it; do not run it.

---

## Self-Review

**1. Spec coverage.** Walking the spec section by section:

| Spec requirement | Task |
|---|---|
| Tables off the grid: four border variables → `0px` | 2 |
| The false `7.042 -> 8.000` comment corrected, saying what is and is not established | 2 |
| Cells get half a row of padding on all four sides; a row is `row × (lines + 1)` | 3 |
| Rules stay painted (box-shadow + outline), not laid out | 3 (preserved; not re-declared) |
| Rules `color-mix(… 28% …)`, header band `… 9% …`, cells `--background-primary`, header weight 600 | 4 |
| Every colour derives from theme variables; dark mode still checked by eye | 4, 9 |
| The table block gets a row above and below and still totals whole rows | 5 |
| Width: at least the column; grows symmetrically to `min(1.6 × column, pane − 96px)`; column wins when the ceiling is below it; past the ceiling Obsidian's scroll applies | 6 |
| Code: right padding equal to the left | 7 |
| Code: wrapped continuations indent two characters; reading view keeps plain wrapping | 7 |
| Label and copy button fit the empty row and overlap no code text | 8 |
| Code spacing: one row above and below, still whole rows | 5 (same `:has()` rules cover code and tables) |
| Wrapping stays; long tokens still break anywhere | not changed, by design — no task |
| Static check in `tests/lint.sh`: four variables `0px`, cell padding half a row, failing when either is removed | 2, 3 |
| Rendered check: whole rows, paragraph phase, 16px code gap, label overlap, window by content, prints what it measured, fails on an empty set | 1 |
| Every guard sabotage-proved | 2–8 step "Sabotage-prove", plus 1 and 9 for the rendered checker |
| Dark mode, wide and narrow pane, both views | 9 |
| Out of scope: HTML comments, Style Settings controls, treatments A and B | no task, correctly |

No gaps. Two spec items are deliberately no-ops (wrapping stays; long tokens
still break), and the plan says so rather than inventing work for them.

**2. Placeholder scan.** No "TBD", no "TODO", no "add error handling", no
"similar to Task N". Every code step carries the actual CSS, Python, or shell.
Two steps carry a contingency with the exact edit to make if a measurement comes
back a specific way (Task 4 step 8 on `!important`, Task 9 step 1 on the vault's
theme copy) — those are decision rules with both branches written out, not
deferred work.

**3. Type and name consistency.** Checked across tasks:

- `--midori-cell-pad` (3) → read in 3, 4; asserted in 3.
- `--table-border-color` redefined (4) → read by the box-shadow and outline that
  already existed in the Tables region.
- `--midori-table-header-bg` (4) → read in 4 both views.
- `--midori-block-max` (6) → read in 6 both views.
- `--midori-code-pad` (7) → read in 7 and in 8 (`right: var(--midori-code-pad)`).
- Axis names from Task 1 (`table-rows`, `code-rows`, `paragraph-phase`,
  `code-right-gap`, `label-overlap`, `cell-opacity`, `breakout`) are used
  verbatim in 2, 4, 5, 6, 7, 8, 9.
- `tests/test_block_geometry.py` imports `FAIL, bad, ok, rules, theme_var` from
  `test_prose_typography` in Task 2 and uses only those names thereafter;
  `code_padding_rules()` is defined in Task 7 and used by both Task 7 tests.
- Every test added is registered in `__main__`, in the order the tasks add them.
