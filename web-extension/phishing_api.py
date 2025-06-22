from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from deep_translator import GoogleTranslator
from langdetect import detect
from bs4 import BeautifulSoup
import joblib
import shap
import numpy as np
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
    # Remove any long runs of the same character (e.g. _____ or 3d3d3d3d)
    text = re.sub(r'(.)\1{3,}', ' ', text)
    return text

# Request model
class HtmlRequest(BaseModel):
    html: str

# Load phishing model and vectorizer
model = joblib.load("email_model.pkl")
vectorizer = joblib.load("email_vectorizer.pkl")
feature_names = vectorizer.get_feature_names_out()

# Ensure input to explainer is dense
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
        # Extract visible text
        soup = BeautifulSoup(req.html, "html.parser")
        visible_text = soup.get_text(separator="\n").strip()
        print("\n[📝] Raw extracted text:\n", visible_text[:500], "\n")

        # Language detection
        try:
            detected_lang = detect(visible_text)
        except Exception:
            detected_lang = "unknown"
        print(f"[🌐] Detected language: {detected_lang}")

        # Translate to English if needed
        if detected_lang == "fr":
            translated_text = GoogleTranslator(source='fr', target='en').translate(visible_text)
        else:
            translated_text = visible_text

        # Vectorize input
        cleaned = clean_text(translated_text)
        X = vectorizer.transform([cleaned])
        if scipy.sparse.issparse(X):
            X_dense = X.toarray()
        else:
            X_dense = X

        # Predict
        prediction = model.predict(X_dense)[0]
        proba = model.predict_proba(X_dense)[0][1]
        is_phishing = bool(proba >= 0.5)

        # --- SHAP Explanation ---
        # Convert sparse matrix to dense
        X_dense = X.toarray()

        # Compute SHAP values
        shap_values = explainer.shap_values(X_dense, check_additivity=False)
        # If shap_values is a list (multi-class), get phishing class (usually 1)
        if isinstance(shap_values, list):
            shap_scores = shap_values[1][0]  # Class 1, first sample
        else:
            shap_scores = shap_values[0]     # Single class model


        # Handle shape depending on binary vs multiclass
        if shap_scores.ndim == 3:
            shap_scores = shap_scores[0]  # binary/multiclass: select phishing class
        elif shap_scores.ndim == 1:
            shap_scores = shap_scores.reshape(1, -1)

        shap_row = shap_scores[0]  # First (and only) sample
        top_indices = np.argsort(np.abs(shap_row))[-5:][::-1]

        explanation = []
        print(f"[🔎] Top SHAP explanations (impact on phishing score):")
        for i in top_indices:
            word = feature_names[i]
            impact = float(shap_row[i])  # ensure Python float
            explanation.append({"word": word, "impact": round(impact, 4)})
            print(f"   - {word:>15}: {impact:+.4f}")



        return {
            "is_phishing": is_phishing,
            "confidence": round(float(proba), 4),
            "language": detected_lang,
            "explanation": explanation
        }

    except Exception as e:
        print("[❌] Exception during analysis:", e)
        return {"error": str(e)}