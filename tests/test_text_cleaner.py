# tests/test_text_cleaner.py

import re
import html as html_mod
import unicodedata

import pytest
from api.config import (
    BANNER_PATTERNS,
    SINGLE_LETTER_WHITELIST,
    STOPWORDS,
    PHONE_RE,
    CURRENCY_RE,
    CURRENCY_TRAIL_RE,
    PERCENT_RE,
    TIME_RE,
    URL_RE,
    EMAIL_RE,
    DATE_RE,
    PLACEHOLDER_TOKENS,
    BASE_THRESHOLD,
)
from api.preprocessing.text_cleaner import (
    normalize_unicode,
    strip_banners,
    join_fragmented_words,
    remove_isolated_letters,
    redact_contacts,
    placeholder_substitutions,
    clean_text,
    fuzzy_reverse_lookup,
    adaptive_threshold,
)
from deep_translator import GoogleTranslator
from difflib import get_close_matches


def test_normalize_unicode_combining():
    # "e" + combining acute → single "é"
    s = "e\u0301"
    assert normalize_unicode(s) == "é"


def test_strip_avis_banner():
    text = "avis: courriel externe. soyez vigilant. Hello World"
    assert strip_banners(text) == "Hello World"

def test_strip_attention_banner():
    text = "attention: external email YOU HAVE MAIL. Something else"
    assert strip_banners(text) == "Something else"

def test_no_banner_left_intact():
    text = "this is fine: no banner here"
    assert strip_banners(text) == text


def test_join_fragmented_words_newline_and_spaced():
    # newline join
    assert join_fragmented_words("pro\ngram") == "program"
    # spaced letters collapse
    spaced = "p r o g r a m m e"
    assert join_fragmented_words(spaced) == "programme"


def test_remove_isolated_letters():
    tokens = ["a", "b", "e", "x", "y", "z"]
    filtered = remove_isolated_letters(tokens)
    # 'a', 'e', 'y' are whitelisted; 'b','x','z' removed
    assert set(filtered) == {"a", "e", "y"}


def test_redact_contacts():
    inp = (
        "Email: test.user@example.com "
        "Phone: +1-800-123-4567 "
        "Site: www.example.org/page"
    )
    out = redact_contacts(inp)
    # everything matches replaced by blanks, collapsed to words
    assert "test.user" not in out
    assert "800" not in out
    assert "example.org" not in out
    # remaining words should be just the labels
    assert out.startswith("Email: Phone: Site:")


def test_placeholder_substitutions_currency_and_percent_and_time_and_url_and_email_and_date_and_phone():
    txt = "Paid €123.45 and $67 on 2025-07-23 at 13:05. Email me@foo.com or visit https://x.co. Tel: 123-4567"
    sub = placeholder_substitutions(txt)
    # Check each placeholder appears
    assert "<MONEY>" in sub
    assert "<PERCENT>" not in sub  # no percent in input
    assert "<TIME>" in sub
    assert "<URL>" in sub
    assert "<EMAIL>" in sub
    assert "<DATE>" in sub
    assert "<PHONE>" in sub


def test_clean_text_integration():
    raw = "Hello   WORLD!!! &amp; Good--bye   99999999"
    cleaned = clean_text(raw)
    # lowercased, entities unescaped, punctuation normalized, big digit blob removed
    assert "hello" in cleaned
    assert "&" not in cleaned
    assert "99999999" not in cleaned


def test_adaptive_threshold_returns_constant():
    assert adaptive_threshold([0.1, 0.9]) == BASE_THRESHOLD


class DummyTranslator:
    def __init__(self, source, target):
        self.source = source
        self.target = target
    def translate(self, word):
        # pretend French translation is word + "_fr"
        return word + "_fr"


def test_fuzzy_reverse_lookup_manual_and_fallback(monkeypatch):
    # monkeypatch manual map in module
    from api.preprocessing.text_cleaner import MANUAL_TRANSLATIONS
    MANUAL_TRANSLATIONS["foo"] = "barrier"
    # direct manual hit
    assert fuzzy_reverse_lookup("foo", "") == "barrier"

    # candidate list has "bonjour", so get_close_matches should find it
    original = "bonjour salut"
    res = fuzzy_reverse_lookup("hello", original)
    assert res in original.split()


def test_fuzzy_reverse_lookup_errors(monkeypatch):
    # if translator fails, returns input
    def bad_translator(source, target):
        raise RuntimeError("fail")
    monkeypatch.setattr(
        "api.preprocessing.text_cleaner.GoogleTranslator",
        lambda source, target: bad_translator
    )
    assert fuzzy_reverse_lookup("xyz", "anything") == "xyz"
