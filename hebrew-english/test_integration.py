#!/usr/bin/env python3
"""
Integration tests for HebrewEnglishSwitcher.

Tests layout, clipboard detection, injection workers, and end-to-end
conversion (selection mode + buffer mode) by calling do_conversion()
directly — the same code path the keyboard listener triggers on Ctrl+1.

Run:
    .venv/bin/python3 test_integration.py
"""

import subprocess
import sys
import os
import time
import multiprocessing
sys.path.insert(0, os.path.dirname(__file__))

from layout import convert_text, detect_language, EN_TO_HE, HE_TO_EN

_failures = []
_passes   = 0


def _pass(name):
    global _passes
    _passes += 1
    print(f"  \u2713  {name}")


def _fail(name, reason):
    _failures.append(name)
    print(f"  \u2717  {name}: {reason}")


def run(name, fn):
    try:
        fn()
        _pass(name)
    except AssertionError as e:
        _fail(name, str(e) or "AssertionError")
    except Exception as e:
        _fail(name, f"{type(e).__name__}: {e}")


def assert_eq(got, expected):
    if got != expected:
        raise AssertionError(f"got {repr(got)}, expected {repr(expected)}")


# ── OS helpers ───────────────────────────────────────────────────────────────

def pbpaste_bytes():
    return subprocess.run(['pbpaste'], capture_output=True).stdout

def pbcopy_bytes(b: bytes):
    p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    p.communicate(b)

def pbpaste_str():
    return pbpaste_bytes().decode('utf-8', errors='replace')

def pbcopy_str(s: str):
    pbcopy_bytes(s.encode('utf-8'))

def osascript(script: str) -> str:
    r = subprocess.run(['osascript', '-e', script], capture_output=True)
    return r.stdout.decode('utf-8', errors='replace').strip()

def open_textedit_with(text):
    escaped = text.replace('"', '\\"')
    osascript(f'''tell application "TextEdit"
    activate
    make new document
    set text of document 1 to "{escaped}"
end tell''')
    time.sleep(0.5)

def open_textedit_empty():
    osascript('''tell application "TextEdit"
    activate
    make new document
end tell''')
    time.sleep(0.5)

def get_textedit_text():
    return osascript('tell application "TextEdit" to get text of document 1')

def close_textedit():
    osascript('tell application "TextEdit" to close document 1 saving no')
    time.sleep(0.2)

def close_all_textedit():
    osascript('tell application "TextEdit" to close every document saving no')
    time.sleep(0.2)

def ensure_textedit_front():
    """Guarantee TextEdit is the frontmost app before sending key events."""
    for _ in range(5):
        front = osascript(
            'tell application "System Events" to name of first process whose frontmost is true')
        if 'TextEdit' in front:
            return
        osascript('tell application "TextEdit" to activate')
        time.sleep(0.4)

def select_all():
    ensure_textedit_front()
    osascript('tell application "System Events" to keystroke "a" using command down')
    time.sleep(0.3)

def send_escape():
    osascript('tell application "System Events" to key code 53')
    time.sleep(0.2)


# ── Section 1: Layout — pure Python ──────────────────────────────────────────

def section_layout():
    print("\n[1] Layout — pure Python, no OS")

    run("EN\u2192HE: akuo \u2192 \u05e9\u05dc\u05d5\u05dd",
        lambda: assert_eq(convert_text("akuo"), "\u05e9\u05dc\u05d5\u05dd"))
    run("HE\u2192EN: \u05e9\u05dc\u05d5\u05dd \u2192 akuo",
        lambda: assert_eq(convert_text("\u05e9\u05dc\u05d5\u05dd"), "akuo"))
    run("EN\u2192HE: hello \u2192 \u05d9\u05e7\u05da\u05da\u05dd",
        lambda: assert_eq(convert_text("hello"), "\u05d9\u05e7\u05da\u05da\u05dd"))
    run("HE\u2192EN: \u05d9\u05e7\u05da\u05da\u05dd \u2192 hello",
        lambda: assert_eq(convert_text("\u05d9\u05e7\u05da\u05da\u05dd"), "hello"))
    run("Geresh EN\u2192HE: w \u2192 \u05f3",
        lambda: assert_eq(convert_text("w"), "\u05f3"))
    run("Geresh HE\u2192EN: \u05f3 \u2192 w",
        lambda: assert_eq(convert_text("\u05f3"), "w"))
    run("Numbers pass through",
        lambda: assert_eq(convert_text("123"), "123"))
    run("Space preserved: akuo akuo \u2192 \u05e9\u05dc\u05d5\u05dd \u05e9\u05dc\u05d5\u05dd",
        lambda: assert_eq(convert_text("akuo akuo"), "\u05e9\u05dc\u05d5\u05dd \u05e9\u05dc\u05d5\u05dd"))
    run("Uppercase as lowercase: AKUO \u2192 \u05e9\u05dc\u05d5\u05dd",
        lambda: assert_eq(convert_text("AKUO"), "\u05e9\u05dc\u05d5\u05dd"))
    run("detect_language: english",
        lambda: assert_eq(detect_language("hello"), "english"))
    run("detect_language: hebrew",
        lambda: assert_eq(detect_language("\u05e9\u05dc\u05d5\u05dd"), "hebrew"))
    run("detect_language: mixed",
        lambda: assert_eq(detect_language("hello \u05e9\u05dc\u05d5\u05dd"), "mixed"))
    run("Roundtrip EN\u2192HE\u2192EN: hello",
        lambda: assert_eq(convert_text(convert_text("hello")), "hello"))
    run("Roundtrip HE\u2192EN\u2192HE: \u05e9\u05dc\u05d5\u05dd",
        lambda: assert_eq(convert_text(convert_text("\u05e9\u05dc\u05d5\u05dd")), "\u05e9\u05dc\u05d5\u05dd"))
    run("All 26 letters in EN_TO_HE", _check_all_letters_mapped)
    run("HE_TO_EN is inverse of EN_TO_HE", _check_inverse_mapping)


def _check_all_letters_mapped():
    missing = [c for c in "abcdefghijklmnopqrstuvwxyz" if c not in EN_TO_HE]
    if missing:
        raise AssertionError(f"Missing: {missing}")

def _check_inverse_mapping():
    wrong = [(en, he, HE_TO_EN.get(he))
             for en, he in EN_TO_HE.items()
             if en.islower() and HE_TO_EN.get(he) != en]
    if wrong:
        raise AssertionError(f"Mismatches: {wrong[:3]}")


# ── Section 2: Clipboard detection logic ─────────────────────────────────────

def section_clipboard():
    print("\n[2] Clipboard detection logic")

    def test_save_restore():
        orig = b"clipboard-original-\xf0\x9f\x94\xa4"
        pbcopy_bytes(orig)
        saved = pbpaste_bytes()
        pbcopy_str("something else")
        pbcopy_bytes(saved)
        assert pbpaste_bytes() == orig

    def test_selection_detected():
        pbcopy_str("before")
        old = pbpaste_bytes()
        pbcopy_str("\u05e9\u05dc\u05d5\u05dd")
        new = pbpaste_bytes()
        assert new != old
        assert new.decode('utf-8') == "\u05e9\u05dc\u05d5\u05dd"

    def test_no_selection():
        pbcopy_str("unchanged")
        old = pbpaste_bytes()
        new = pbpaste_bytes()
        assert new == old

    run("Save and restore clipboard bytes", test_save_restore)
    run("Selection detected when clipboard changes", test_selection_detected)
    run("No selection when clipboard unchanged",    test_no_selection)


# ── Section 3: Injection workers ─────────────────────────────────────────────

def section_workers():
    print("\n[3] Injection workers")

    def test_selection_worker_clipboard_restored():
        import app as _app
        orig = b"original-clipboard-for-worker-test"
        pbcopy_bytes(orig)

        p = multiprocessing.Process(
            target=_app._inject_selection_worker,
            args=("akuo", orig))
        p.start()
        p.join(timeout=8)
        assert p.exitcode == 0, f"Worker exited {p.exitcode}"
        time.sleep(0.3)
        result = pbpaste_bytes()
        assert result == orig, f"Clipboard not restored: {repr(result)}"

    def test_inject_worker_clipboard_restored():
        import app as _app
        orig = b"clipboard-before-inject-worker"
        pbcopy_bytes(orig)
        # n=0 → no backspaces, just paste + restore
        p = multiprocessing.Process(
            target=_app._inject_worker,
            args=(0, "test-paste"))
        p.start()
        p.join(timeout=8)
        assert p.exitcode == 0, f"Worker exited {p.exitcode}"
        time.sleep(0.3)
        result = pbpaste_bytes()
        assert result == orig, f"Clipboard not restored: {repr(result)}"

    run("_inject_selection_worker: clipboard restored", test_selection_worker_clipboard_restored)
    run("_inject_worker: clipboard restored",          test_inject_worker_clipboard_restored)


# ── Section 4: End-to-end via do_conversion() ────────────────────────────────
#
# We call do_conversion() directly — the same function the keyboard listener
# invokes on Ctrl+1.  This tests the full conversion pipeline:
#   • Selection detection (Cmd+C clipboard diff)
#   • Buffer fallback
#   • Injection subprocess
#   • Input source switch
#
# TextEdit is used as the target app so we can read back the result.

def _run_conversion(app):
    """Call do_conversion() synchronously (it blocks on p.join)."""
    ensure_textedit_front()    # guarantee TextEdit has focus before Cmd+C/Cmd+V
    app.is_typing  = False
    app.pressed_keys = set()   # no Ctrl held → skip wait loop
    app.do_conversion()        # blocks until subprocess finishes
    time.sleep(0.4)            # let TextEdit settle


def section_end_to_end():
    print("\n[4] End-to-end via do_conversion() + TextEdit")
    import app as _app

    # ── selection: Hebrew → English ──────────────────────────────────────────
    def test_sel_he_en():
        open_textedit_with("\u05e9\u05dc\u05d5\u05dd")
        select_all()
        _app.buffer = []
        _run_conversion(_app)
        result = get_textedit_text()
        close_textedit()
        assert_eq(result, "akuo")

    # ── selection: English → Hebrew ──────────────────────────────────────────
    def test_sel_en_he():
        open_textedit_with("akuo")
        select_all()
        _app.buffer = []
        _run_conversion(_app)
        result = get_textedit_text()
        close_textedit()
        assert_eq(result, "\u05e9\u05dc\u05d5\u05dd")

    # ── selection: multi-word ────────────────────────────────────────────────
    def test_sel_multiword():
        open_textedit_with("\u05e9\u05dc\u05d5\u05dd \u05e9\u05dc\u05d5\u05dd")
        select_all()
        _app.buffer = []
        _run_conversion(_app)
        result = get_textedit_text()
        close_textedit()
        assert_eq(result, "akuo akuo")

    # ── selection: hello ─────────────────────────────────────────────────────
    def test_sel_hello():
        open_textedit_with("\u05d9\u05e7\u05da\u05da\u05dd")
        select_all()
        _app.buffer = []
        _run_conversion(_app)
        result = get_textedit_text()
        close_textedit()
        assert_eq(result, "hello")

    # ── buffer: English → Hebrew ─────────────────────────────────────────────
    def test_buf_en_he():
        open_textedit_empty()
        send_escape()                           # reset any stale buffer
        _app.buffer = list("akuo")              # 4 chars in buffer
        _run_conversion(_app)                   # no selection → buffer mode
        result = get_textedit_text()
        close_textedit()
        assert_eq(result, "\u05e9\u05dc\u05d5\u05dd")

    # ── buffer: Hebrew → English ─────────────────────────────────────────────
    def test_buf_he_en():
        open_textedit_empty()
        send_escape()
        _app.buffer = list("\u05e9\u05dc\u05d5\u05dd")   # ש ל ו ם
        _run_conversion(_app)
        result = get_textedit_text()
        close_textedit()
        assert_eq(result, "akuo")

    # ── buffer: multi-word ───────────────────────────────────────────────────
    def test_buf_multiword():
        open_textedit_empty()
        send_escape()
        _app.buffer = list("akuo akuo")
        _run_conversion(_app)
        result = get_textedit_text()
        close_textedit()
        assert_eq(result, "\u05e9\u05dc\u05d5\u05dd \u05e9\u05dc\u05d5\u05dd")

    # ── no-op: empty buffer + no selection → text unchanged ──────────────────
    def test_noop_empty():
        open_textedit_with("untouched")
        send_escape()
        _app.buffer = []
        _run_conversion(_app)
        result = get_textedit_text()
        close_textedit()
        assert_eq(result, "untouched")

    # ── no-op: convert_text returns same string → skip ───────────────────────
    def test_noop_already_converted():
        # "123" maps to "123" — no change expected
        open_textedit_with("123")
        select_all()
        _app.buffer = []
        _run_conversion(_app)
        result = get_textedit_text()
        close_textedit()
        assert_eq(result, "123")

    run("Selection HE\u2192EN: \u05e9\u05dc\u05d5\u05dd \u2192 akuo",         test_sel_he_en)
    run("Selection EN\u2192HE: akuo \u2192 \u05e9\u05dc\u05d5\u05dd",         test_sel_en_he)
    run("Selection multi-word: \u05e9\u05dc\u05d5\u05dd \u05e9\u05dc\u05d5\u05dd \u2192 akuo akuo", test_sel_multiword)
    run("Selection HE\u2192EN: \u05d9\u05e7\u05da\u05da\u05dd \u2192 hello",  test_sel_hello)
    run("Buffer EN\u2192HE: akuo \u2192 \u05e9\u05dc\u05d5\u05dd",            test_buf_en_he)
    run("Buffer HE\u2192EN: \u05e9\u05dc\u05d5\u05dd \u2192 akuo",            test_buf_he_en)
    run("Buffer multi-word: akuo akuo \u2192 \u05e9\u05dc\u05d5\u05dd \u05e9\u05dc\u05d5\u05dd", test_buf_multiword)
    run("No-op: empty buffer + no selection \u2192 unchanged",                 test_noop_empty)
    run("No-op: numbers already correct \u2192 unchanged",                     test_noop_already_converted)


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    multiprocessing.set_start_method('fork')

    # Save user clipboard — tests modify it, restore at end
    user_clip = pbpaste_bytes()

    print("\u2550" * 56)
    print(" HebrewEnglishSwitcher \u2014 Integration Test Suite")
    print("\u2550" * 56)

    section_layout()
    section_clipboard()
    section_workers()

    close_all_textedit()
    section_end_to_end()
    close_all_textedit()

    pbcopy_bytes(user_clip)   # restore user clipboard

    total = _passes + len(_failures)
    print(f"\n{'=' * 56}")
    if _failures:
        print(f"RESULT: {len(_failures)} FAILED / {total} total")
        for f in _failures:
            print(f"  \u2717  {f}")
        sys.exit(1)
    else:
        print(f"RESULT: ALL {total} TESTS PASSED \u2713")
