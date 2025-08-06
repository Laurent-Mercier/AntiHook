# api/config.py

import os
from typing import List, Dict

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Model & vectorizer file locations.
TEXT_MODEL_PATHS: Dict[str, str] = {
    "random_forest":           os.path.join(BASE_DIR, "models", "random_forest.pkl"),
    "random_forest_tuned":     os.path.join(BASE_DIR, "models", "random_forest_tuned.pkl"),
    "logistic_regression":     os.path.join(BASE_DIR, "models", "logistic_regression.pkl"),
    "hist_gradient_boosting":  os.path.join(BASE_DIR, "models", "hist_gradient_boosting.pkl"),
}
LINK_MODEL_PATHS: Dict[str, str] = {
    "link_random_forest":           os.path.join(BASE_DIR, "models", "link_random_forest.pkl"),
    "link_logistic_regression":     os.path.join(BASE_DIR, "models", "link_logistic_regression.pkl"),
    "link_hist_gradient_boosting":  os.path.join(BASE_DIR, "models", "link_hist_gradient_boosting.pkl"),
}
VECTORIZER_PATH      = os.path.join(BASE_DIR, "models", "email_vectorizer.pkl")
LINK_VECTORIZER_PATH = os.path.join(BASE_DIR, "models", "link_vectorizer.pkl")

# SHAP background seed texts.
SHAP_BACKGROUND_TEXTS: List[str] = [
    "dear customer your account has been suspended",
    "click here to verify your identity",
    "bank update required immediately",
    "this is a safe and verified email",
    "reset your password now",
    "thank you for your purchase",
    "please confirm your address"
]

# Ensemble & heuristic settings.
TEXT_MODEL_WEIGHTS = {
    "random_forest":           2.0,
    "random_forest_tuned":     1.0,
    "logistic_regression":     1.5,
    "hist_gradient_boosting":  2.5,
}
LINK_MODEL_WEIGHTS = {
    "link_random_forest":          2.0,
    "link_logistic_regression":    1.5,
    "link_hist_gradient_boosting": 2.5,
}
BASE_THRESHOLD      = 0.5
MIN_CONSENSUS_MODELS = 2
CONSENSUS_BAND       = 0.05

SENSITIVE_SUBSTRINGS = {
    "gmail", "hotmail", "outlook", "tel", "phone",
    "email", "courriel", "www", "http", "https"
}

# Text‐cleaning constants.
PLACEHOLDER_TOKENS = {"<MONEY>", "<TIME>", "<EMAIL>", "<PHONE>", "<PERCENT>", "<URL>", "<DATE>"}

BANNER_PATTERNS = [
    r"^avis:\s*courriel externe\.\s*soyez vigilant\.*",
    r"^attention:\s*external email.*?\.\s*"
]
SINGLE_LETTER_WHITELIST = {"a", "à", "e", "y", "i", "o"}
STOPWORDS = set()

MANUAL_TRANSLATIONS = {
    "click":    "cliquer",
    "account":  "compte",
    "password": "mot de passe",
    "login":    "connexion",
    "email":    "courriel",
}

# Regex for placeholders & redaction.
PHONE_RE          = r"(?:(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,5}\d{2,6})"
CURRENCY_RE       = r"(?:(?<=\s)|^)(?:€|eur|\$|usd|cad|chf|£)\s?\d+[.,]?\d*(?:\s?(?:€|eur|\$|usd|cad|chf|£))?(?=\s|$)"
CURRENCY_TRAIL_RE = r"\d+[.,]?\d*\s?(?:€|eur|\$|usd|cad|chf|£)"
TIME_RE           = r"\b(?:[01]?\d|2[0-3])[:h][0-5]\d(?:\s?(?:am|pm))?\b"
PERCENT_RE        = r"\b\d{1,3}(?:[.,]\d+)?\s?%\b"
URL_RE            = r"(?:https?://|ftp://|www\.)[^\s\)>\"\'<]{3,}"
EMAIL_RE          = r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
DATE_RE           = r"""(?:
    \b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b |
    \b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b |
    \b\d{1,2}\s+(?:janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc)[a-z]*\.?\s*(\d{4})?\b |
    \b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?\b
)"""
