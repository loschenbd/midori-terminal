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
import time
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

THEME_STATE = r"""
(() => {
  const p = document.createElement('div');
  p.style.cssText = 'position:absolute;visibility:hidden;line-height:var(--midori-row)';
  document.body.appendChild(p);
  const row = parseFloat(getComputedStyle(p).lineHeight);
  p.remove();
  // A sheet is identified by the RULES it contains, not by its name. Matching
  // ownerNode.id against /midori/i finds midori-timer-style and misses the
  // theme, which is injected as an unnamed inline <style>.
  let rules = null;
  for (const s of document.styleSheets) {
    let n = 0; try { n = s.cssRules.length; } catch (e) { continue; }
    for (let i = 0; i < Math.min(n, 400); i++) {
      const txt = s.cssRules[i].cssText || '';
      if (txt.includes('--midori-row') || txt.includes('--midori-set-measure')) { rules = n; break; }
    }
    if (rules) break;
  }
  let empty = 0;
  for (const s of document.styleSheets) { try { if (s.cssRules.length === 0) empty++; } catch (e) {} }
  return {row, themeSheet: rules, emptySheets: empty,
          drawn: document.body.classList.contains('midori-drawn'),
          indent: getComputedStyle(document.body).getPropertyValue('--midori-indent').trim()};
})()
"""

FAIL = []


def ok(axis, msg):
    print(f"  ok   [{axis}] {msg}")


def bad(axis, msg):
    print(f"  FAIL [{axis}] {msg}")
    FAIL.append(axis)


def require_theme_loaded(ws, samples=3, gap=0.7):
    """Refuse to measure unless the theme is loaded in EVERY sample.

    THIS GATE EXISTS BECAUSE ITS ABSENCE ALREADY PRODUCED A WRONG CONCLUSION.
    A probe took ONE sample while Obsidian was swapping the theme's <style>
    element: every --midori-* variable read unset, body had lost
    midori-drawn, --file-line-width was Obsidian's default 700px, and one
    inline sheet held 0 rules. Each number was correct. The conclusion drawn
    beside them -- "the theme is not loaded, this cannot run" -- was wrong:
    the theme was loaded seconds before and seconds after. One sample of a
    reloading stylesheet is not a state; three agreeing samples are.

    Why it is fatal rather than a warning: a themeless window does not FAIL
    the axes below, it measures Obsidian's own defaults and reports them with
    full confidence. That is the precise failure this file's docstring exists
    to prevent, and it is cheaper to refuse than to explain afterwards.
    """
    seen = []
    for i in range(samples):
        seen.append(evaluate(ws, THEME_STATE))
        if i < samples - 1:
            time.sleep(gap)
    for s in seen:
        print(f"  theme: row={s['row']} drawn={s['drawn']} indent={s['indent']!r} "
              f"themeSheetRules={s['themeSheet']} emptySheets={s['emptySheets']}")
    good = [s for s in seen
            if s["row"] == 24 and s["themeSheet"] and s["drawn"] and s["indent"]]
    if len(good) != samples:
        sys.exit(f"theme not loaded in {samples - len(good)} of {samples} samples. "
                 "Every sample must show row=24, a stylesheet carrying "
                 "--midori-row, body.midori-drawn, and a resolved "
                 "--midori-indent. A themeless window measures Obsidian's "
                 "defaults and would report them as results. If this fires "
                 "repeatedly, re-select the theme in Settings -> Appearance; "
                 "if it fires once, the theme was mid-reload -- just re-run.")
    print(f"theme loaded in all {samples} samples\n")


def main():
    ws = pick_window()
    require_theme_loaded(ws)
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
