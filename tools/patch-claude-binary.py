#!/usr/bin/env python3
"""Route Claude Code's inline-code and tip colours to the terminal's ANSI blue.

    usage: patch-claude-binary.py <claude binary> <output path>
    exit:  0  wrote a patched copy to <output path>
           3  already patched; nothing written
           2  not patchable: this build isn't laid out the way this file expects

Why a binary edit at all. Two render paths ignore ~/.claude/themes: inline code
(`codespan`, drawn with the `permission` token) and the `suggestion` token
(tips, ghost-text). Both go through one helper, in 2.1.272:

    function mt(e,r,o="foreground"){return(t)=>{ ...
      if(e.startsWith("rgb(")||e.startsWith("#")||e.startsWith("ansi256(")
         ||e.startsWith("ansi:"))return gX(t,e,o);
      let i=typeof r==="string"?_H(r):r;return gX(t,i[e],o)}}

The call sites pass the base-mode NAME as `r`, so `_H` hands back the stock
preset and a custom theme's value never applies: stock periwinkle
rgb(87,105,247) whatever the theme file says.

What this does (measured on Claude Code 2.1.272, Sept 2026):

  1. Rewrites every `<helper>("permission",` and `<helper>("suggestion",` call to
     `<helper>("ansi:blue" ,`: the same byte length, so no offset in the file
     moves. The helper passes `ansi:` values straight through, and ANSI blue is
     palette 4, which the Midori terminal themes set to exactly the colours
     these tokens were meant to have (#3a5572 paper, #6c87a4 night). The
     terminal does the light/dark switch; nothing here knows the mode.
     tests/test_patch_claude_binary.py fails if palette 4 and the watcher's
     token values drift apart.

  2. Zeroes the bytecode length of each module that holds a call site. Every
     module ships as source PLUS precompiled JavaScriptCore bytecode, and Bun
     runs the bytecode. Step 1 alone changed nothing on screen: a real reply
     drew `ls -la` in 38;2;87;105;247 from the stock binary and from the edited
     one alike. With the bytecode length zeroed, Bun compiles those modules from
     the edited source and the same reply drew SGR 34. Three modules on 2.1.272
     (25 call sites, ~1.96 MB of bytecode dropped); the banner came up in
     2.39 s against 2.47 s stock, so no measurable startup cost.
     Older builds shipped the app as ONE module: on 2.1.202 the same pass
     drops 151 MB of bytecode (all of src/entrypoints/cli.js), so every launch
     would compile the whole app from source. That cost is not measured; those
     builds predate the diff-token merge anyway and auto-update past it.
     Reading and rewriting the 210 MB 2.1.272 binary takes 1.1 s with the
     bytes.find scan below (8.6 s with the first, regex version; the output is
     byte-identical). A whole apply-claude-midori-patch.sh run takes 10.8 s
     (28 s before), most of it codesign, the re-signed copy's first launch,
     and the stock backup — once per Claude Code version.

The caller re-signs the output (codesign -f -s -): on arm64 macOS a binary whose
signature no longer matches its contents is killed at launch.

What this no longer does. This file replaces patch-claude-diffs.py, which
edited JS that tweakcc unpacked from the binary and then repacked. That had two
jobs this one drops:
  * Diff bands. Through Claude Code 2.1.243 they were hardcoded RGB triples and
    the old patch rewrote eight of them. From 2.1.247 the diff renderer lays the
    theme's diffAdded/diffRemoved/*Word tokens over its own palette, so the
    watcher's theme file colours them; an unpatched 2.1.272 /theme preview drew
    the exact Midori washes (48;2;201;206;187 and friends). Across the stock
    backups kept locally the merge is absent in 2.1.243 and present from 2.1.247
    (2.1.244-246 weren't kept).
  * tweakcc. It could not extract 2.1.229 or later, so no Midori patch landed
    from 2.1.229 through 2.1.272. Its tracker has the extraction break on
    2.1.231+ (tweakcc #945) and a 4.3.3 regression breaking ESM bundles (#981).

Bun's module table (StandaloneModuleGraph), read backwards from the end:

    ... module data ... | Offsets (32 B) | "\\n---- Bun! ----\\n"
    Offsets: byte_count u64, modules {offset u32, length u32}, ...
    module data starts at trailer - 32 - byte_count; `modules` is an array of
    52-byte records whose first eight u32s are {offset, length} pointers into
    the module data for name, contents, sourcemap and bytecode.

Every assumption is checked before a byte changes: each name must start with
/$bunfs/, every pointer must land inside the module data, and every call site
must sit inside exactly one module's contents. Anything else exits 2 and the
binary is left alone.
"""
import re
import struct
import sys

TRAILER = b"\n---- Bun! ----\n"
OFFSETS_SIZE = 32
RECORD_SIZE = 52
# Record layout: name, contents, sourcemap, bytecode, each {offset u32, length u32}.
BYTECODE_LENGTH_AT = 28
# The quoted token is 12 bytes ("permission", "suggestion"); "ansi:blue" is 11,
# so one trailing space keeps every offset in the file where it was.
ANSI_BLUE = b'"ansi:blue" '

CODESPAN = re.compile(rb'case"codespan":return ([A-Za-z_$][\w$]*)\((?:"permission"|"ansi:blue" ),')


class Unpatchable(Exception):
    """This build is not laid out the way the patcher expects; leave it alone."""


def module_table(data):
    """Parse Bun's module table; one dict per module, in record order."""
    trailer = data.rfind(TRAILER)
    if trailer < OFFSETS_SIZE:
        raise Unpatchable("no Bun module table (trailer not found)")
    byte_count = struct.unpack_from("<Q", data, trailer - OFFSETS_SIZE)[0]
    table_off, table_len = struct.unpack_from("<II", data, trailer - OFFSETS_SIZE + 8)
    base = trailer - OFFSETS_SIZE - byte_count
    if base < 0 or table_len == 0 or table_len % RECORD_SIZE or table_off + table_len > byte_count:
        raise Unpatchable(f"module table offsets don't fit {RECORD_SIZE}-byte records")
    modules = []
    for i in range(table_len // RECORD_SIZE):
        record = base + table_off + i * RECORD_SIZE
        f = struct.unpack_from("<8I", data, record)
        if any(off + length > byte_count for off, length in zip(f[0::2], f[1::2])):
            raise Unpatchable(f"module record {i} points outside the module data")
        name = bytes(data[base + f[0]:base + f[0] + f[1]])
        if not name.startswith(b"/$bunfs/"):
            raise Unpatchable(f"module record {i} is not a /$bunfs/ module ({name[:40]!r})")
        modules.append({
            "record": record,
            "name": name.decode("utf-8", "replace"),
            "start": base + f[2],
            "end": base + f[2] + f[3],
            "bytecode": f[7],
        })
    return modules


# Scanning is bytes.find plus an explicit identifier-boundary check, not regex:
# the first version ran re.finditer with a lookbehind over the whole 210 MB file
# (three passes) and a patch-and-verify run took 28 s, stalling the first `claude`
# launch after every update.
IDENT_CHAR = re.compile(rb"[\w$]")


def _find_codespan(data):
    i = data.find(b'case"codespan":return ')
    while i >= 0:
        anchor = CODESPAN.match(data, i)
        if anchor:
            return anchor
        i = data.find(b'case"codespan":return ', i + 1)
    return None


def _calls(data, helper, argument):
    """Offsets of `<helper>(<argument>` where <helper> is a whole identifier."""
    needle = helper + b"(" + argument
    hits = []
    i = data.find(needle)
    while i >= 0:
        if i == 0 or not IDENT_CHAR.match(data, i - 1):
            hits.append(i)
        i = data.find(needle, i + 1)
    return hits


def patch(data):
    """Return (patched bytearray, report), or None when already patched.

    Raises Unpatchable when any assumption fails; `data` is never modified."""
    anchor = _find_codespan(data)
    if not anchor:
        raise Unpatchable('inline-code render path not found (case"codespan")')
    helper = anchor.group(1)
    stock = sorted(_calls(data, helper, b'"permission",') + _calls(data, helper, b'"suggestion",'))
    done = _calls(data, helper, b'"ansi:blue" ,')
    # The codespan call is one site; tips must account for at least one more.
    if len(stock) + len(done) < 2:
        raise Unpatchable("no suggestion call sites through the inline-code helper")
    modules = module_table(data)
    owners = {}
    for site in stock + done:
        hits = [k for k, mod in enumerate(modules) if mod["start"] <= site < mod["end"]]
        if len(hits) != 1:
            raise Unpatchable(f"call site at byte {site} lies in {len(hits)} modules, not 1")
        owners[hits[0]] = owners.get(hits[0], 0) + 1
    # Source already rewritten is NOT done while any owner keeps its bytecode:
    # Bun would run the bytecode and the screen would stay stock (measured).
    if not stock and all(modules[k]["bytecode"] == 0 for k in owners):
        return None
    out = bytearray(data)
    token_at = len(helper) + 1
    for site in stock:
        out[site + token_at:site + token_at + len(ANSI_BLUE)] = ANSI_BLUE
    for k in owners:
        struct.pack_into("<I", out, modules[k]["record"] + BYTECODE_LENGTH_AT, 0)
    assert len(out) == len(data)
    report = {
        "helper": helper.decode(),
        "sites": len(stock) + len(done),
        "rewritten": len(stock),
        "modules": [(modules[k]["name"], owners[k], modules[k]["bytecode"]) for k in sorted(owners)],
    }
    return out, report


def main(argv):
    if len(argv) != 3:
        print("usage: patch-claude-binary.py <claude binary> <output path>", file=sys.stderr)
        return 64
    with open(argv[1], "rb") as f:
        data = f.read()
    try:
        result = patch(data)
    except Unpatchable as exc:
        print(f"not patchable: {exc}", file=sys.stderr)
        return 2
    if result is None:
        print("already patched")
        return 3
    out, report = result
    with open(argv[2], "wb") as f:
        f.write(out)
    print(f"{report['rewritten']} of {report['sites']} call sites -> ansi:blue (helper {report['helper']})")
    for name, sites, bytecode in report["modules"]:
        print(f"bytecode dropped: {name} ({sites} site(s), {bytecode} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
