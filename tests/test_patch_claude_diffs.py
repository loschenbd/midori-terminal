#!/usr/bin/env python3
"""Unit tests for tools/patch-claude-diffs.py — the one component with real,
fragile logic (regex rewrites, idempotency, fail-loud, minified-name capture).

No pytest / no network / no binary needed: the patcher operates on JS *strings*,
so we feed it synthetic fixtures built FROM the module's own TRIPLE_PATCHES (so a
future palette change updates the fixtures automatically instead of silently
falsifying the tests). Run:  python3 tests/test_patch_claude_diffs.py
"""
import contextlib
import importlib.util
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(HERE, "..", "tools", "patch-claude-diffs.py")


def _load():
    # Module filename has hyphens (not import-safe); load by path.
    spec = importlib.util.spec_from_file_location("patch_claude_diffs", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load()


def run_patch(src):
    """Call patch() while swallowing its progress print()."""
    with contextlib.redirect_stdout(io.StringIO()):
        return m.patch(src)


def stock_fixture(ctor="Xl", codespan_helper="Ro", triples=None):
    """A minimal chunk of 'minified JS' containing each stock triple exactly once
    (as `<ctor>(r,g,b)`) plus one codespan call `<helper>("permission",t)`."""
    triples = m.TRIPLE_PATCHES if triples is None else triples
    parts = [f"{ctor}({stock})" for stock, _, _ in triples]
    parts.append(f'{codespan_helper}("permission",t)')
    return "const T=[" + ",".join(parts) + "];"


# ── tests ────────────────────────────────────────────────────────────────────

def test_patches_all_triples_and_codespan():
    out = run_patch(stock_fixture())
    for stock, midori, label in m.TRIPLE_PATCHES:
        assert f"({midori})" in out, f"midori triple missing: {label}"
        assert f"({stock})" not in out, f"stock triple survived: {label}"
    assert m.MIDORI_CODESPAN in out, "codespan colour not injected"
    assert '"permission",t' not in out, "stock permission token survived"


def test_idempotent():
    once = run_patch(stock_fixture())
    twice = run_patch(once)
    assert once == twice, "second patch changed already-patched source (not idempotent)"


def test_preserves_minified_constructor_and_helper_names():
    # The exact churn that bit us in-session: Xl->ku (constructor), Ro->Zn (helper).
    out = run_patch(stock_fixture(ctor="ku", codespan_helper="Zn"))
    first_midori = m.TRIPLE_PATCHES[0][1]
    assert f"ku({first_midori})" in out, "constructor name not preserved on rewrite"
    assert f"Zn({m.MIDORI_CODESPAN},t)" in out, "helper name not preserved on codespan rewrite"


def test_fail_loud_on_zero_matches():
    # Drop one triple → that triple matches 0x and its midori isn't present → must ABORT.
    partial = stock_fixture(triples=m.TRIPLE_PATCHES[:-1])
    try:
        run_patch(partial)
    except SystemExit:
        return
    raise AssertionError("expected SystemExit when a stock triple is missing (palette changed)")


def test_fail_loud_on_multiple_matches():
    # Duplicate the first triple → 2 matches → ambiguous → must ABORT.
    first_stock = m.TRIPLE_PATCHES[0][0]
    ambiguous = stock_fixture() + f" Xl({first_stock});"
    try:
        run_patch(ambiguous)
    except SystemExit:
        return
    raise AssertionError("expected SystemExit when a stock triple matches more than once")


def test_codespan_alone_is_idempotent_skip():
    # Already-patched codespan (midori literal present) must be skipped, not double-wrapped.
    already = f"case codespan:return Zn({m.MIDORI_CODESPAN},t)(e.text);"
    out = run_patch(already + " " + stock_fixture())
    assert out.count(m.MIDORI_CODESPAN) == 1, "codespan double-applied over an existing patch"


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
