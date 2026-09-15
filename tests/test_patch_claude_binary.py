#!/usr/bin/env python3
"""Unit tests for tools/patch-claude-binary.py — the one component with real,
fragile logic: a same-length rewrite inside a 200 MB binary, a hand-parsed Bun
module table, idempotency, and refusing anything it doesn't recognise.

No pytest / no network / no binary needed: fixtures are synthetic Bun module
tables built here from the patcher's own layout constants. What they cannot
prove is that the layout matches a real Claude Code binary; that was checked by
rendering, recorded in the patcher's docstring.
Run:  python3 tests/test_patch_claude_binary.py
"""
import importlib.util
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..")
MOD_PATH = os.path.join(REPO, "tools", "patch-claude-binary.py")


def _load():
    # Module filename has hyphens (not import-safe); load by path.
    spec = importlib.util.spec_from_file_location("patch_claude_binary", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load()

CODESPAN_SRC = b'case"codespan":return mt("permission",t)(e.text);'
SUGGESTION_SRC = b'a=mt("suggestion",w.theme)(s);b=mt("suggestion",gt)(q);'
# `xmt(` is a different function whose name merely ends in the helper's.
UNRELATED_SRC = b'c=xmt("suggestion",k);function f(){return 1}'


def build(modules, prefix=b"\xcf\xfa\xed\xfe fake Mach-O header\x00" * 2):
    """A file laid out like a Bun-compiled binary: module data, 52-byte records,
    32-byte offsets, trailer. modules = [(name, contents, bytecode_len), ...]."""
    data = bytearray()
    pointers = []
    for name, contents, bytecode in modules:
        n = len(data); data += name
        c = len(data); data += contents
        b = len(data); data += b"\xbc" * bytecode
        pointers.append((n, len(name), c, len(contents), 0, 0, b, bytecode))
    table = len(data)
    for p in pointers:
        data += struct.pack("<8I", *p).ljust(m.RECORD_SIZE, b"\x00")
    offsets = struct.pack("<QII", len(data), table, len(pointers) * m.RECORD_SIZE)
    return bytes(prefix) + bytes(data) + offsets.ljust(m.OFFSETS_SIZE, b"\x00") + m.TRAILER + b"code signature"


def stock(helper=b"mt"):
    swap = lambda src: src.replace(b"mt(", helper + b"(")
    return build([
        (b"/$bunfs/root/chunk-render.js", swap(CODESPAN_SRC), 400),
        (b"/$bunfs/root/chunk-tips.js", swap(SUGGESTION_SRC), 300),
        (b"/$bunfs/root/chunk-other.js", swap(UNRELATED_SRC), 200),
        (b"/$bunfs/root/cli", b"import './chunk-render.js';", 100),
    ])


def bytecode_by_name(data):
    return {mod["name"]: mod["bytecode"] for mod in m.module_table(data)}


def refuses(data, why):
    try:
        m.patch(data)
    except m.Unpatchable:
        return
    raise AssertionError(f"expected Unpatchable: {why}")


# ── tests ────────────────────────────────────────────────────────────────────

def test_rewrites_every_call_site_at_the_same_length():
    src = stock()
    out, report = m.patch(src)
    assert len(out) == len(src), "file length changed: every later offset would move"
    assert not re.search(rb'(?<![\w$])mt\("(?:permission|suggestion)",', out), "a stock call site survived"
    assert out.count(b'mt("ansi:blue" ,') == 3, "expected the codespan call and both tip calls rewritten"
    assert report["rewritten"] == 3


def test_drops_bytecode_only_where_a_call_site_lives():
    bytecode = bytecode_by_name(m.patch(stock())[0])
    assert bytecode["/$bunfs/root/chunk-render.js"] == 0, "codespan module kept its bytecode"
    assert bytecode["/$bunfs/root/chunk-tips.js"] == 0, "tips module kept its bytecode"
    assert bytecode["/$bunfs/root/chunk-other.js"] == 200, "a module with no call site lost its bytecode"
    assert bytecode["/$bunfs/root/cli"] == 100, "the entry module lost its bytecode"


def test_source_rewritten_but_bytecode_intact_is_not_done():
    # The measured failure: the text edit alone leaves Bun running the bytecode,
    # so the screen stays stock. Such a binary must be finished, not skipped.
    half = stock().replace(b'return mt("permission",', b'return mt("ansi:blue" ,')
    half = half.replace(b'=mt("suggestion",', b'=mt("ansi:blue" ,')
    result = m.patch(half)
    assert result is not None, "source-only edit reported as already patched"
    out, report = result
    assert report["rewritten"] == 0
    assert bytecode_by_name(out)["/$bunfs/root/chunk-tips.js"] == 0, "bytecode not dropped on a half-patched binary"


def test_idempotent():
    once = m.patch(stock())[0]
    assert m.patch(once) is None, "second pass did not recognise its own output"


def test_captures_the_minified_helper_name():
    # The helper was Ro in 2.1.202, Zn in 2.1.210, zn in 2.1.212, mt in 2.1.272.
    out, report = m.patch(stock(helper=b"Zn"))
    assert report["helper"] == "Zn"
    assert out.count(b'Zn("ansi:blue" ,') == 3, "helper name not followed"


def test_leaves_longer_identifiers_alone():
    out = m.patch(stock())[0]
    assert b'xmt("suggestion",k)' in out, "rewrote a call to a different function (xmt)"


def test_refuses_without_the_codespan_anchor():
    refuses(stock().replace(b'case"codespan"', b'case"codespam"'), "inline-code render path renamed")


def test_refuses_without_suggestion_sites():
    refuses(build([(b"/$bunfs/root/chunk-render.js", CODESPAN_SRC, 400)]), "no tip call sites")


def test_refuses_a_call_site_outside_every_module():
    lone = build([(b"/$bunfs/root/chunk-tips.js", SUGGESTION_SRC, 300)], prefix=CODESPAN_SRC)
    refuses(lone, "the codespan call sits outside every module's contents")


def test_refuses_an_unrecognised_module_table():
    src = stock()
    refuses(src.replace(b"/$bunfs/root/", b"/elsewhere/xx"), "module names not under /$bunfs/")
    refuses(src.replace(m.TRAILER, b"\n---- Bux! ----\n"), "no Bun trailer")


def test_palette_4_is_the_colour_the_tokens_were_meant_to_be():
    # The patch trades the theme's suggestion/permission values for ANSI blue. That
    # only keeps Midori's colours while Ghostty palette 4 equals those values.
    watcher = open(os.path.join(REPO, "watcher", "midori-claude-theme.sh"), encoding="utf-8").read()
    for token in ("suggestion", "permission"):
        values = [v.lower() for v in re.findall(rf'"{token}": "(#[0-9a-fA-F]{{6}})"', watcher)]
        assert len(values) == 2, f"expected a light and a dark {token} in the watcher, found {values}"
        for theme, value in zip(("midori-paper", "midori-night"), values):
            text = open(os.path.join(REPO, "ghostty", "themes", theme), encoding="utf-8").read()
            palette = re.search(r"^palette = 4=(#[0-9a-fA-F]{6})\s*$", text, re.M)
            assert palette, f"{theme}: palette 4 not found"
            assert palette.group(1).lower() == value, (
                f"{theme} palette 4 is {palette.group(1)} but the watcher's {token} is {value}"
            )


# ── runner ───────────────────────────────────────────────────────────────────

def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:  # unexpected error = failure
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed ({len(tests)} total)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
