# tests/test_analyze.py

import pytest
import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.analyze import router

# ─── Dummy stand‑ins ─────────────────────────────────────────────────────

class DummySP:
    """Mimic a sparse matrix with .toarray()."""
    def __init__(self, arr):
        self._arr = arr
    def toarray(self):
        return self._arr

class DummyVectorizer:
    """Always returns a 1×2 feature vector."""
    def transform(self, texts):
        # ignore texts, return shape (1,2)
        return DummySP(np.array([[0.1, 0.2]]))
    def get_feature_names_out(self):
        return np.array(["feat1", "feat2"])

def dummy_weighted_vote(models, weights, Xsp, Xdn):
    # ensemble probability .7, per‑model map, vote_score 0.7, total_weight 1.0
    return 0.7, {name: 0.7 for name in models}, 0.7, 1.0

def dummy_consensus_adjustment(decision, prob, per_model, threshold):
    # leave decision unchanged
    return decision

def dummy_gray(decision, prob, text):
    return decision

def dummy_money(decision, prob, explanation):
    return decision

def dummy_aggregate_shap(X_dense, feature_names, models, background,
                         original_text_fr, detected_lang):
    return [{"word": "feat1", "impact": 0.5}]

# ─── Pytest fixture to patch everything at import time ────────────────────

@pytest.fixture(autouse=True)
def patch_analyze_module(monkeypatch):
    import api.routes.analyze as mod

    # Always detect English
    monkeypatch.setattr(mod, "detect", lambda txt: "en")

    # Never actually call translator
    monkeypatch.setattr(mod, "GoogleTranslator", lambda **kw: None)

    # Swap in dummy vectorizers
    monkeypatch.setattr(mod, "vectorizer", DummyVectorizer())
    monkeypatch.setattr(mod, "link_vector", DummyVectorizer())

    # Replace models dicts with one dummy entry
    monkeypatch.setattr(mod, "text_models", {"dummy": None})
    monkeypatch.setattr(mod, "link_models", {"dummy_link": None})

    # Patch voting and heuristics
    monkeypatch.setattr(mod, "weighted_vote", dummy_weighted_vote)
    monkeypatch.setattr(mod, "consensus_adjustment", dummy_consensus_adjustment)
    monkeypatch.setattr(mod, "apply_gray_band_rule", dummy_gray)
    monkeypatch.setattr(mod, "apply_money_only_rule", dummy_money)
    monkeypatch.setattr(mod, "aggregate_shap", dummy_aggregate_shap)

    # Ensure SHAP background has matching dimension
    monkeypatch.setattr(mod, "_bg_dense", np.zeros((1, 2)))

# ─── Helper to mount router ───────────────────────────────────────────────

def make_app():
    app = FastAPI()
    app.include_router(router)
    return app

# ─── Tests ────────────────────────────────────────────────────────────────

def test_analyze_html_without_links():
    app = make_app()
    client = TestClient(app)

    payload = {"html": "<html><body><p>Hello, world!</p></body></html>"}
    resp = client.post("/analyze_html", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    # dummy_weighted_vote returns 0.7 but consensus makes decision False
    assert data["confidence"] == pytest.approx(0.7)
    # since base_dec = vote_score>=threshold but consensus leaves it unchanged:
    assert isinstance(data["is_phishing"], bool)
    assert data["language"] == "en"
    assert isinstance(data["explanation"], list)
    assert data["explanation"] == [{"word": "feat1", "impact": 0.5}]

def test_analyze_html_with_links():
    app = make_app()
    client = TestClient(app)

    # simple anchor tag triggers link‐branch
    payload = {"html": '<html><body><a href="http://example.com">click</a></body></html>'}
    resp = client.post("/analyze_html", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    # should behave similarly, but via combined text+link vote
    assert data["confidence"] == pytest.approx(0.7)
    assert isinstance(data["is_phishing"], bool)
    assert data["language"] == "en"
    assert isinstance(data["explanation"], list)
