/* Unit tests for Midori Timer's pure functions — duration parsing and the two
 * formatters. Run:  node tests/test_midori_timer.js
 *
 * The plugin is a single CommonJS file that `require('obsidian')` at the top,
 * a module that only exists inside Obsidian. Rather than mock the whole API,
 * the source is read, the import line is rewritten to local stubs, and an
 * export appendix is appended — so the functions under test are the ones that
 * actually ship, not a copy that can drift from them.
 *
 * THE TEST THAT EARNS ITS KEEP is the round trip. The settings tab stores
 * seconds but displays `formatHuman`, and re-parses that text on every
 * keystroke. If `parseDuration(formatHuman(x)) !== x` for any x, opening the
 * settings tab and touching the field silently rewrites the saved default —
 * a corruption with no error and no visible cause. 7265s (2h 1m 5s) is in the
 * table because it is the case where all three units are present at once.
 */

const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, '..', 'obsidian', 'plugins', 'midori-timer', 'main.js');

function load() {
  let src = fs.readFileSync(SRC, 'utf8');
  const importLine = /const \{[^}]*\} = require\('obsidian'\);/;
  if (!importLine.test(src)) {
    throw new Error('obsidian import not found — did the plugin header change?');
  }
  src = src.replace(
    importLine,
    'const Plugin=class{},PluginSettingTab=class{},Setting=class{},Modal=class{},'
    + 'Menu=class{},Notice=class{},setIcon=()=>{},Platform={isMobile:false};',
  );
  src += '\nmodule.exports={parseDuration,formatClock,formatHuman,caretColor,CARET_STOPS};';
  const mod = { exports: {} };
  const win = { AudioContext: null, setTimeout, setInterval, clearInterval };
  const doc = { head: { appendChild() {} }, createElement: () => ({ remove() {} }) };
  new Function('module', 'exports', 'window', 'document', 'require', src)(
    mod, mod.exports, win, doc, require,
  );
  return mod.exports;
}

const { parseDuration, formatClock, formatHuman, caretColor, CARET_STOPS } = load();

let fail = 0;
function eq(got, want, label) {
  if (got === want) {
    console.log(`  ok   ${label}`);
  } else {
    console.log(`  FAIL ${label}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
    fail = 1;
  }
}

function ok(cond, label) { eq(Boolean(cond), true, label); }

console.log('== parseDuration: accepted forms ==');
eq(parseDuration('25'), 1500, 'a bare number is minutes');
eq(parseDuration('25m'), 1500, '25m');
eq(parseDuration('90s'), 90, '90s');
eq(parseDuration('2h'), 7200, '2h');
eq(parseDuration('1h30'), 5400, '1h30 — a trailing bare number is minutes');
eq(parseDuration('1h30m'), 5400, '1h30m');
eq(parseDuration('1h 30m'), 5400, '1h 30m');
eq(parseDuration('1.5h'), 5400, '1.5h');
eq(parseDuration('45 minutes'), 2700, 'units spelled out');
eq(parseDuration('1 hour 30 minutes'), 5400, 'fully spelled out');
eq(parseDuration('  25M  '), 1500, 'case and surrounding whitespace');

console.log('== parseDuration: clock forms (stopwatch convention) ==');
eq(parseDuration('1:30'), 90, 'one colon is mm:ss');
eq(parseDuration('1:30:00'), 5400, 'two colons is hh:mm:ss');
eq(parseDuration('0:45'), 45, '0:45');

console.log('== parseDuration: rejections ==');
eq(parseDuration(''), null, 'empty string');
eq(parseDuration('   '), null, 'whitespace only');
eq(parseDuration('abc'), null, 'letters');
eq(parseDuration('25 apples'), null, 'trailing garbage is rejected, not ignored');
eq(parseDuration('0'), null, 'zero');
eq(parseDuration('0m'), null, '0m');
eq(parseDuration('-5'), null, 'negative');
eq(parseDuration(null), null, 'null');
eq(parseDuration(undefined), null, 'undefined');

console.log('== formatClock ==');
eq(formatClock(1500), '25:00', '1500 -> 25:00');
eq(formatClock(90), '1:30', '90 -> 1:30');
eq(formatClock(3599), '59:59', 'under an hour carries no hour field');
eq(formatClock(3600), '1:00:00', '3600 -> 1:00:00');
eq(formatClock(5400), '1:30:00', '5400 -> 1:30:00');
eq(formatClock(0), '0:00', 'zero');
eq(formatClock(-5), '0:00', 'negative clamps to zero');
eq(formatClock(1499.6), '25:00', 'ceils, so a fresh 25m reads 25:00 not 24:59');
eq(formatClock(59.2), '1:00', 'ceils across the minute boundary');

console.log('== formatHuman ==');
eq(formatHuman(1500), '25m', '1500');
eq(formatHuman(5400), '1h 30m', '5400');
eq(formatHuman(90), '1m 30s', '90');
eq(formatHuman(45), '45s', '45');
eq(formatHuman(3600), '1h', 'an exact hour drops the empty minutes');
eq(formatHuman(0), '0s', 'zero still renders a unit');

console.log('== round trip: the settings field must not corrupt its own value ==');
for (const secs of [45, 90, 300, 1500, 2700, 3600, 5400, 7265]) {
  eq(parseDuration(formatHuman(secs)), secs, `parse(formatHuman(${secs})) === ${secs}`);
}

console.log('== caretColor: the stop table and the drift between stops ==');

// The drift is the whole design, so the table itself is worth asserting: a
// reordered or duplicated stop would still interpolate, just wrongly.
eq(CARET_STOPS.length, 4, 'four stops: indigo, sage, ochre, wine');
eq(CARET_STOPS.map((s) => s.at).join(','), '0,0.4,0.8,1', 'stops are ordered and span [0,1]');
eq(CARET_STOPS[0].varName, '--color-blue', 'rests at the caret\'s own indigo');
eq(CARET_STOPS[3].varName, '--color-red', 'ends at wine');

// Segment selection. The boundary cases are the ones that break: at exactly
// 0.40 the mix must be 0% of the NEXT segment, not 100% of the previous one,
// or the colour jumps a whole segment for one tick.
eq(caretColor(0).key, '0:0', 't=0 is the first stop exactly');
eq(caretColor(0.2).key, '0:50', 'halfway through the first segment');
eq(caretColor(0.4).key, '1:0', 'a boundary starts the next segment at 0%');
eq(caretColor(0.6).key, '1:50', 'halfway through the second');
eq(caretColor(0.8).key, '2:0', 'the second boundary, same rule');
eq(caretColor(0.9).key, '2:50', 'halfway through the last, shorter segment');
eq(caretColor(1).key, '2:100', 't=1 is the last stop exactly');

// Clamped, not extrapolated: a session restored past its deadline is wine.
eq(caretColor(1.7).key, '2:100', 'past the end clamps to wine');
eq(caretColor(-3).key, '0:0', 'before the start clamps to indigo');
eq(caretColor(NaN).key, '0:0', 'a NaN fraction cannot poison the style');
eq(caretColor(undefined).key, '0:0', 'nor can a missing one');

// The space is the one thing about the colour a unit test CAN assert. It
// cannot see the defect that chose it — a rectangular space cuts the corner
// between indigo and sage and dips below both endpoints' chroma, measured at
// t=0.30 — only that the code asked for a polar one. See the note in main.js.
ok(/color-mix\(in oklch,/.test(caretColor(0.5).color), 'interpolates hue in oklch, not a rectangular space');
ok(/var\(--interactive-accent,/.test(caretColor(0.5).color), 'mixes theme variables, not hex');
ok(!/#[0-9a-f]{6}\s+\d+%/i.test(caretColor(0.5).color), 'no hardcoded colour is mixed directly');

// The write suppressor: equal keys mean renderCaret skips the style write.
// 100 steps a segment, not one per tick.
const keys = new Set();
for (let i = 0; i <= 6000; i += 1) keys.add(caretColor(i / 6000).key);
ok(keys.size <= 303, `6000 ticks collapse to ${keys.size} distinct writes`);
ok(keys.size >= 300, 'but not so few that the drift becomes visible steps');

console.log(`\nmidori-timer: ${fail ? 'failures above' : 'all green'}`);
process.exit(fail);
