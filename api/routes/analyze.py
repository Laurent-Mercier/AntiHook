# api/routes/analyze.py

from fastapi import APIRouter
from pydantic import BaseModel
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from langdetect import detect
import joblib
import numpy as np
import __main__ 

from ..config import (
    TEXT_MODEL_PATHS,
    LINK_MODEL_PATHS,
    VECTORIZER_PATH,
    LINK_VECTORIZER_PATH,
    SHAP_BACKGROUND_TEXTS,
    TEXT_MODEL_WEIGHTS,
    LINK_MODEL_WEIGHTS,
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

from ..preprocessing.url_processing import URLFeatureExtractor
__main__.URLFeatureExtractor = URLFeatureExtractor

from ..inference.ensemble import (
    load_models,
    weighted_vote,
    consensus_adjustment,
    apply_gray_band_rule,
    apply_money_only_rule,
)
from ..explainers.shap_helpers import aggregate_shap

router = APIRouter()

# load artifacts once at import
text_models = load_models(TEXT_MODEL_PATHS)
link_models = load_models(LINK_MODEL_PATHS)
vectorizer   = joblib.load(VECTORIZER_PATH)
link_vector  = joblib.load(LINK_VECTORIZER_PATH)
feature_names = vectorizer.get_feature_names_out()

# prepare SHAP background
_bg_sparse = vectorizer.transform([clean_text(t) for t in SHAP_BACKGROUND_TEXTS])
_bg_dense  = _bg_sparse.toarray()

class HtmlRequest(BaseModel):
    html: str

@router.post("/analyze_html")
async def analyze_html(req: HtmlRequest):
    # 1) Extract & redact PII
    soup = BeautifulSoup(req.html, "html.parser")
    raw  = soup.get_text(separator="\n").strip()
    redacted = redact_contacts(raw)

    # 2) Language detect & strip banners
    lang = detect(redacted) if redacted else "unknown"
    stripped = strip_banners(redacted)
    fr_source = stripped if lang == "fr" else None

    # 3) Translate if French
    if lang == "fr":
        try:
            translated = GoogleTranslator(source="fr", target="en").translate(stripped)
        except:
            translated = stripped
    else:
        translated = stripped

    # 4) Clean & vectorize text
    cleaned    = clean_text(translated)
    X_text_sp  = vectorizer.transform([cleaned])
    X_text_den = X_text_sp.toarray()

    # 5) Text ensemble
    txt_prob, txt_map, txt_vs, txt_wt = weighted_vote(
        text_models, TEXT_MODEL_WEIGHTS, X_text_sp, X_text_den
    )

    # 6) Link extraction + ensemble
    hrefs = [a.get("originalsrc") or a["href"] for a in soup.find_all("a", href=True)]
    hrefs = list(dict.fromkeys(hrefs))
    if hrefs:
        X_link_sp  = link_vector.transform(hrefs)
        X_link_den = X_link_sp.toarray()
        lnk_prob, lnk_map, lnk_vs, lnk_wt = weighted_vote(
            link_models, LINK_MODEL_WEIGHTS, X_link_sp, X_link_den
        )
        total_vs = txt_vs + lnk_vs
        total_wt = txt_wt + lnk_wt
        final_prob = total_vs / total_wt
        merged_map = {**txt_map, **lnk_map}
        base_dec = total_vs >= (BASE_THRESHOLD * total_wt)
        is_phish = consensus_adjustment(base_dec, final_prob, merged_map, BASE_THRESHOLD)
    else:
        final_prob = txt_prob
        merged_map = txt_map
        base_dec = txt_vs >= (BASE_THRESHOLD * txt_wt)
        is_phish = consensus_adjustment(base_dec, final_prob, txt_map, BASE_THRESHOLD)

    # 7) SHAP explanation (text only)
    explanation = aggregate_shap(
        X_dense=X_text_den,
        feature_names=feature_names,
        models=text_models,
        background=_bg_dense,
        original_text_fr=fr_source,
        detected_lang=lang,
    )

    # 8) Heuristic tweaks
    is_phish = apply_gray_band_rule(is_phish, final_prob, cleaned)
    is_phish = apply_money_only_rule(is_phish, final_prob, explanation)

    return {
        "is_phishing": bool(is_phish),
        "confidence":  round(final_prob, 4),
        "language":    lang,
        "explanation": explanation,
    }