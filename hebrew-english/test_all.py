#!/usr/bin/env python3
"""
Comprehensive test suite for dub-switch Hebrew↔English keyboard switcher.
20 tests covering layout mapping, language detection, conversion logic,
buffer behavior, and edge cases.

Run:  python3 -m pytest test_all.py -v
"""

import sys
import os
import threading

sys.path.insert(0, os.path.dirname(__file__))

import pytest
from layout import convert_text, detect_language, EN_TO_HE, HE_TO_EN, HEBREW_CHARS


# ═══════════════════════════════════════════════════════════════════════════════
# 1-4: Language detection
# ═══════════════════════════════════════════════════════════════════════════════

def test_01_detect_pure_english():
    """Pure ASCII alpha text is detected as english."""
    assert detect_language("hello") == "english"
    assert detect_language("A") == "english"
    assert detect_language("Hello World") == "english"


def test_02_detect_pure_hebrew():
    """Pure Hebrew character text is detected as hebrew."""
    assert detect_language("שלום") == "hebrew"
    assert detect_language("ש") == "hebrew"
    assert detect_language("שלום עולם") == "hebrew"


def test_03_detect_mixed():
    """Text with both Hebrew and ASCII alpha chars is mixed."""
    assert detect_language("hello שלום") == "mixed"
    assert detect_language("aש") == "mixed"


def test_04_detect_edge_cases():
    """Digits are in HEBREW_CHARS (they map to themselves in EN_TO_HE),
    so digit-only text is detected as 'hebrew'. Spaces/empty are 'mixed'."""
    # Digits are values in EN_TO_HE ('1':'1'), so they're in HEBREW_CHARS
    assert detect_language("123") == "hebrew"

    # Spaces and empty strings have no hebrew or english → mixed
    assert detect_language("   ") == "mixed"
    assert detect_language("") == "mixed"

    # Punctuation not in HEBREW_CHARS → mixed
    assert detect_language("!@#") == "mixed"


# ═══════════════════════════════════════════════════════════════════════════════
# 5-9: English → Hebrew conversion
# ═══════════════════════════════════════════════════════════════════════════════

def test_05_en_to_he_basic_word():
    """'akuo' on a QWERTY keyboard maps to שלום on Hebrew layout."""
    assert convert_text("akuo") == "שלום"


def test_06_en_to_he_uppercase_treated_as_lowercase():
    """Uppercase English letters convert the same as lowercase."""
    assert convert_text("AKUO") == "שלום"
    assert convert_text("AkUo") == "שלום"


def test_07_en_to_he_with_spaces():
    """Multi-word phrases preserve spaces."""
    assert convert_text("akuo akuo") == "שלום שלום"


def test_08_en_to_he_special_chars():
    """Punctuation keys convert when part of English text (not standalone).
    Standalone punctuation has no alpha chars, so detect_language returns
    'mixed' and punctuation passes through since it's not in HEBREW_CHARS."""
    # Standalone punctuation passes through (no alpha to trigger english detection)
    assert convert_text(";") == ";"
    assert convert_text(",") == ","

    # But when mixed with English alpha, punctuation converts via EN_TO_HE
    assert convert_text("a;") == "שף"
    assert convert_text("a,") == "שת"
    assert convert_text("a.") == "שץ"
    assert convert_text("w") == "׳"  # 'w' is alpha, so detected as english


def test_09_en_to_he_full_alphabet():
    """Every lowercase letter a-z has an EN_TO_HE mapping."""
    for ch in "abcdefghijklmnopqrstuvwxyz":
        assert ch in EN_TO_HE, f"'{ch}' missing from EN_TO_HE"


# ═══════════════════════════════════════════════════════════════════════════════
# 10-13: Hebrew → English conversion
# ═══════════════════════════════════════════════════════════════════════════════

def test_10_he_to_en_basic_word():
    """שלום maps back to 'akuo'."""
    assert convert_text("שלום") == "akuo"


def test_11_he_to_en_with_spaces():
    """Multi-word Hebrew preserves spaces."""
    assert convert_text("שלום שלום") == "akuo akuo"


def test_12_he_to_en_geresh():
    """׳ (Hebrew geresh, U+05F3) maps to 'w'."""
    assert convert_text("׳") == "w"


def test_13_he_to_en_inverse_completeness():
    """Every lowercase EN_TO_HE entry has a matching HE_TO_EN reverse."""
    for en_char, he_char in EN_TO_HE.items():
        if en_char.islower():
            assert he_char in HE_TO_EN, f"HE_TO_EN missing '{he_char}' (from '{en_char}')"
            assert HE_TO_EN[he_char] == en_char, (
                f"HE_TO_EN['{he_char}'] = '{HE_TO_EN[he_char]}', expected '{en_char}'"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 14-16: Round-trip fidelity
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("word", ["akuo", "hello", "vsrgev", "w", "abc"])
def test_14_roundtrip_en_he_en(word):
    """English → Hebrew → English round-trip returns the original."""
    assert convert_text(convert_text(word)) == word


@pytest.mark.parametrize("word", ["שלום", "׳ישא", "יקךךם", "ש"])
def test_15_roundtrip_he_en_he(word):
    """Hebrew → English → Hebrew round-trip returns the original."""
    assert convert_text(convert_text(word)) == word


def test_16_digits_passthrough():
    """Digits map to themselves and round-trip unchanged."""
    assert convert_text("123") == "123"
    assert convert_text("0") == "0"
    assert convert_text("9876543210") == "9876543210"


# ═══════════════════════════════════════════════════════════════════════════════
# 17: Mixed-language conversion
# ═══════════════════════════════════════════════════════════════════════════════

def test_17_mixed_text_per_char():
    """Mixed Hebrew+English text converts each char based on its type."""
    # 'a' is English → ש, 'ש' is Hebrew → a
    result = convert_text("aש")
    assert result == "שa"


# ═══════════════════════════════════════════════════════════════════════════════
# 18: Unmapped characters pass through
# ═══════════════════════════════════════════════════════════════════════════════

def test_18_unmapped_chars_passthrough():
    """Characters not in the mapping tables pass through unchanged."""
    # These symbols aren't in EN_TO_HE or HE_TO_EN
    result = convert_text("hello!")
    he_hello = convert_text("hello")
    assert result == he_hello + "!"

    # Emoji should pass through
    result2 = convert_text("שלום" + "!")
    en_shalom = convert_text("שלום")
    assert result2 == en_shalom + "!"


# ═══════════════════════════════════════════════════════════════════════════════
# 19-20: Buffer and app-level logic (unit-testable parts)
# ═══════════════════════════════════════════════════════════════════════════════

def test_19_buffer_reset_on_idle(monkeypatch):
    """Buffer is cleared after IDLE_RESET_SECONDS of inactivity."""
    # We test the reset_buffer + schedule_idle_reset logic directly
    # by importing from app and manipulating the buffer
    import app

    # Patch IDLE_RESET_SECONDS to something tiny for testing
    monkeypatch.setattr(app, 'IDLE_RESET_SECONDS', 0.1)

    with app.buffer_lock:
        app.buffer = list("test")
    assert len(app.buffer) == 4

    app.schedule_idle_reset()
    # Wait for the timer to fire
    import time
    time.sleep(0.3)

    with app.buffer_lock:
        assert app.buffer == [], f"Buffer should be empty after idle reset, got {app.buffer}"


def test_20_conversion_lock_prevents_reentry():
    """Only one conversion can run at a time (conversion_lock)."""
    import app

    # Acquire the lock manually
    acquired = app._conversion_lock.acquire(blocking=False)
    assert acquired, "Lock should be acquirable"

    # Now do_conversion should bail immediately
    # We can verify by checking it returns without error
    # and doesn't modify buffer
    app.buffer = list("test")
    app.is_typing = False
    app.pressed_keys = set()

    # do_conversion should see the lock is held and return immediately
    app.do_conversion()

    # Buffer should be unchanged (do_conversion bailed)
    assert app.buffer == list("test"), "Buffer should be unchanged when lock is held"

    app._conversion_lock.release()
    app.buffer = []  # clean up
