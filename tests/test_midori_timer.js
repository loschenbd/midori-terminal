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
  src += '\nmodule.exports={parseDuration,formatClock,formatHuman};';
  const mod = { exports: {} };
  const win = { AudioContext: null, setTimeout, setInterval, clearInterval };
  const doc = { head: { appendChild() {} }, createElement: () => ({ remove() {} }) };
  new Function('module', 'exports', 'window', 'document', 'require', src)(
    mod, mod.exports, win, doc, require,
  );
  return mod.exports;
}

const { parseDuration, formatClock, formatHuman } = load();

let fail = 0;
function eq(got, want, label) {
  if (got === want) {
    console.log(`  ok   ${label}`);
  } else {
    console.log(`  FAIL ${label}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
    fail = 1;
  }
}

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

console.log(`\nmidori-timer: ${fail ? 'failures above' : 'all green'}`);
process.exit(fail);
