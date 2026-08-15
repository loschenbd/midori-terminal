'use strict';

/* Does each plugin actually LOAD, and does it export a Plugin class?
 *
 * WHY THIS EXISTS. `node --check` only parses. A main.js that has been
 * truncated — say by an edit that replaced a range and swallowed everything
 * after it — is still perfectly valid JavaScript; it simply ends early. It
 * parses, it lints, and the only symptom is Obsidian saying "Failed to load
 * plugin" with no line number. That happened, and the browser harness did not
 * catch it either, because the harness lifts the modal out of the file and
 * never asks the file as a whole to be a plugin.
 *
 * So this requires each main.js the way Obsidian does, with `obsidian` stubbed,
 * and insists that what comes back is a class extending Plugin with an onload.
 * It is a load test, not a behaviour test: nothing is instantiated, because
 * instantiating would need the whole app object.
 */

const Module = require('module');
const path = require('path');
const fs = require('fs');

// The stub only has to be shaped enough to be extended and destructured from.
class Plugin { }
class PluginSettingTab { }
class Modal { }
class Component { }
const obsidianStub = {
  Plugin,
  PluginSettingTab,
  Modal,
  Component,
  Setting: class Setting { },
  Menu: class Menu { },
  Notice: class Notice { },
  MarkdownView: class MarkdownView { },
  ItemView: class ItemView { },
  setIcon: () => {},
  Platform: { isMobile: false, isDesktop: true },
  requestUrl: async () => ({}),
  normalizePath: (p) => p,
  debounce: (fn) => fn,
};

/* Obsidian also hands plugins CodeMirror at runtime — midori-caret builds a
 * ViewPlugin from it — and it is no more installed here than `obsidian` is. */
const cmViewStub = {
  ViewPlugin: { fromClass: () => ({}) },
  Decoration: { none: {}, set: () => ({}), widget: () => ({}) },
  WidgetType: class WidgetType { },
  EditorView: { updateListener: { of: () => ({}) }, decorations: { from: () => ({}) } },
};

const realLoad = Module._load;
Module._load = function load(request, parent, isMain) {
  if (request === 'obsidian') return obsidianStub;
  if (request.startsWith('@codemirror/')) return cmViewStub;
  return realLoad(request, parent, isMain);
};

const root = path.join(__dirname, '..', 'obsidian', 'plugins');
let fail = 0;

for (const name of fs.readdirSync(root).sort()) {
  const main = path.join(root, name, 'main.js');
  if (!fs.existsSync(main)) continue;
  let exported;
  try {
    delete require.cache[require.resolve(main)];
    exported = require(main);
  } catch (err) {
    console.log(`  FAIL ${name} threw on load: ${err.message}`);
    fail = 1;
    continue;
  }
  if (typeof exported !== 'function') {
    console.log(`  FAIL ${name} exports ${typeof exported}, not a class`
      + ' (a truncated main.js looks exactly like this)');
    fail = 1;
  } else if (!(exported.prototype instanceof Plugin)) {
    console.log(`  FAIL ${name} exports a class that does not extend Plugin`);
    fail = 1;
  } else if (typeof exported.prototype.onload !== 'function') {
    console.log(`  FAIL ${name} has no onload`);
    fail = 1;
  } else {
    console.log(`  ok   ${name} loads and exports a Plugin`);
  }

  // The manifest has to agree that this plugin exists, or Obsidian ignores it.
  const mf = path.join(root, name, 'manifest.json');
  try {
    const m = JSON.parse(fs.readFileSync(mf, 'utf8'));
    if (m.id !== name) {
      console.log(`  FAIL ${name} manifest id is "${m.id}"`);
      fail = 1;
    } else {
      console.log(`  ok   ${name} manifest v${m.version}`);
    }
  } catch (err) {
    console.log(`  FAIL ${name} manifest unreadable: ${err.message}`);
    fail = 1;
  }
}

Module._load = realLoad;
process.exit(fail);
