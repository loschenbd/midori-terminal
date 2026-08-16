const { Plugin } = require("obsidian");

/* The dot is this plugin's own element, so this plugin styles it — and via a
 * stylesheet rather than inline styles, which is not a nicety: an inline style
 * can only be overridden with !important, and the theme should be able to
 * restyle a dot sitting in its own status bar without that. */
const STYLE = `
.zen-toggle-btn {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 1.5px solid var(--text-faint);
  background: transparent;
  vertical-align: middle;
  transition: background 120ms ease, border-color 120ms ease;
}
.zen-toggle-btn.is-on {
  background: var(--interactive-accent);
  border-color: var(--interactive-accent);
}
.status-bar-item:hover .zen-toggle-btn {
  border-color: var(--interactive-accent);
}
`;

module.exports = class ZenToggle extends Plugin {
  async onload() {
    const saved = await this.loadData();
    this.zen = saved?.zen ?? false;
    document.body.classList.toggle("zen-mode", this.zen);

    this.addCommand({
      id: "toggle-zen",
      name: "Toggle zen mode",
      callback: () => this.toggle(),
    });

    // Official status-bar API: never participates in workspace layout,
    // and zen mode keeps the status bar, so the toggle is always reachable.
    this.item = this.addStatusBarItem();
    this.item.addClass("mod-clickable");
    this.item.setAttribute("aria-label", "Toggle zen mode");
    this.dot = this.item.createEl("span", { cls: "zen-toggle-btn" });

    const style = document.createElement('style');
    style.id = 'zen-toggle-style';
    style.textContent = STYLE;
    document.head.appendChild(style);
    this.register(() => style.remove());

    this.registerDomEvent(this.item, "click", () => this.toggle());
    this.render();
  }

  render() {
    if (!this.dot) return;
    this.dot.toggleClass('is-on', this.zen);
  }

  async toggle() {
    this.zen = !this.zen;
    document.body.classList.toggle("zen-mode", this.zen);
    await this.saveData({ zen: this.zen });
    this.render();
  }

  onunload() {
    document.body.classList.remove("zen-mode");
  }
};
