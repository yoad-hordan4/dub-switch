"""
Unit tests for layout.py — the Hebrew↔English character mapping.
No OS dependencies; runs anywhere Python is installed.

Run:
    .venv/bin/python3 -m pytest test_layout.py -v
"""

import pytest
from layout import convert_text, detect_language, EN_TO_HE, HE_TO_EN


# ── detect_language ────────────────────────────────────────────────────────────

def test_detect_english():
    assert detect_language("hello") == "english"

def test_detect_hebrew():
    assert detect_language("שלום") == "hebrew"

def test_detect_mixed():
    assert detect_language("hello שלום") == "mixed"


# ── English → Hebrew ───────────────────────────────────────────────────────────
# To type שלום on an English keyboard in Hebrew layout: a=ש k=ל u=ו o=ם → "akuo"

def test_en_to_he_word():
    assert convert_text("akuo") == "שלום"

def test_en_to_he_uppercase_treated_as_lowercase():
    assert convert_text("AKUO") == "שלום"

def test_en_to_he_with_space():
    assert convert_text("akuo akuo") == "שלום שלום"

def test_en_to_he_geresh():
    # 'w' → ׳ (Hebrew geresh, U+05F3)
    assert convert_text("w") == "׳"

def test_en_to_he_numbers_passthrough():
    assert convert_text("123") == "123"

def test_en_to_he_hello():
    # h=י e=ק l=ך l=ך o=ם
    assert convert_text("hello") == "יקךךם"


# ── Hebrew → English ───────────────────────────────────────────────────────────

def test_he_to_en_word():
    assert convert_text("שלום") == "akuo"

def test_he_to_en_with_space():
    assert convert_text("שלום שלום") == "akuo akuo"

def test_he_to_en_geresh():
    # ׳ (U+05F3) → 'w'
    assert convert_text("׳") == "w"

def test_he_to_en_numbers_passthrough():
    assert convert_text("123") == "123"

def test_he_to_en_hello():
    assert convert_text("יקךךם") == "hello"


# ── Round-trips ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("word", ["akuo", "hello", "vsrgev", "w"])
def test_roundtrip_en_he_en(word):
    assert convert_text(convert_text(word)) == word

@pytest.mark.parametrize("word", ["שלום", "׳ישא", "יקךךם"])
def test_roundtrip_he_en_he(word):
    assert convert_text(convert_text(word)) == word


# ── Mapping completeness ───────────────────────────────────────────────────────

def test_all_lowercase_letters_have_en_to_he_mapping():
    for ch in "abcdefghijklmnopqrstuvwxyz":
        assert ch in EN_TO_HE, f"'{ch}' missing from EN_TO_HE"

def test_he_to_en_is_inverse_of_en_to_he():
    for en_char, he_char in EN_TO_HE.items():
        if en_char.islower():
            assert HE_TO_EN.get(he_char) == en_char, (
                f"HE_TO_EN['{he_char}'] should be '{en_char}', got '{HE_TO_EN.get(he_char)}'"
            )
