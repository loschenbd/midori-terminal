'use strict';

/* Midori Caret — draw the editor caret, the selection band and the note-title
 * caret as elements the theme can size.
 *
 * WHY THIS EXISTS. The Midori theme renders prose in font faces carrying
 * symmetric metric overrides (ascent-override: 45%, descent-override: 45%).
 * That is what puts every baseline at exactly line-height/2 and lets the whole
 * theme use plain multiples of the 24px row instead of a per-heading ladder of
 * magic numbers. The cost lands on everything the BROWSER draws from font
 * metrics rather than from glyph outlines:
 *
 *   - the caret. Chromium takes its height from the font's content area, which
 *     symmetric metrics make symmetric about the baseline, so it runs
 *     [baseline +/- 0.45em] while the glyphs run about 0.72em up and 0.22em
 *     down — a short tick sitting ~3px too low.
 *   - the selection band. Native selection paints the line box, and the
 *     baseline is at its centre, so the band is 24px with the ink crowded into
 *     its top half: measured 1.5px of tan above the ascenders and 12.25px
 *     below the baseline. It reads as a band the text is sitting on top of
 *     rather than one drawn around the text.
 *
 * No CSS reaches either. `caret-color` is the only property that touches the
 * native caret and it only sets the colour; `::selection` accepts colour
 * properties only, never geometry. So this plugin hides both natives and draws
 * replacements the theme can size.
 *
 * THE ONE PROPERTY THAT MAKES THE CSS SIMPLE: because A = D, the baseline is
 * the vertical CENTRE of a text box — of the 0.9em font content area AND of
 * the 24px line box, since line-height centring puts the baseline at L/2 too.
 * So `top: 50%` of any rect handed to us here is the baseline, whichever of
 * the two CodeMirror happened to measure. Every rule in theme.css leans on
 * that instead of on a font size it cannot see.
 *
 * WHY NOT drawSelection(). CodeMirror ships drawSelection(), which would draw
 * the band in one line — but it replaces the selection MECHANISM, and
 * Obsidian's live preview leans on native selection for widget interaction and
 * IME. This uses the layer() primitive, which only draws: the real selection
 * stays native and keeps behaving, and the theme merely paints it transparent
 * so there is no doubled band. That is the whole reason for the extra code.
 */

const { Plugin, Notice, Platform } = require('obsidian');
const cmView = require('@codemirror/view');

/* THE SELECTION HALF IS DESKTOP-ONLY, and this is a platform limit rather than
 * a preference. Both replacements work by painting the native out and drawing
 * over it, and on iOS only one of those two natives can be painted out:
 *
 *   caret-color: transparent                    -> honoured
 *   ::selection { background-color: transparent } -> IGNORED
 *
 * Measured in the iOS Simulator against a plain contenteditable, not inferred:
 * with the ::selection rule applied and computing to rgba(0,0,0,0), iOS still
 * drew its full selection band with handles. The highlight on an editable is
 * UIKit's text-interaction UI drawn ABOVE the web content, not a CSS-painted
 * background, so no stylesheet reaches it. (The caret is drawn by WebKit's own
 * editing code and does respect caret-color — verified the same way: the
 * native caret blinked across 4 of 8 frames without the rule and 0 of 8 with
 * it.)
 *
 * So on mobile the band is drawn UNDER a native band that cannot be removed.
 * The first attempt at that read as a doubled highlight — two offset slabs of
 * colour — and the band was made desktop-only. That was the wrong conclusion:
 * the problem was the geometry, not the drawing.
 *
 * What mobile's band actually is, measured off a dark-mode iPhone screenshot:
 * every pixel of the selected region multiplied by 0.8. Ground 26,25,23 ->
 * 21,20,18, dot-grid dots 49,53,51 -> 39,43,40, and — the part that settles it
 * — the TEXT too, 234,232,227 -> 187,185,181. A selection background sits
 * behind the glyphs and cannot dim them. This one is a translucent black scrim
 * composited on top of everything, which is exactly what "UIKit above the web
 * content" looks like from inside the page.
 *
 * That makes it unrecolourable (nothing behind it can change what it paints)
 * but also see-through: a band drawn underneath comes back at 80%, which is
 * plenty. The whole job is to make our band the same SHAPE as the scrim, so
 * the two read as one highlight. Measured off the same screenshot, the scrim
 * is the plain line box — 288 device px for 4 rows at 3x, i.e. exactly 4 x 24
 * CSS px, contiguous, with no gap between rows — and full-width across every
 * row but the first and last. BLOCK_ROWS below builds that shape; theme.css
 * supplies the matching 12px/12px slot under body.is-mobile. */
const IS_MOBILE = !!(Platform && Platform.isMobile);
/* The title band stays desktop-only. Its slot is in em against the title's own
 * face rather than the 24px prose line box, so squaring it off against the
 * native scrim is a separate measurement, and the title is not where anyone
 * drags a selection. */
const TITLE_SELECTION_IS_SUPPORTED = !IS_MOBILE;
const BLOCK_ROWS = IS_MOBILE;

const CURSOR_LAYER = 'midori-cursorLayer';
const CURSOR_CLASS = 'midori-cursor';
const SELECTION_LAYER = 'midori-selectionLayer';
const SELECTION_CLASS = 'midori-selection';
const TITLE_CARET_CLASS = 'midori-title-caret';
const TITLE_SELECTION_CLASS = 'midori-title-selection';

const BODY_CLASS = 'midori-caret-active';
const SELECTION_BODY_CLASS = 'midori-selection-active';
const TITLE_BODY_CLASS = 'midori-title-caret-active';
const TITLE_SELECTION_BODY_CLASS = 'midori-title-selection-active';
// New in the build that moved the title caret's height out of this file and
// into theme.css. Older builds set an inline height and never set the bar's
// font-size, so the em-based rules would resolve against the body's 16px and
// draw the caret ~13px high — hence a class those builds do not set.
const TITLE_SLOT_BODY_CLASS = 'midori-title-slot-active';

/* THIS PLUGIN IS ONLY MEANINGFUL UNDER THE MIDORI STYLESHEET. Obsidian installs
 * plugins per VAULT but themes are chosen per vault too, so a vault can easily
 * end up with this plugin enabled and a different theme selected — which is
 * exactly what happened: a vault running an unrelated theme had the body
 * classes set and invisible markers drawn into it, because nothing there styles
 * .midori-selection. Harmless by luck rather than by design, and it would stop
 * being harmless the moment another theme used one of these class names.
 *
 * Detected by probing for a custom property the theme defines rather than by
 * comparing the theme NAME, so a renamed copy or a fork that pulls in these
 * rules still works. The check is re-run on every css-change, which is what
 * Obsidian fires when the theme is switched. */
const THEME_SENTINEL = '--midori-slot-rise';

function midoriStylesheetActive() {
  return getComputedStyle(document.body).getPropertyValue(THEME_SENTINEL).trim() !== '';
}

/* The blink is restarted by flipping between two identical keyframes, the same
 * trick CodeMirror uses: re-assigning the same animation name would not
 * retrigger it, so the caret would keep blinking on its old schedule and could
 * be invisible at the moment you start typing. */
function flipBlink(el) {
  el.style.animationName =
    el.style.animationName === 'midori-blink' ? 'midori-blink2' : 'midori-blink';
}

/* THE INVARIANT EVERY RULE IN theme.css DEPENDS ON: one marker == one visual
 * row. The stylesheet takes `top: 50%` of a marker as the baseline, which is
 * only true for a box that is one row tall — the 0.9em content area and the
 * 24px line box are both centred on the baseline under A = D, but a box
 * spanning SEVERAL rows is centred on nothing.
 *
 * RectangleMarker.forRange breaks that invariant by design. For anything
 * larger than a single row it returns three pieces — the first partial row,
 * the last partial row, and ONE block rectangle covering everything between:
 *
 *   selection across 4 wrapped rows -> h=14, h=82 (3.42 rows), h=14
 *   selection across 3 logical lines -> h=14, h=106 (4.42 rows), h=14
 *
 * The middle piece then got a single 19px band at its centre and every row
 * inside it went unpainted — a selection with holes, plus a stray bar floating
 * in the gap. It looked correct for a year of single-row selections because
 * those are the one case forRange does not decompose.
 *
 * So don't ask CodeMirror where the rows are; ask the browser. A DOM Range's
 * getClientRects() IS the line-box decomposition — one rect per visual row, at
 * that row's own font size, which is what makes this work across headings and
 * wrapped lines alike rather than assuming a 24px pitch. An empty line comes
 * back as its 24px line box, so blank lines inside a selection still paint,
 * and both boxes satisfy the 50% rule. */
function layerBase(view) {
  // Mirrors CodeMirror's own (unexported) getBase, which is what marker
  // coordinates are relative to.
  const rect = view.scrollDOM.getBoundingClientRect();
  const scaleX = view.scaleX || 1;
  const scaleY = view.scaleY || 1;
  const rtl = cmView.Direction && view.textDirection === cmView.Direction.RTL;
  const left = rtl
    ? rect.right - view.scrollDOM.clientWidth * scaleX
    : rect.left;
  return {
    left: left - view.scrollDOM.scrollLeft * scaleX,
    top: rect.top - view.scrollDOM.scrollTop * scaleY,
  };
}

function rowMarkers(view, markerClass, range) {
  const { RectangleMarker } = cmView;
  let rects;
  try {
    const start = view.domAtPos(range.from);
    const end = view.domAtPos(range.to);
    const dom = document.createRange();
    dom.setStart(start.node, start.offset);
    dom.setEnd(end.node, end.offset);
    rects = Array.from(dom.getClientRects());
  } catch (err) {
    // domAtPos can land inside a widget/decoration it cannot map. Falling back
    // to forRange is worse geometry, not no geometry.
    return RectangleMarker.forRange(view, markerClass, range);
  }

  const base = layerBase(view);
  const live = rects.filter((r) => r.width > 0 && r.height > 0);

  /* SQUARE OFF THE MIDDLE ROWS when we are drawing under a native scrim we
   * cannot remove (see BLOCK_ROWS). getClientRects hugs the text, so a row
   * ending mid-line leaves the rest of that row to the scrim alone — a ragged
   * sage edge with a dark tail past it, which is the doubling complaint in
   * another form. Every row except the one the selection starts on runs from
   * the content's left edge, and every row except the one it ends on runs to
   * the right edge, which is the same three-piece shape the scrim uses. */
  const content = BLOCK_ROWS && live.length > 1
    ? view.contentDOM.getBoundingClientRect()
    : null;

  const out = [];
  live.forEach((r, i) => {
    const left = content && i > 0 ? content.left : r.left;
    const right = content && i < live.length - 1 ? content.right : r.right;
    out.push(new RectangleMarker(
      markerClass, left - base.left, r.top - base.top, right - left, r.height,
    ));
  });
  return out.length ? out : RectangleMarker.forRange(view, markerClass, range);
}

/* A caret for a NON-EMPTY range, i.e. the blinking bar at the end you are
 * dragging. theme.css paints the native caret out inside .cm-content, and this
 * layer used to skip non-empty ranges entirely — so selecting anything left no
 * caret at all, native or drawn. CodeMirror's own drawSelection does the same
 * thing via its drawRangeCursor option, which defaults to on.
 *
 * Duck-typed rather than built with EditorSelection.cursor(): forRange's empty
 * branch reads only .empty, .head and .assoc, so this avoids taking a second
 * externalised CodeMirror module as a dependency just to make one object. */
function headCursor(range) {
  if (range.empty) return range;
  return {
    empty: true,
    from: range.head,
    to: range.head,
    head: range.head,
    assoc: range.head > range.anchor ? -1 : 1,
  };
}

/* Both layers are the same shape: collect RectangleMarkers for the ranges we
 * care about and let CSS do the rest. `wantEmpty` picks which one this is —
 * the caret draws for EVERY range (at its head), the band only for non-empty
 * ones. */
function buildLayer({ cls, markerClass, above, wantEmpty }) {
  const { layer, RectangleMarker } = cmView;
  if (!layer || !RectangleMarker) return null;

  return layer({
    above,
    class: cls,

    markers(view) {
      const out = [];
      for (const range of view.state.selection.ranges) {
        if (wantEmpty) {
          for (const piece of RectangleMarker.forRange(view, markerClass, headCursor(range))) {
            out.push(piece);
          }
        } else if (!range.empty) {
          for (const piece of rowMarkers(view, markerClass, range)) out.push(piece);
        }
      }
      return out;
    },

    update(update, dom) {
      if (wantEmpty) {
        /* STEADY WHILE A RANGE IS SELECTED. The blink lives on the layer, so
         * once the caret started being drawn at the head of a non-empty range
         * it inherited it — and a caret flashing on and off at the end of a
         * highlight reads as the selection itself flickering. It marks where
         * the selection ends, which is a position, not an invitation to type
         * there, so it holds still until the selection collapses.
         *
         * Driven by the inline animation-name rather than a class, because
         * flipBlink already owns that property; a stylesheet rule would have
         * to fight it with !important. 'none' also gives flipBlink a value it
         * does not recognise, so the branch below restores a real keyframe
         * name the moment the selection collapses. */
        const hasRange = update.state.selection.ranges.some((r) => !r.empty);
        if (hasRange) {
          dom.style.animationName = 'none';
        } else if (
          dom.style.animationName === 'none'
          || update.transactions.some((tr) => tr.selection)
        ) {
          flipBlink(dom);
        }
      }
      // geometryChanged matters: a font finishing loading or the pane being
      // resized moves both without touching doc or selection.
      return update.docChanged || update.selectionSet || update.geometryChanged;
    },
  });
}

/* THE NOTE TITLE IS NOT IN CODEMIRROR. `.inline-title` is its own
 * contenteditable, outside .cm-content, so neither the layers above nor
 * theme.css's rules scoped to .cm-content reach it — which is why the title
 * kept the dropped native caret after the editor stopped having one, and then
 * kept the native selection band after the editor stopped having that too. It
 * has no CodeMirror view to hang a layer on, so this draws both directly off
 * the DOM selection.
 *
 * NEITHER ONE CARRIES ITS GEOMETRY HERE. Both get the title's own font-size
 * copied onto them, and theme.css sizes them in em off --midori-title-slot-*
 * — one slot, two renderings, the same arrangement the prose caret and band
 * have. That division matters because the title is the one place in the theme
 * whose font size is a user setting, so its slot has to track the glyphs
 * rather than the 24px row. All this code supplies is the BASELINE.
 *
 * The caret's height used to be computed here, as 0.82 of the measured caret
 * box. That ratio predates any measurement of the rendered face: it put the
 * bar 0.4px short of Spectral's ascenders and stopped it dead on the baseline,
 * so it cleared no descender at all. */

/* theme.css sizes the title caret and the title bands in em, and both live
 * OUTSIDE .inline-title — so they carry the title's own font size and the em
 * resolves against the face they are wrapping rather than against the body. */
function titleEm(title) {
  return `${parseFloat(getComputedStyle(title).fontSize) || 16}px`;
}

/* Which .inline-title, if any, the range is in. Ranges normalise so that start
 * precedes end, so dragging up out of the title still puts the title end at
 * `start` — but either endpoint can also be an ancestor element when the drag
 * left the title entirely, hence the fallback scan. */
function titleFor(range) {
  for (const node of [range.startContainer, range.endContainer]) {
    const el = node && (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement);
    const hit = el && el.closest && el.closest('.inline-title');
    if (hit) return hit;
  }
  for (const candidate of document.querySelectorAll('.inline-title')) {
    if (range.intersectsNode(candidate)) return candidate;
  }
  return null;
}

/* A selection dragged from the title down into the note is ONE range covering
 * both, and its rects would then include every prose line — which the editor's
 * own layer is already drawing. Clip to the title's contents so each surface
 * paints exactly its own half. */
function clipToTitle(range, title) {
  const bounds = document.createRange();
  bounds.selectNodeContents(title);
  const clipped = range.cloneRange();
  if (clipped.compareBoundaryPoints(Range.START_TO_START, bounds) < 0) {
    clipped.setStart(bounds.startContainer, bounds.startOffset);
  }
  if (clipped.compareBoundaryPoints(Range.END_TO_END, bounds) > 0) {
    clipped.setEnd(bounds.endContainer, bounds.endOffset);
  }
  return clipped.collapsed ? null : clipped;
}

function setupTitleOverlay(plugin) {
  const bar = document.createElement('div');
  bar.className = TITLE_CARET_CLASS;
  bar.style.display = 'none';
  document.body.appendChild(bar);

  // One band per visual line of the selection; the pool is reused rather than
  // rebuilt so a drag does not churn the DOM on every selectionchange.
  const bands = [];
  plugin.register(() => {
    bar.remove();
    for (const band of bands) band.remove();
  });

  const hideBandsFrom = (from) => {
    for (let i = from; i < bands.length; i += 1) bands[i].style.display = 'none';
  };
  const hide = () => {
    bar.style.display = 'none';
    hideBandsFrom(0);
  };

  const drawCaret = (range, title) => {
    hideBandsFrom(0);

    // A collapsed range in an empty title has no rects at all; fall back to the
    // element box, which has the same metric centring.
    let rect = range.getBoundingClientRect();
    if (!rect || (rect.height === 0 && rect.width === 0 && rect.top === 0)) {
      rect = title.getBoundingClientRect();
    }
    if (!rect.height) return hide();

    // A = D, so the box centres on the baseline — see the header comment.
    // `top` IS the baseline; theme.css lifts the bar by the slot's rise and
    // carries it the drop past, exactly as it does for the bands.
    const baseline = rect.top + rect.height / 2;

    bar.style.display = 'block';
    bar.style.fontSize = titleEm(title);
    bar.style.left = `${rect.left}px`;
    bar.style.top = `${baseline}px`;
    flipBlink(bar);
  };

  const drawBands = (range, title) => {
    bar.style.display = 'none';
    // The title band is desktop-only — see TITLE_SELECTION_IS_SUPPORTED.
    if (!TITLE_SELECTION_IS_SUPPORTED) return hideBandsFrom(0);

    const clipped = clipToTitle(range, title);
    if (!clipped) return hide();

    const rects = Array.from(clipped.getClientRects())
      .filter((r) => r.width > 0 && r.height > 0);
    if (!rects.length) return hide();

    // The bands live next to the title rather than on <body> so they scroll
    // with it instead of being chased by a scroll handler.
    const host = title.parentElement || document.body;

    rects.forEach((rect, i) => {
      while (bands.length <= i) {
        const fresh = document.createElement('div');
        fresh.className = TITLE_SELECTION_CLASS;
        bands.push(fresh);
      }
      const band = bands[i];
      if (band.parentElement !== host) host.appendChild(band);
      band.style.display = 'block';

      // Positioned against whatever containing block the host resolved to,
      // which is only knowable once the element is laid out.
      const origin = (band.offsetParent || host).getBoundingClientRect();
      const baseline = rect.top + rect.height / 2; // A = D again

      // JS supplies the baseline; the rise above it and the drop below it stay
      // in CSS — see titleEm above for why the font size comes along.
      band.style.fontSize = titleEm(title);
      band.style.left = `${rect.left - origin.left}px`;
      band.style.width = `${rect.width}px`;
      band.style.top = `${baseline - origin.top}px`;
    });

    hideBandsFrom(rects.length);
  };

  plugin.hideTitleOverlay = hide;

  const place = () => {
    // Nothing here is styled unless the Midori stylesheet is loaded, and the
    // vault may have switched to another theme since load.
    if (!midoriStylesheetActive()) return hide();

    const sel = document.getSelection();
    if (!sel || sel.rangeCount === 0) return hide();

    const range = sel.getRangeAt(0);
    const title = titleFor(range);
    if (!title) return hide();

    if (range.collapsed) drawCaret(range, title);
    else drawBands(range, title);
  };

  // selectionchange is the only event that fires for every way the caret can
  // move (typing, arrows, clicking, undo). The rest are for cases where the
  // caret does not move but its SCREEN position does. The bands are positioned
  // inside the title's own container, so scroll only matters to the caret.
  plugin.registerDomEvent(document, 'selectionchange', place);
  plugin.registerDomEvent(window, 'resize', place);
  plugin.registerDomEvent(document, 'scroll', place, true);
  plugin.registerDomEvent(document, 'focusout', (e) => {
    if (e.target && e.target.closest && e.target.closest('.inline-title')) hide();
  });

  return place;
}

module.exports = class MidoriCaret extends Plugin {
  onload() {
    const caretLayer = buildLayer({
      cls: CURSOR_LAYER, markerClass: CURSOR_CLASS, above: true, wantEmpty: true,
    });
    const selectionLayer = buildLayer({
      cls: SELECTION_LAYER, markerClass: SELECTION_CLASS, above: false, wantEmpty: false,
    });

    if (!caretLayer || !selectionLayer) {
      // Obsidian externalises @codemirror/view, so which version is present is
      // the app's business, not ours. Say so rather than failing silently and
      // leaving the user with an invisible caret or an invisible selection.
      new Notice(
        'Midori Caret: this Obsidian build does not expose the CodeMirror ' +
          'layer API, so the caret and selection are left as the browser draws them.',
        10000,
      );
      return;
    }

    this.registerEditorExtension(
      [caretLayer, selectionLayer],
    );

    // The theme hides the natives ONLY under these classes, so theme.css stays
    // correct on its own — uninstall the plugin and the native caret and
    // selection come back, rather than the editor losing both entirely. They
    // are separate classes rather than one so the selection half can be
    // switched off (it repaints a band Obsidian usually leaves to the
    // compositor) without giving up the caret — which is exactly what mobile
    // needs, since the native band there cannot be painted out at all.
    this.syncTheme = () => {
      const on = midoriStylesheetActive();
      const cls = document.body.classList;
      cls.toggle(BODY_CLASS, on);
      cls.toggle(SELECTION_BODY_CLASS, on);
      cls.toggle(TITLE_BODY_CLASS, on);
      cls.toggle(TITLE_SELECTION_BODY_CLASS, on && TITLE_SELECTION_IS_SUPPORTED);
      cls.toggle(TITLE_SLOT_BODY_CLASS, on);
      if (!on && this.hideTitleOverlay) this.hideTitleOverlay();
    };

    setupTitleOverlay(this);
    // Added LAST and only after setupTitleOverlay has actually installed its
    // listeners: these classes are what make theme.css hide the native title
    // caret and the native title selection, so anything that throws above must
    // leave the natives alone rather than trade them for nothing. It is also
    // why they are separate classes from BODY_CLASS — see the matching note in
    // theme.css. TITLE_SELECTION_BODY_CLASS is separate from TITLE_BODY_CLASS
    // for the same reason again: the 1.1.0 build already set the caret class,
    // so hanging the new ::selection rule on it would have blanked the title
    // selection for anyone running the new CSS against the old code.
    this.syncTheme();
    // Obsidian fires css-change when the theme is switched, so a vault that
    // moves on or off Midori picks this up without a reload.
    this.registerEvent(this.app.workspace.on('css-change', () => this.syncTheme()));
  }

  onunload() {
    document.body.classList.remove(BODY_CLASS);
    document.body.classList.remove(SELECTION_BODY_CLASS);
    document.body.classList.remove(TITLE_BODY_CLASS);
    document.body.classList.remove(TITLE_SELECTION_BODY_CLASS);
    document.body.classList.remove(TITLE_SLOT_BODY_CLASS);
  }
};
