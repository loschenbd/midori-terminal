// Midori — a small shell lexer for markdown-preview code blocks.
//
// Why this exists. The preview's fenced code is tokenised by highlight.js in
// the extension host, long before our CSS sees the HTML, and its Bash grammar
// only emits classes for shell builtins (a fixed coreutils list — `cd`, `echo`,
// `whoami`, …), quotes, comments and `$vars`. A command name in command
// position is not a token in that model, so `git`, `npm`, `node`, `brew` and
// every argument they take come out as plain text. No stylesheet can colour a
// span that was never created, which is why this is JavaScript and not more CSS.
//
// So for shell fences only, we tokenise the block ourselves and emit the same
// `hljs-*` class names the stylesheet already maps. Every other language falls
// through to highlight.js untouched — it handles JSON, TS and the rest well.
//
// Ordering note: MarkdownItEngine builds the instance with its own `highlight`
// option and *then* applies contributed plugins, so re-setting `highlight` here
// wins. It also normalises some aliases before we see them ("shell" arrives as
// "sh"), hence the alias set below covers both spellings.

const SHELL = new Set([
  'bash', 'sh', 'shell', 'zsh', 'ksh',
  'console', 'shell-session', 'shellsession', 'terminal',
]);

// Characters that end a bare word. `#` is deliberately absent: it only opens a
// comment at the start of a word, so `sha#1` stays one token.
const WORD_END = /[\s'"|&;()<>$]/;

// Operators that put us back into command position — the next word is a command
// name again, not an argument.
const CMD_RESET = ['&&', '||', '|', ';;', ';', '(', ')', '&'];

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function span(cls, text) {
  return `<span class="hljs-${cls}">${esc(text)}</span>`;
}

// Bare words get the "subcommand" treatment; anything carrying a path, an
// extension or an `=` is data, not a verb, and stays plain.
const BARE_WORD = /^[A-Za-z][A-Za-z0-9_-]*$/;
const ASSIGNMENT = /^[A-Za-z_][A-Za-z0-9_]*=/;

function lexLine(line) {
  let out = '';
  let i = 0;
  let cmdPos = true; // the next word is a command name

  // A leading `$ ` or `% ` is a session prompt, not part of the command.
  const prompt = /^(\s*)([$%])(\s+)/.exec(line);
  if (prompt) {
    out += esc(prompt[1]) + span('meta', prompt[2]) + esc(prompt[3]);
    i = prompt[0].length;
  }

  while (i < line.length) {
    const ch = line[i];

    if (/\s/.test(ch)) {
      let j = i;
      while (j < line.length && /\s/.test(line[j])) j++;
      out += esc(line.slice(i, j));
      i = j;
      continue;
    }

    // `#` at a word boundary opens a comment that runs to end of line.
    if (ch === '#') {
      out += span('comment', line.slice(i));
      return out;
    }

    if (ch === "'" || ch === '"') {
      let j = i + 1;
      while (j < line.length) {
        if (ch === '"' && line[j] === '\\') { j += 2; continue; }
        if (line[j] === ch) { j++; break; }
        j++;
      }
      out += span('string', line.slice(i, j));
      i = j;
      cmdPos = false;
      continue;
    }

    if (ch === '$') {
      // `${NAME}`, `$(cmd)` and `$NAME` are all substitutions.
      let j = i + 1;
      if (line[j] === '{') { while (j < line.length && line[j] !== '}') j++; j++; }
      else if (line[j] === '(') { let d = 0; while (j < line.length) { if (line[j] === '(') d++; if (line[j] === ')' && --d === 0) { j++; break; } j++; } }
      else { while (j < line.length && /[A-Za-z0-9_]/.test(line[j])) j++; }
      out += span('subst', line.slice(i, j));
      i = j;
      cmdPos = false;
      continue;
    }

    const op = CMD_RESET.find((o) => line.startsWith(o, i));
    if (op) {
      out += esc(op);
      i += op.length;
      cmdPos = true;
      continue;
    }

    // Redirections separate tokens but do not restart the command.
    if (ch === '<' || ch === '>') {
      let j = i;
      while (j < line.length && (line[j] === '<' || line[j] === '>')) j++;
      out += esc(line.slice(i, j));
      i = j;
      continue;
    }

    let j = i;
    while (j < line.length && !WORD_END.test(line[j])) j++;
    const word = line.slice(i, j);
    i = j;

    if (ASSIGNMENT.test(word)) {
      // `FOO=bar cmd` — an env prefix, so the command is still ahead.
      const eq = word.indexOf('=');
      out += span('subst', word.slice(0, eq)) + esc(word.slice(eq));
    } else if (word.startsWith('-')) {
      out += span('meta', word);
      cmdPos = false;
    } else if (cmdPos) {
      out += span('built_in', word);
      cmdPos = false;
    } else if (BARE_WORD.test(word)) {
      out += span('title', word);
    } else {
      out += esc(word);
    }
  }

  return out;
}

function lexShell(code) {
  return code.split('\n').map(lexLine).join('\n');
}

function activate() {
  return {
    extendMarkdownIt(md) {
      const previous = md.options.highlight;
      md.set({
        highlight: (code, lang, attrs) => {
          if (SHELL.has(String(lang || '').toLowerCase())) {
            try {
              return lexShell(code);
            } catch (e) {
              // Never let a lexer bug blank out a code block.
              console.error('midori: shell lexer failed', e);
            }
          }
          return previous ? previous(code, lang, attrs) : esc(code);
        },
      });
      return md;
    },
  };
}

module.exports = { activate, lexShell };
