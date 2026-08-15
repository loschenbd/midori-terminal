'use strict';

/* WHEN does midori-timer write the caret colour, and where?
 *
 * The drift is delivered by writing --midori-timer-caret to body. Where
 * midori-caret has drawn a caret, that is an element with a CSS-animated
 * blink, and repainting it costs nothing. Where it has not, the caret is the
 * browser's and so is its blink — and Chromium does not carry a blink through
 * a colour change underneath it. Three hundred writes a session, on a clock
 * unrelated to the blink's, is a caret that blinks wrong; that was reported
 * from use, not theorised.
 *
 * So the native branch defers its write to the next keystroke, when the caret
 * is being typed at and the blink is either suspended or resetting anyway.
 * This pins that down: which branch writes immediately, which defers, that a
 * deferred write is not lost, and that stopping drops a pending one on the
 * floor rather than painting a stale colour onto an idle caret.
 */

const Module = require('module');
const path = require('path');
const assert = require('assert');

class Plugin { }
const obsidianStub = {
  Plugin,
  PluginSettingTab: class PluginSettingTab { },
  Modal: class Modal { },
  Setting: class Setting { },
  Menu: class Menu { },
  Notice: class Notice { },
  setIcon: () => {},
  Platform: { isMobile: false, isDesktop: true },
  debounce: (fn) => fn,
};

const realLoad = Module._load;
Module._load = (request, parent, isMain) =>
  (request === 'obsidian' ? obsidianStub : realLoad(request, parent, isMain));

/* Only the parts of body that renderCaret touches. The class list is a plain
 * Set so a test can say "midori-caret is present" by adding one string. */
const classes = new Set();
const writes = [];
global.document = {
  body: {
    classList: {
      contains: (c) => classes.has(c),
      toggle: (c, on) => (on ? classes.add(c) : classes.delete(c)),
    },
    style: {
      setProperty: (k, v) => writes.push(['set', k, v]),
      removeProperty: (k) => writes.push(['remove', k]),
    },
  },
};

const MidoriTimer = require(path.join(__dirname, '..', 'obsidian', 'plugins',
                                      'midori-timer', 'main.js'));
Module._load = realLoad;

let fail = 0;
const ok = (name) => console.log(`  ok   ${name}`);
const check = (name, fn) => {
  try { fn(); ok(name); } catch (err) { console.log(`  FAIL ${name}: ${err.message}`); fail = 1; }
};

/* A plugin in the middle of a 1000s session, without going through onload —
 * which would want an app object. Elapsed is set by moving the deadline. */
function timerAt(elapsed) {
  const t = Object.create(MidoriTimer.prototype);
  t.settings = { display: 'caret' };
  t.session = { endsAt: Date.now() + (1000 - elapsed) * 1000, pausedAt: null, total: 1000 };
  t.caretKey = null;
  t.caretPending = null;
  writes.length = 0;
  return t;
}
const sets = () => writes.filter((w) => w[0] === 'set');

check('the drawn caret is painted on the tick, as it always was', () => {
  classes.add('midori-drawn');
  const t = timerAt(100);
  t.renderCaret();
  assert.strictEqual(sets().length, 1, 'expected one write');
  assert.strictEqual(sets()[0][1], '--midori-timer-caret');
  assert.strictEqual(t.caretPending, null, 'nothing should be left pending');
  classes.delete('midori-drawn');
});

check('the native caret is not painted on the tick', () => {
  const t = timerAt(100);
  t.renderCaret();
  assert.strictEqual(sets().length, 0, 'the tick must not touch a blinking caret');
  assert.ok(t.caretPending, 'the colour should be waiting');
});

check('the next keystroke lands it', () => {
  const t = timerAt(100);
  t.renderCaret();
  const wanted = t.caretPending;
  t.flushCaret();
  assert.deepStrictEqual(sets(), [['set', '--midori-timer-caret', wanted]]);
  assert.strictEqual(t.caretPending, null);
});

check('a keystroke with nothing pending writes nothing', () => {
  const t = timerAt(100);
  t.flushCaret();
  t.flushCaret();
  assert.strictEqual(sets().length, 0);
});

check('ticks in between coalesce: one keystroke, one write, latest colour', () => {
  const t = timerAt(100);
  t.renderCaret();
  t.session.endsAt = Date.now() + 100 * 1000;   // much later in the session
  t.renderCaret();
  const wanted = t.caretPending;
  t.flushCaret();
  assert.strictEqual(sets().length, 1, 'a keystroke is one write however many ticks passed');
  assert.strictEqual(sets()[0][2], wanted);
});

check('stopping drops a pending colour rather than landing it later', () => {
  const t = timerAt(100);
  t.renderCaret();
  assert.ok(t.caretPending);
  t.session = { endsAt: null, pausedAt: null, total: null };
  t.renderCaret();
  assert.strictEqual(t.caretPending, null, 'a stale colour must not survive the session');
  t.flushCaret();
  assert.strictEqual(sets().length, 0);
  assert.ok(writes.some((w) => w[0] === 'remove'), 'the property should be removed');
  assert.ok(!classes.has('midori-timer-running'), 'and the gate class with it');
});

console.log(fail ? 'caret writes: failures above' : 'caret writes: all green');
process.exit(fail);
