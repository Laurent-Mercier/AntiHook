# tests/test_ensemble.py

import os
import numpy as np
import pytest
from sklearn.base import BaseEstimator
from api.inference.ensemble import (
    weighted_vote,
    consensus_adjustment,
    apply_gray_band_rule,
    apply_money_only_rule,
)

class DummyModel(BaseEstimator):
    """A fake classifier that always returns a fixed probability."""
    def __init__(self, prob: float):
        self.prob = prob

    def predict_proba(self, X):
        # pretend binary probs [neg, pos]
        batch = np.atleast_2d(X)
        return np.stack([[1 - self.prob, self.prob]] * batch.shape[0], axis=0)

def test_weighted_vote_basic():
    # two models: one hist_gradient_boosting, one regular
    models = {
        "foo": DummyModel(0.2),
        "hist_gradient_boosting_bar": DummyModel(0.8),
    }
    weights = {"foo": 1.0, "hist_gradient_boosting_bar": 2.0}

    # dummy inputs (shape doesn’t matter for DummyModel)
    Xs = np.zeros((1, 3))
    Xd = np.zeros((1, 3))

    prob, per_model, vote_score, total_weight = weighted_vote(models, weights, Xs, Xd)

    # vote_score = 0.2*1 + 0.8*2 = 1.8, total_weight = 3
    assert total_weight == pytest.approx(3.0)
    assert vote_score == pytest.approx(1.8)
    assert prob == pytest.approx(1.8 / 3.0)

    assert per_model["foo"] == pytest.approx(0.2)
    assert per_model["hist_gradient_boosting_bar"] == pytest.approx(0.8)

def test_consensus_adjustment_within_band():
    per_model = {"a": 0.6, "b": 0.4, "c": 0.3}
    base = True
    threshold = 0.5
    # ensemble_prob inside [0.45, 0.55] and only one model ≥0.5 < MIN_CONSENSUS_MODELS(2)
    assert not consensus_adjustment(base, 0.5, per_model, threshold)

def test_consensus_adjustment_outside_band():
    per_model = {"a": 0.6, "b": 0.4, "c": 0.3}
    base = True
    threshold = 0.5
    # ensemble_prob = 0.6 outside band => unchanged
    assert consensus_adjustment(base, 0.6, per_model, threshold)

def test_apply_gray_band_rule_downgrade():
    # in gray band [0.5–0.7) and no high-risk keywords => False
    assert not apply_gray_band_rule(True, 0.6, "nothing risky here")

def test_apply_gray_band_rule_keep():
    # in gray band but text contains 'password' => stays True
    assert apply_gray_band_rule(True, 0.6, "please update your password")

def test_apply_gray_band_rule_outside_band():
    # outside band => unchanged
    assert apply_gray_band_rule(True, 0.8, "nothing risky here")

def test_apply_money_only_rule_downgrade():
    explanation = [
        {"word": "money", "impact": 1.0},
        {"word": "argent", "impact": 0.5},
        {"word": "<money>", "impact": 0.2},
    ]
    # below 0.75 => downgrade
    assert not apply_money_only_rule(True, 0.7, explanation)

def test_apply_money_only_rule_keep_high_confidence():
    explanation = [
        {"word": "money", "impact": 1.0},
        {"word": "argent", "impact": 0.5},
        {"word": "<money>", "impact": 0.2},
    ]
    # above 0.75 => stays True
    assert apply_money_only_rule(True, 0.8, explanation)

def test_apply_money_only_rule_non_money_top3():
    # if any of top3 is non‐money, stays True
    explanation = [
        {"word": "other", "impact": 1.0},
        {"word": "argent", "impact": 0.5},
        {"word": "<money>", "impact": 0.2},
    ]
    assert apply_money_only_rule(True, 0.7, explanation)