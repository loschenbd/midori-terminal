'use strict';

/* Midori Confetti — throw confetti when a note crosses a word-count target.
 *
 * WHY THIS EXISTS. Nothing in the community registry does this. Of 6,478
 * plugins, none pairs a settable word goal with a celebration: Writing Goals
 * draws a progress bar and stops there, Target Word Count *blocks editing*
 * until you hit your number, and the one confetti plugin fires on every
 * keystroke. The nearest match is a 2021 forum request for exactly this,
 * filed under "Plugins ideas" and never built.
 *
 * THREE DECISIONS THAT SHAPE THE CODE.
 *
 * 1. Fire on the CROSSING, not on the value. The obvious implementation —
 *    "if words >= target, celebrate" — is wrong in a way that only shows up
 *    in use: every finished note is above its target forever, so opening one
 *    and typing a single character would set it off. Instead the previous
 *    count is remembered per note and the burst fires only on the transition
 *    prev < target <= now. A note opened above target seeds `prev` at load
 *    (see onFileOpen) and therefore stays quiet.
 *
 * 2. Debounce the count, not the celebration. Counting words means scanning
 *    the whole document; doing that per keystroke is wasteful in a long note
 *    and pointless besides, since a target can only be crossed once. The
 *    editor-change handler is debounced, which also means the burst lands a
 *    beat after you finish the word rather than mid-keystroke.
 *
 * 3. Read colours from the theme, don't hardcode them. Particle colours come
 *    from CSS custom properties the theme already defines (--checkbox-color,
 *    --code-function and friends). That makes the burst track Midori Paper
 *    and Midori Night automatically — and degrade sensibly under any other
 *    theme — with the Midori accents kept only as fallbacks for a theme that
 *    defines none of them.
 *
 * WORD COUNTING. Obsidian exposes no public word-count API, so this counts
 * its own: YAML frontmatter is stripped (it is metadata, not prose), CJK
 * ideographs and kana count one word each as is conventional, and everything
 * else is counted as runs of letters, digits, apostrophes and hyphens. The
 * number will therefore track, but not always exactly equal, the status-bar
 * count — that one includes frontmatter.
 */

const { Plugin, PluginSettingTab, Setting, Notice, debounce } = require('obsidian');

const DEFAULTS = {
  enabled: true,
  target: 500,
  mode: 'session',     // 'session' = words added since you opened the note; 'total' = words in the note
  oncePerDay: true,
  particles: 140,
  message: '',         // optional notice alongside the burst; empty = no notice
};

/* Theme variables sampled for particle colour, most characteristic first.
 * Fallbacks are the Midori Paper accents, used only if a theme defines none. */
const COLOR_VARS = [
  ['--checkbox-color', '#5f6f5e'],            // sage
  ['--code-important', '#b06d4a'],            // terracotta
  ['--code-function', '#3a5572'],             // slate
  ['--code-string', '#6c7d52'],               // moss
  ['--code-operator', '#7a4a4a'],             // brick
  ['--blockquote-border-color', '#c9916b'],   // clay
];

const CJK = /[぀-ヿ㐀-䶿一-鿿豈-﫿ｦ-ﾟ]/g;
const WORD = /[A-Za-z0-9À-ɏ'’-]+/g;
const FRONTMATTER = /^---\r?\n[\s\S]*?\r?\n---\r?\n?/;

function countWords(text) {
  if (!text) return 0;
  const body = text.replace(FRONTMATTER, '');
  const cjk = (body.match(CJK) || []).length;
  // Replace rather than ignore, so a CJK run cannot glue two Latin words together.
  const latin = (body.replace(CJK, ' ').match(WORD) || []).length;
  return cjk + latin;
}

function today() {
  // Local date, not UTC: "once per day" should mean the user's day.
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/* ------------------------------------------------------------------ burst */

class Burst {
  constructor(count) {
    this.canvas = document.createElement('canvas');
    // Fixed, inert and above the workspace. pointer-events:none matters —
    // without it the canvas would swallow clicks for its whole lifetime.
    Object.assign(this.canvas.style, {
      position: 'fixed', inset: '0', width: '100%', height: '100%',
      pointerEvents: 'none', zIndex: 'var(--layer-notice, 100)',
    });
    document.body.appendChild(this.canvas);

    this.ctx = this.canvas.getContext('2d');
    this.dpr = window.devicePixelRatio || 1;
    this.resize();
    this.onResize = () => this.resize();
    window.addEventListener('resize', this.onResize);

    const cs = getComputedStyle(document.body);
    const colors = COLOR_VARS.map(([v, fb]) => cs.getPropertyValue(v).trim() || fb);

    const W = window.innerWidth, H = window.innerHeight;
    this.parts = [];
    // Two cannons angled inward from the lower corners. A single centre burst
    // reads as an explosion; two crossing arcs read as a celebration and, more
    // practically, keep the middle of the screen — where the text is — clearer.
    for (let i = 0; i < count; i++) {
      const left = i % 2 === 0;
      // Elevation measured from horizontal, so the two cannons differ only in
      // the sign of vx. Deriving both components from one angle and then
      // trying to correct the sign afterwards is how this got written wrong
      // the first time: every particle launched leftward and the right-hand
      // arc flew straight off screen, unseen.
      const elev = (38 + Math.random() * 34) * Math.PI / 180;
      const speed = 13 + Math.random() * 14;
      this.parts.push({
        x: left ? -12 : W + 12,
        y: H * (0.74 + Math.random() * 0.18),
        vx: Math.cos(elev) * speed * (left ? 1 : -1),
        vy: -Math.sin(elev) * speed,
        w: 6 + Math.random() * 7,
        h: 4 + Math.random() * 4,
        rot: Math.random() * Math.PI,
        vr: (Math.random() - 0.5) * 0.32,
        color: colors[i % colors.length],
        life: 0,
        ttl: 105 + Math.random() * 55,
      });
    }

    this.frame = 0;
    this.raf = requestAnimationFrame(() => this.tick());
  }

  resize() {
    const w = window.innerWidth, h = window.innerHeight;
    this.canvas.width = Math.floor(w * this.dpr);
    this.canvas.height = Math.floor(h * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
  }

  tick() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    let alive = 0;

    for (const p of this.parts) {
      if (p.life > p.ttl) continue;
      alive++;
      p.life++;
      p.vy += 0.34;          // gravity
      p.vx *= 0.986;         // drag, so the arcs settle instead of shooting off
      p.vy *= 0.994;
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.vr;

      // Fade only over the last third, so the burst reads as solid before it goes.
      const t = p.life / p.ttl;
      ctx.globalAlpha = t > 0.66 ? Math.max(0, 1 - (t - 0.66) / 0.34) : 1;
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      // Squashing the height by |cos(rot)| fakes a flat rectangle tumbling in
      // 3D — cheaper and steadier than rotating a real quad, and the flicker as
      // it passes edge-on is what makes paper read as paper. The offset has to
      // be half the *squashed* height, or the fleck drifts up and down as it
      // spins instead of tumbling in place.
      const fh = p.h * Math.abs(Math.cos(p.rot * 2)) + 1;
      ctx.fillRect(-p.w / 2, -fh / 2, p.w, fh);
      ctx.restore();
    }

    if (alive === 0 || this.frame++ > 400) return this.destroy();
    this.raf = requestAnimationFrame(() => this.tick());
  }

  destroy() {
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = null;
    window.removeEventListener('resize', this.onResize);
    this.canvas.remove();
  }
}

/* ----------------------------------------------------------------- plugin */

module.exports = class MidoriConfetti extends Plugin {
  async onload() {
    this.settings = Object.assign({}, DEFAULTS, await this.loadData());
    this.bursts = new Set();
    this.prev = new Map();       // path -> word count at last check
    this.baseline = new Map();   // path -> word count when the note was opened

    this.addSettingTab(new MidoriConfettiSettings(this.app, this));

    this.addCommand({
      id: 'test-burst',
      name: 'Throw confetti now',
      callback: () => this.celebrate(null),
    });

    this.addCommand({
      id: 'reset-today',
      name: "Reset today's celebrations",
      callback: async () => {
        this.settings.celebrated = {};
        await this.saveSettings();
        new Notice('Midori Confetti: today reset.');
      },
    });

    // 400ms is long enough that a fast typist scans the document once per
    // burst of typing rather than once per key, and short enough that the
    // confetti still feels like a response to the word you just finished.
    const check = debounce((editor, info) => this.check(editor, info), 400, false);
    this.registerEvent(this.app.workspace.on('editor-change', check));
    this.registerEvent(this.app.workspace.on('file-open', (file) => this.onFileOpen(file)));

    // Seed for whatever is already open, so the first keystroke after enabling
    // the plugin compares against a real number rather than against zero.
    this.app.workspace.onLayoutReady(() => this.onFileOpen(this.app.workspace.getActiveFile()));
  }

  onunload() {
    for (const b of this.bursts) b.destroy();
    this.bursts.clear();
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  async onFileOpen(file) {
    if (!file || file.extension !== 'md') return;
    let text = '';
    try {
      text = await this.app.vault.cachedRead(file);
    } catch (e) {
      return;
    }
    const n = countWords(text);
    // Seeding BOTH is what keeps a finished note quiet: `prev` at the current
    // value means there is no upward crossing to detect on the next keystroke.
    this.baseline.set(file.path, n);
    this.prev.set(file.path, n);
  }

  metric(path, words) {
    if (this.settings.mode === 'total') return words;
    const base = this.baseline.get(path);
    return Math.max(0, words - (base == null ? words : base));
  }

  check(editor, info) {
    if (!this.settings.enabled) return;
    const file = info && info.file;
    if (!file || file.extension !== 'md') return;

    const words = countWords(editor.getValue());
    // A note can be edited without this plugin ever having seen a file-open for
    // it — a second pane, a note restored with the workspace, an edit made in
    // the same tick the plugin loaded. Without a baseline, session mode would
    // measure every note against itself and return 0 forever, so seed it here.
    if (!this.baseline.has(file.path)) this.baseline.set(file.path, words);
    const now = this.metric(file.path, words);
    const before = this.metric(file.path, this.prev.get(file.path) ?? words);
    this.prev.set(file.path, words);

    const target = Number(this.settings.target) || 0;
    if (target <= 0) return;
    if (!(before < target && now >= target)) return;

    if (this.settings.oncePerDay) {
      const seen = (this.settings.celebrated || {})[file.path];
      if (seen === today()) return;
      this.settings.celebrated = Object.assign({}, this.settings.celebrated, { [file.path]: today() });
      this.pruneCelebrated();
      this.saveSettings();
    }

    this.celebrate(now);
  }

  /* Keep the persisted record from growing without bound in a large vault:
   * anything not from today is no longer consulted by the oncePerDay check. */
  pruneCelebrated() {
    const t = today();
    const kept = {};
    for (const [k, v] of Object.entries(this.settings.celebrated || {})) if (v === t) kept[k] = v;
    this.settings.celebrated = kept;
  }

  celebrate(count) {
    const msg = this.settings.message
      || (count == null ? '' : `${count.toLocaleString()} words.`);

    // Motion is the whole feature, so when it is unwelcome the plugin still
    // reports the achievement rather than silently doing nothing.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      new Notice(msg || 'Word target reached.');
      return;
    }

    if (msg) new Notice(msg);
    const b = new Burst(Math.max(20, Math.min(400, Number(this.settings.particles) || 140)));
    this.bursts.add(b);
    const done = b.destroy.bind(b);
    b.destroy = () => { done(); this.bursts.delete(b); };
  }
};

class MidoriConfettiSettings extends PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName('Enabled')
      .setDesc('Turn the celebration off without disabling the plugin.')
      .addToggle((t) => t
        .setValue(this.plugin.settings.enabled)
        .onChange(async (v) => { this.plugin.settings.enabled = v; await this.plugin.saveSettings(); }));

    new Setting(containerEl)
      .setName('Word target')
      .setDesc('Confetti fires the moment a note crosses this number.')
      .addText((t) => t
        .setPlaceholder('500')
        .setValue(String(this.plugin.settings.target))
        .onChange(async (v) => {
          const n = parseInt(v, 10);
          if (Number.isFinite(n) && n > 0) { this.plugin.settings.target = n; await this.plugin.saveSettings(); }
        }));

    new Setting(containerEl)
      .setName('Count')
      .setDesc('Words written since you opened the note, or the note\'s total.')
      .addDropdown((d) => d
        .addOption('session', 'Words written this session')
        .addOption('total', 'Total words in the note')
        .setValue(this.plugin.settings.mode)
        .onChange(async (v) => {
          this.plugin.settings.mode = v;
          // The baselines describe the old mode; drop them so the next check
          // measures against the new one rather than a stale reference point.
          this.plugin.baseline.clear();
          this.plugin.prev.clear();
          this.plugin.onFileOpen(this.app.workspace.getActiveFile());
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Once per note per day')
      .setDesc('Off means every upward crossing celebrates — useful if you delete and rewrite past the target.')
      .addToggle((t) => t
        .setValue(this.plugin.settings.oncePerDay)
        .onChange(async (v) => { this.plugin.settings.oncePerDay = v; await this.plugin.saveSettings(); }));

    new Setting(containerEl)
      .setName('Particles')
      .setDesc('20 to 400.')
      .addSlider((s) => s
        .setLimits(20, 400, 10)
        .setValue(this.plugin.settings.particles)
        .setDynamicTooltip()
        .onChange(async (v) => { this.plugin.settings.particles = v; await this.plugin.saveSettings(); }));

    new Setting(containerEl)
      .setName('Notice')
      .setDesc('Shown alongside the confetti. Leave empty to show the word count instead.')
      .addText((t) => t
        .setPlaceholder('(word count)')
        .setValue(this.plugin.settings.message)
        .onChange(async (v) => { this.plugin.settings.message = v; await this.plugin.saveSettings(); }));

    new Setting(containerEl)
      .setName('Try it')
      .setDesc('Throw a burst now, using the current settings.')
      .addButton((b) => b.setButtonText('Throw confetti').onClick(() => this.plugin.celebrate(null)));
  }
}
