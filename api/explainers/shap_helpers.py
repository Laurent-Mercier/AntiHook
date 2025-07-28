# api/explainers/shap_helpers.py

import shap
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from typing import Dict, Any, List
from ..config import SENSITIVE_SUBSTRINGS
from ..preprocessing.text_cleaner import normalize_unicode, strip_banners  # if needed
from deep_translator import GoogleTranslator
from difflib import get_close_matches

# Cache for explainers
_shap_cache: Dict[str, Any] = {}

def _pipeline_transform(pipeline: Pipeline, X: np.ndarray) -> tuple[np.ndarray, Any]:
    """Run all but final step of pipeline on X."""
    for _, step in pipeline.steps[:-1]:
        X = step.transform(X)
    final_est = pipeline.steps[-1][1]
    return X, final_est

def _get_linear_explainer(key: str, estimator: Any, background: np.ndarray) -> shap.LinearExplainer:
    """Reuse or create a LinearExplainer."""
    cache_key = f"lin::{key}::{background.shape[1]}"
    if cache_key not in _shap_cache:
        _shap_cache[cache_key] = shap.LinearExplainer(estimator, background)
    return _shap_cache[cache_key]

def _get_tree_explainer(key: str, model_obj: Any, background: np.ndarray) -> shap.Explainer:
    """Reuse or create a Tree SHAP Explainer with Independent masker."""
    cache_key = f"tree::{key}"
    if cache_key not in _shap_cache:
        masker = shap.maskers.Independent(background)
        _shap_cache[cache_key] = shap.Explainer(model_obj, masker)
    return _shap_cache[cache_key]

def compute_shap_row(
    model_name: str,
    model_obj: Any,
    X_dense: np.ndarray,
    background: np.ndarray
) -> np.ndarray:
    """
    Compute SHAP values for one sample:
      - Linear/Pipeline → LinearExplainer
      - Tree models → shap.Explainer
    Returns 1d array of length = n_features.
    """
    # Linear or Logistic
    if isinstance(model_obj, LogisticRegression) or (
       isinstance(model_obj, Pipeline) and
       isinstance(model_obj.steps[-1][1], LogisticRegression)
    ):
        if isinstance(model_obj, Pipeline):
            bg_mat, final_est = _pipeline_transform(model_obj, background.copy())
            samp_mat, _     = _pipeline_transform(model_obj, X_dense.copy())
        else:
            final_est = model_obj
            bg_mat, samp_mat = background, X_dense

        expl = _get_linear_explainer(model_name, final_est, bg_mat)
        vals = expl(samp_mat).values
        row = vals[0]  # single sample
        return row

    # Tree‐based
    expl = _get_tree_explainer(model_name, model_obj, background)
    outs = expl(X_dense).values
    if outs.ndim == 2:
        return outs[0]
    if outs.ndim == 3:
        cls = 1 if outs.shape[2] > 1 else 0
        return outs[0, :, cls]
    raise RuntimeError(f"Unexpected SHAP shape: {outs.shape}")

def aggregate_shap(
    X_dense: np.ndarray,
    feature_names: np.ndarray,
    models: Dict[str, Any],
    background: np.ndarray,
    original_text_fr: str | None,
    detected_lang: str
) -> List[Dict[str, Any]]:
    """
    Average SHAP rows across models, pick top‑10 by abs(value),
    map tokens back to French if needed, filter PII tokens.
    """
    total = np.zeros(X_dense.shape[1])
    count = 0

    for name, mdl in models.items():
        try:
            row = compute_shap_row(name, mdl, X_dense, background)
            total += row
            count += 1
        except Exception as e:
            print(f"[⚠️] SHAP failed for {name}: {e}")

    if count == 0:
        return [{"word": "[no shap]", "impact": 0.0}]

    avg = total / count
    nz_idx = X_dense[0].nonzero()[0]
    if not len(nz_idx):
        return [{"word": "[no meaningful words]", "impact": 0.0}]

    top10 = sorted(nz_idx, key=lambda i: abs(avg[i]), reverse=True)[:10]
    expl: List[Dict[str, Any]] = []

    for i in top10:
        token = feature_names[i]
        impact = float(avg[i])
        # French reverse lookup
        if detected_lang == "fr" and original_text_fr:
            guess = GoogleTranslator(source="en", target="fr").translate(token).lower()
            match = get_close_matches(guess, original_text_fr.lower().split(), n=1, cutoff=0.85)
            display = match[0] if match else guess
        else:
            display = token

        expl.append({"word": display, "impact": round(impact, 4)})

    # filter out sensitive substrings
    filtered = [e for e in expl if not any(ss in e["word"].lower() for ss in SENSITIVE_SUBSTRINGS)]
    return filtered or expl
