# api/preprocessing/text_cleaner.py

import re
import html
import unicodedata
from deep_translator import GoogleTranslator
from typing import Dict, List, Tuple, Any
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
)

def normalize_unicode(text: str) -> str:
    """Normalize Unicode to NFC for consistent accent handling."""
    return unicodedata.normalize("NFC", text)

def strip_banners(text: str) -> str:
    """Remove any leading disclaimer/banner lines."""
    low = text.lower()
    for pat in BANNER_PATTERNS:
        m = re.match(pat, low)
        if m:
            return text[m.end():].lstrip()
    return text

def join_fragmented_words(text: str) -> str:
    """
    Reassemble words split across newlines or as spaced letters.
    E.g. "p r o g r a m m e" → "programme", "pro\ngram" → "program".
    """
    # letter + newline + letter → join
    text = re.sub(r"([A-Za-zÀ-ÖØ-öø-ÿ])\n+([A-Za-zÀ-ÖØ-öø-ÿ])", r"\1\2", text)
    # collapse sequences of single letters
    def collapse(m: re.Match) -> str:
        return "".join(m.group(0).split())
    return re.sub(r"(?:\b[A-Za-zÀ-ÖØ-öø-ÿ]\b\s+){2,}\b[A-Za-zÀ-ÖØ-öø-ÿ]\b",
                  collapse,
                  text)

def remove_isolated_letters(tokens: list[str]) -> list[str]:
    """Filter out stray single-character tokens (unless whitelisted)."""
    return [t for t in tokens
            if not (len(t) == 1 and t not in SINGLE_LETTER_WHITELIST)]

def redact_contacts(text: str) -> str:
    """Strip PII: emails, phones, bare domains/URLs."""
    for pattern in (EMAIL_RE, PHONE_RE, URL_RE):
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()

def placeholder_substitutions(text: str) -> str:
    """Replace currency, percent, time, URL, email, date, phone with placeholders."""
    text = re.sub(CURRENCY_RE,       " <MONEY> ", text, flags=re.IGNORECASE)
    text = re.sub(CURRENCY_TRAIL_RE, " <MONEY> ", text, flags=re.IGNORECASE)
    text = re.sub(PERCENT_RE,        " <PERCENT> ", text, flags=re.IGNORECASE)
    text = re.sub(TIME_RE,           " <TIME> ", text, flags=re.IGNORECASE)
    text = re.sub(URL_RE,            " <URL> ", text)
    text = re.sub(EMAIL_RE,          " <EMAIL> ", text)
    text = re.sub(DATE_RE,           " <DATE> ", text, flags=re.IGNORECASE | re.VERBOSE)
    def phone_filter(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        return " <PHONE> " if len(digits) >= 6 else m.group(0)
    return re.sub(PHONE_RE, phone_filter, text)

def clean_text(raw: str) -> str:
    """
    Full text pipeline:
    1. HTML‐entity unescape & Unicode normalize
    2. Rejoin fragmented words
    3. Placeholder subs
    4. Lowercase & restore placeholders
    5. Char filtering, digit blobs & repetition collapse
    6. Tokenize & drop stopwords/isolated letters
    """
    s = html.unescape(raw)
    s = normalize_unicode(s)
    s = join_fragmented_words(s)
    s = placeholder_substitutions(s)
    s = s.lower()
    # restore uppercase placeholders
    for ph in PLACEHOLDER_TOKENS:
        s = s.replace(ph.lower(), ph)
    # strip unwanted chars & collapse whitespace
    s = re.sub(r"[^\w\s<>\-.,]", " ", s)
    s = re.sub(r"\d{8,}", " ", s)
    s = re.sub(r"(.)\1{5,}", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()

    tokens = [t for t in s.split() if t not in STOPWORDS]
    tokens = remove_isolated_letters(tokens)
    return " ".join(tokens)

def fuzzy_reverse_lookup(word_en: str, original_text_fr: str) -> str:
    """
    Map an English token back to the closest French word
    present in the source text, using translation + fuzzy match.
    """
    try:
        low = word_en.lower()
        if low in MANUAL_TRANSLATIONS:
            return MANUAL_TRANSLATIONS[low]
        candidates = original_text_fr.lower().split()
        guess = GoogleTranslator(source="en", target="fr").translate(word_en).lower()
        match = get_close_matches(guess, candidates, n=1, cutoff=0.85)
        return match[0] if match else guess
    except Exception:
        return word_en

def adaptive_threshold(_probs: List[float]) -> float:
    """
    Placeholder for any dynamic threshold logic.
    Currently returns BASE_THRESHOLD unchanged.
    """
    return BASE_THRESHOLD
