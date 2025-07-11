from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from deep_translator import GoogleTranslator
from langdetect import detect
from bs4 import BeautifulSoup
import joblib
import shap
import numpy as np
import matplotlib.pyplot as plt
import re
import os
from difflib import get_close_matches

# --- Text cleaner ---
def clean_text(text):
    text = text.lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"\d{1,4}[-:/]\d{1,2}[-:/]\d{1,4}", " ", text)
    text = re.sub(r"\d{1,2}:\d{2}", " ", text)
    text = re.sub(r"\+?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,4}", " ", text)
    text = re.sub(r"\b\d{1,4}\b", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r'(.)\1{3,}', ' ', text)
    return text

# --- Reverse match for French fallback ---
manual_translations = {
    "click": "cliquer",
    "account": "compte",
    "password": "mot de passe",
    "login": "connexion",
    "email": "courriel"
}

def fuzzy_reverse_lookup(word_en, original_text_fr):
    try:
        # Use manual override first
        if word_en.lower() in manual_translations:
            return manual_translations[word_en.lower()]

        candidates = original_text_fr.lower().split()
        word_fr_guess = GoogleTranslator(source='en', target='fr').translate(word_en).lower()
        match = get_close_matches(word_fr_guess, candidates, n=1, cutoff=0.6)
        return match[0] if match else word_fr_guess
    except:
        return word_en


# --- FastAPI setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request schema ---
class HtmlRequest(BaseModel):
    html: str

# --- Load models and vectorizer ---
model_paths = {
    "random_forest": "random_forest.pkl",
    "random_forest_tuned": "random_forest_tuned.pkl",
    "logistic_regression": "logistic_regression.pkl",
    "hist_gradient_boosting": "hist_gradient_boosting.pkl"
}

models = {}
for key, path in model_paths.items():
    if os.path.exists(path):
        models[key] = joblib.load(path)
    else:
        print(f"[⚠️] Model not found: {path}")

vectorizer = joblib.load("email_vectorizer.pkl")
feature_names = vectorizer.get_feature_names_out()

# --- SHAP background for TreeExplainer ---
shap_background_texts = [
    "dear customer your account has been suspended",
    "click here to verify your identity",
    "bank update required immediately",
    "this is a safe and verified email",
    "reset your password now",
    "thank you for your purchase",
    "please confirm your address"
]
shap_background = vectorizer.transform([clean_text(t) for t in shap_background_texts]).toarray()

@app.post("/analyze_html")
async def analyze_html(req: HtmlRequest):
    try:
        # --- Extract and preprocess text ---
        soup = BeautifulSoup(req.html, "html.parser")
        visible_text = soup.get_text(separator="\n").strip()
        print("\n[📝] Raw extracted text:\n", visible_text[:500])

        try:
            detected_lang = detect(visible_text)
        except Exception:
            detected_lang = "unknown"
        print(f"[🌐] Detected language: {detected_lang}")

        visible_text_fr = visible_text if detected_lang == "fr" else None

        text_en = GoogleTranslator(source='fr', target='en').translate(visible_text) if detected_lang == "fr" else visible_text
        cleaned = clean_text(text_en)
        X = vectorizer.transform([cleaned])
        X_dense = X.toarray()

        # --- Maturity Voting ---
        votes = []
        confidences = []
        for name, model in models.items():
            input_X = X_dense if name == "hist_gradient_boosting" else X
            proba = model.predict_proba(input_X)[0][1]
            confidences.append(proba)
            votes.append(proba >= 0.5)
        vote_sum = sum(votes)
        is_phishing = vote_sum >= (len(votes) / 2)
        avg_conf = np.mean(confidences)
        print(f"[🧠] Maturity voting: {vote_sum}/{len(votes)} voted phishing")

        # --- SHAP Aggregation ---
        total_shap = np.zeros(X_dense.shape[1])
        valid_explanations = 0

        for name, model in models.items():
            try:
                if "logistic" in name and hasattr(model, "named_steps"):
                    scaler = model.named_steps['standardscaler']
                    clf = model.named_steps['logisticregression']
                    X_scaled = scaler.transform(X_dense)
                    explainer = shap.LinearExplainer(clf, X_scaled, feature_perturbation="interventional")
                    shap_values = explainer(X_scaled)
                    shap_row = shap_values.values[0]
                else:
                    explainer = shap.TreeExplainer(model, data=shap_background, feature_perturbation="interventional")
                    shap_values = explainer.shap_values(X_dense, check_additivity=False)

                    if isinstance(shap_values, list):
                        shap_row = shap_values[1][0]  # Class 1 (phishing)
                    elif shap_values.ndim == 3:
                        shap_row = shap_values[0, :, 1]
                    else:
                        shap_row = shap_values[0]

                print(f"[🔍] SHAP shape for {name}: {shap_row.shape}, sum={np.sum(np.abs(shap_row)):.6f}")

                if shap_row.shape[0] == X_dense.shape[1]:
                    total_shap += shap_row
                    valid_explanations += 1
                else:
                    print(f"[⚠️] Skipping SHAP for {name}: shape mismatch {shap_row.shape}")

            except Exception as e:
                print(f"[⚠️] SHAP failed for model {name}: {e}")

        explanation = []
        if valid_explanations > 0:
            aggregated_shap = total_shap / valid_explanations
            nonzero_indices = X_dense[0].nonzero()[0]

            if len(nonzero_indices) == 0:
                explanation = [{"word": "[no meaningful words]", "impact": 0.0}]
                print("[⚠️] No non-zero TF-IDF features.")
            else:
                top_indices = sorted(nonzero_indices, key=lambda i: abs(aggregated_shap[i]), reverse=True)[:10]

                print("\n[🔎] Aggregated SHAP contributions (top 10):")
                for i in top_indices:
                    word_en = feature_names[i]
                    impact = float(aggregated_shap[i])
                    if detected_lang == "fr" and visible_text_fr:
                        word = fuzzy_reverse_lookup(word_en, visible_text_fr)
                    else:
                        word = word_en
                    explanation.append({"word": word, "impact": round(impact, 4)})
                    print(f"   - {word_en:>15} → {word:>15}: {impact:+.4f}")

                try:
                    plt.figure(figsize=(8, 4))
                    bar_words = [feature_names[i] for i in top_indices][::-1]
                    bar_impacts = [aggregated_shap[i] for i in top_indices][::-1]
                    bar_colors = ['red' if v > 0 else 'green' for v in bar_impacts]

                    plt.barh(bar_words, bar_impacts, color=bar_colors)
                    plt.xlabel("SHAP Impact")
                    plt.title("Top SHAP Features (Maturity Voting)")
                    plt.tight_layout()
                    plt.savefig("shap_explanation.png")
                    plt.close()
                    print("[📈] Aggregated SHAP plot saved to shap_explanation.png")
                except Exception as plot_err:
                    print("[⚠️] Could not generate SHAP plot:", plot_err)

        return {
            "is_phishing": bool(is_phishing),
            "confidence": round(float(avg_conf), 4),
            "language": detected_lang,
            "explanation": explanation
        }

    except Exception as e:
        print("[❌] Exception during analysis:", e)
        return {"error": str(e)}