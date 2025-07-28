# api/inference/ensemble.py

import os
import joblib
from typing import Dict, Any, Tuple
from ..config import (
    TEXT_MODEL_PATHS,
    LINK_MODEL_PATHS,
    TEXT_MODEL_WEIGHTS,
    LINK_MODEL_WEIGHTS,
    BASE_THRESHOLD,
    MIN_CONSENSUS_MODELS,
    CONSENSUS_BAND,
    HIGH_RISK_KEYWORDS,
)

def load_models(paths: Dict[str, str]) -> Dict[str, Any]:
    """Load pickle models by name from disk, skipping missing ones."""
    models: Dict[str, Any] = {}
    for name, fp in paths.items():
        if not os.path.exists(fp):
            print(f"[⚠️] Missing model file: {fp}")
            continue
        models[name] = joblib.load(fp)
        print(f"[✅] Loaded model: {name}")
    return models

def weighted_vote(
    models: Dict[str, Any],
    weights: Dict[str, float],
    X_sparse,
    X_dense
) -> Tuple[float, Dict[str, float], float, float]:
    """
    Compute weighted ensemble probability.
    Returns (ensemble_prob, per_model_probs, vote_score, total_weight).
    """
    vote_score = 0.0
    total_weight = 0.0
    per_model = {}
    for name, mdl in models.items():
        inp = X_dense if "hist_gradient_boosting" in name else X_sparse
        p = float(mdl.predict_proba(inp)[0][1])
        w = weights.get(name, 1.0)
        per_model[name] = p
        vote_score += p * w
        total_weight += w

    ensemble_prob = vote_score / total_weight if total_weight else 0.0
    return ensemble_prob, per_model, vote_score, total_weight

def consensus_adjustment(
    base_decision: bool,
    ensemble_prob: float,
    per_model_probs: Dict[str, float],
    threshold: float
) -> bool:
    """
    If ensemble_prob lies within threshold±CONSENSUS_BAND,
    require at least MIN_CONSENSUS_MODELS models ≥0.5.
    """
    low = threshold - CONSENSUS_BAND
    high = threshold + CONSENSUS_BAND
    if low <= ensemble_prob <= high:
        count = sum(p >= 0.5 for p in per_model_probs.values())
        if base_decision and count < MIN_CONSENSUS_MODELS:
            return False
    return base_decision

def apply_gray_band_rule(
    decision: bool,
    ensemble_prob: float,
    cleaned_text: str
) -> bool:
    """
    If in [0.5, 0.7) and none of HIGH_RISK_KEYWORDS in text,
    downgrade to False.
    """
    if decision and 0.5 <= ensemble_prob < 0.7:
        if not any(k in cleaned_text.lower() for k in HIGH_RISK_KEYWORDS):
            return False
    return decision

def apply_money_only_rule(
    decision: bool,
    ensemble_prob: float,
    explanation: list[dict]
) -> bool:
    """
    If top‑3 tokens are all money‑like and prob<0.75,
    downgrade to False.
    """
    if decision and explanation:
        top3 = explanation[:3]
        money_only = all(
            tok["word"].lower().startswith("argent")
            or tok["word"].lower() in {"money", "<money>"}
            for tok in top3
        )
        if money_only and ensemble_prob < 0.75:
            return False
    return decision
