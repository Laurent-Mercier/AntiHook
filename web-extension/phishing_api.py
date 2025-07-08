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
import scipy

def clean_text(text):
    text = text.lower()
    text = re.sub(r"http\S+", " ", text)  # URLs
    text = re.sub(r"\d{1,4}[-:/]\d{1,2}[-:/]\d{1,4}", " ", text)  # Dates
    text = re.sub(r"\d{1,2}:\d{2}", " ", text)  # Times
    text = re.sub(r"\+?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,4}", " ", text)  # Phone numbers
    text = re.sub(r"\b\d{1,4}\b", " ", text)  # Short numbers
    text = re.sub(r"[^\w\s]", " ", text)  # Punctuation
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r'(.)\1{3,}', ' ', text)  # Long character repetitions
    return text

# Request model
class HtmlRequest(BaseModel):
    html: str

# Load phishing model and vectorizer
model = joblib.load("email_model.pkl")
vectorizer = joblib.load("email_vectorizer.pkl")
feature_names = vectorizer.get_feature_names_out()

# SHAP TreeExplainer
explainer = shap.TreeExplainer(model, feature_perturbation="interventional")

# Initialize FastAPI
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze_html")
async def analyze_html(req: HtmlRequest):
    try:
        # --- Extract text ---
        soup = BeautifulSoup(req.html, "html.parser")
        visible_text = soup.get_text(separator="\n").strip()
        print("\n[📝] Raw extracted text:\n", visible_text[:500], "\n")

        # --- Detect language ---
        try:
            detected_lang = detect(visible_text)
        except Exception:
            detected_lang = "unknown"
        print(f"[🌐] Detected language: {detected_lang}")

        # --- Translate to English if needed ---
        if detected_lang == "fr":
            translated_text = GoogleTranslator(source='fr', target='en').translate(visible_text)
        else:
            translated_text = visible_text

        # --- Clean and vectorize ---
        cleaned = clean_text(translated_text)
        X = vectorizer.transform([cleaned])
        X_dense = X.toarray()

        # --- Predict ---
        prediction = model.predict(X_dense)[0]
        proba = model.predict_proba(X_dense)[0][1]
        is_phishing = bool(proba >= 0.5)

        # --- SHAP explanation ---
        shap_values = explainer.shap_values(X_dense, check_additivity=False)

        # Shape: (1, num_features, 2) or (1, num_features)
        if isinstance(shap_values, list) and len(shap_values) > 1:
            shap_row = shap_values[1][0]
        elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
            shap_row = shap_values[0, :, 1]
        else:
            shap_row = shap_values[0]  # single class fallback

        # --- Normalize SHAP values ---
        max_val = max(abs(val) for val in shap_row) if np.any(shap_row) else 1.0
        normalized_shap_row = shap_row / max_val

        # --- Extract nonzero TF-IDF features ---
        nonzero_indices = X_dense[0].nonzero()[0]
        if len(nonzero_indices) == 0:
            explanation = [{"word": "[no meaningful words]", "impact": 0.0}]
            print("[⚠️] No non-zero TF-IDF features.")
        else:
            # Rank and print full explanation
            ranked = sorted(nonzero_indices, key=lambda i: abs(normalized_shap_row[i]), reverse=True)
            explanation = []
            print("\n[🔎] All SHAP contributions (words in input):")
            for i in ranked:
                word = feature_names[i]
                impact = float(normalized_shap_row[i])
                explanation.append({"word": word, "impact": round(impact, 4)})
                print(f"   - {word:>15}: {impact:+.4f}")

            # --- Save SHAP bar plot instead ---
            try:
                plt.figure(figsize=(8, 4))
                bar_words = [feature_names[i] for i in ranked[:10]]
                bar_impacts = [normalized_shap_row[i] for i in ranked[:10]]
                plt.barh(bar_words[::-1], bar_impacts[::-1], color="red")
                plt.xlabel("Normalized SHAP Impact")
                plt.title("Top SHAP Features (Phishing Explanation)")
                plt.tight_layout()
                plt.savefig("shap_explanation.png")
                plt.close()
                print("[📈] SHAP bar plot saved to shap_explanation.png")
            except Exception as plot_err:
                print("[⚠️] Could not generate SHAP plot:", plot_err)


        return {
            "is_phishing": is_phishing,
            "confidence": float(proba),
            "language": detected_lang,
            "explanation": explanation
        }

    except Exception as e:
        print("[❌] Exception during analysis:", e)
        return {"error": str(e)}