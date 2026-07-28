'use strict';

/* Midori Caret — draw the editor caret as an element the theme can size.
 *
 * WHY THIS EXISTS. The Midori theme renders prose in font faces carrying
 * symmetric metric overrides (ascent-override: 45%, descent-override: 45%).
 * That is what puts every baseline at exactly line-height/2 and lets the whole
 * theme use plain multiples of the 24px row instead of a per-heading ladder of
 * magic numbers. The cost is the caret: Obsidian's editor is a plain
 * contenteditable, so the caret is the BROWSER's, and Chromium takes its height
 * from the font's content area. Symmetric metrics make that area symmetric
 * about the baseline, so the caret runs [baseline +/- 0.45em] while the glyphs
 * run about 0.72em up and 0.22em down — a short tick sitting ~3px too low.
 *
 * No CSS can fix that. `caret-color` is the only property that touches the
 * native caret, and it only sets the colour. So this plugin hides the native
 * caret and draws its own, which the theme then sizes with a transform.
 *
 * WHY NOT drawSelection(). CodeMirror ships drawSelection(), which would do
 * this in one line — but it replaces the native SELECTION too, and Obsidian's
 * live preview leans on native selection for widget interaction and IME. This
 * uses the same primitives (layer + RectangleMarker) to draw cursors ONLY,
 * leaving selection rendering exactly as Obsidian had it. That is the whole
 * reason for the extra thirty lines.
 */

const { Plugin, Notice } = require('obsidian');
const cmView = require('@codemirror/view');

const LAYER_CLASS = 'midori-cursorLayer';
const CURSOR_CLASS = 'midori-cursor';
const BODY_CLASS = 'midori-caret-active';

/* The blink is restarted by flipping between two identical keyframes, the same
 * trick CodeMirror uses: re-assigning the same animation name would not
 * retrigger it, so the caret would keep blinking on its old schedule and could
 * be invisible at the moment you start typing. */
function buildCaretLayer() {
  const { layer, RectangleMarker } = cmView;
  if (!layer || !RectangleMarker) return null;

  return layer({
    above: true,
    class: LAYER_CLASS,

    markers(view) {
      const out = [];
      for (const range of view.state.selection.ranges) {
        if (!range.empty) continue; // ranges keep the native selection
        for (const piece of RectangleMarker.forRange(view, CURSOR_CLASS, range)) {
          out.push(piece);
        }
      }
      return out;
    },

    update(update, dom) {
      if (update.transactions.some((tr) => tr.selection)) {
        dom.style.animationName =
          dom.style.animationName === 'midori-blink' ? 'midori-blink2' : 'midori-blink';
      }
      // geometryChanged matters: a font finishing loading or the pane being
      // resized moves the caret without touching doc or selection.
      return update.docChanged || update.selectionSet || update.geometryChanged;
    },
  });
}

module.exports = class MidoriCaret extends Plugin {
  onload() {
    const caretLayer = buildCaretLayer();

    if (!caretLayer) {
      // Obsidian externalises @codemirror/view, so which version is present is
      // the app's business, not ours. Say so rather than failing silently and
      // leaving the user with an invisible caret.
      new Notice(
        'Midori Caret: this Obsidian build does not expose the CodeMirror ' +
          'layer API, so the caret is left as the browser draws it.',
        10000,
      );
      return;
    }

    this.registerEditorExtension(caretLayer);

    // The theme hides the native caret ONLY under this class, so theme.css
    // stays correct on its own — uninstall the plugin and the native caret
    // comes back rather than the editor losing its cursor entirely.
    document.body.classList.add(BODY_CLASS);
  }

  onunload() {
    document.body.classList.remove(BODY_CLASS);
  }
};
