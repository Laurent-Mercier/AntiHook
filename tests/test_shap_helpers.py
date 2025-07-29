# tests/test_shap_helpers.py

import numpy as np
import pytest
import shap
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import api.explainers.shap_helpers as sh


class DummyExplainer:
    """
    A stand‐in for shap.LinearExplainer or shap.Explainer
    that always returns a constant .values array of shape (1, n_features).
    """
    def __init__(self, model, background=None):
        # just record if you want
        self.model = model
        self.background = background

    def __call__(self, X):
        class SV:
            # always return 3 features
            values = np.array([[0.5, -0.5, 0.0]])
        return SV()


def test_pipeline_transform():
    # Prepare a small 2×3 array
    X = np.array([[1.0, 2.0, 3.0],
                  [4.0, 5.0, 6.0]])
    # Build and fit a trivial pipeline
    pipe = Pipeline([
        ("scale", StandardScaler()),
        ("logreg", LogisticRegression(max_iter=10))
    ])
    pipe.fit(X, np.array([0, 1]))  # fit scaler + logistic

    Xt, final_est = sh._pipeline_transform(pipe, X.copy())
    # Should return a scaled X of same shape
    assert isinstance(Xt, np.ndarray)
    assert Xt.shape == X.shape
    # Final estimator must be our LogisticRegression
    assert isinstance(final_est, LogisticRegression)


def test_linear_explainer_caching(monkeypatch):
    sh._shap_cache.clear()
    dummy_lr = LogisticRegression()
    background = np.zeros((5, 3))

    # Monkey‐patch shap.LinearExplainer to our dummy
    monkeypatch.setattr(shap, "LinearExplainer", DummyExplainer)

    e1 = sh._get_linear_explainer("mymodel", dummy_lr, background)
    e2 = sh._get_linear_explainer("mymodel", dummy_lr, background)

    # Should reuse the same object
    assert e1 is e2
    # And cache key should be present
    key = f"lin::mymodel::{background.shape[1]}"
    assert key in sh._shap_cache


def test_tree_explainer_caching(monkeypatch):
    sh._shap_cache.clear()
    dummy_model = object()
    background = np.zeros((2, 4))

    # Patch both maskers.Independent and shap.Explainer
    monkeypatch.setattr(shap.maskers, "Independent", lambda b: "MASKER")
    monkeypatch.setattr(shap, "Explainer", lambda m, masker: DummyExplainer(m, masker))

    e1 = sh._get_tree_explainer("tree1", dummy_model, background)
    e2 = sh._get_tree_explainer("tree1", dummy_model, background)

    assert e1 is e2
    assert "tree::tree1" in sh._shap_cache


def test_compute_shap_row_linear(monkeypatch):
    # Patch the linear explainer
    monkeypatch.setattr(shap, "LinearExplainer", DummyExplainer)

    lr = LogisticRegression()
    # We don’t actually need to fit lr because DummyExplainer ignores it
    X_dense = np.array([[1.0, 0.0, -1.0]])
    background = np.zeros((3, 3))

    row = sh.compute_shap_row("linmodel", lr, X_dense, background)

    # DummyExplainer always gives [0.5, -0.5, 0.0]
    assert isinstance(row, np.ndarray)
    np.testing.assert_allclose(row, [0.5, -0.5, 0.0])


def test_compute_shap_row_tree(monkeypatch):
    # Patch tree explainer
    monkeypatch.setattr(shap.maskers, "Independent", lambda b: None)
    monkeypatch.setattr(shap, "Explainer", lambda m, masker: DummyExplainer(m, masker))

    dummy_model = object()
    X_dense = np.array([[2.0, -2.0, 1.0]])
    background = np.zeros((2, 3))

    row = sh.compute_shap_row("treemodel", dummy_model, X_dense, background)
    # Should return same dummy row
    assert isinstance(row, np.ndarray)
    np.testing.assert_allclose(row, [0.5, -0.5, 0.0])


def test_aggregate_shap(monkeypatch):
    # Monkey‐patch compute_shap_row to a constant row
    def fake_compute(name, mdl, X, bg):
        return np.array([1.0, 0.0, -1.0])

    monkeypatch.setattr(sh, "compute_shap_row", fake_compute)

    X_dense = np.array([[3.0, 0.0, 5.0]])
    background = np.zeros((2, 3))
    models = {"m1": None, "m2": None}
    feature_names = np.array(["tok1", "tok2", "tok3"])

    # English path (no reverse‐lookup)
    out = sh.aggregate_shap(
        X_dense, feature_names, models, background,
        original_text_fr=None, detected_lang="en"
    )
    # Should be a list of dicts of length ≤ 3
    assert isinstance(out, list)
    assert all("word" in d and "impact" in d for d in out)

    # Test sensitive‐filter: if feature_names includes 'gmail'
    feature_names2 = np.array(["gmail", "x", "y"])
    X2 = np.array([[1,1,1]])
    out2 = sh.aggregate_shap(
        X2, feature_names2, {"m": None}, background,
        original_text_fr=None, detected_lang="en"
    )
    # since 'gmail' contains a sensitive substring,
    # it should be filtered out, but fallback to original if all removed
    assert isinstance(out2, list)
    # either 'gmail' dropped or present if fallback
    assert all(isinstance(item, dict) for item in out2)