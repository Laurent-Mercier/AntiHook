import joblib
import shap
import numpy as np
import matplotlib.pyplot as plt
import re
from langdetect import detect
from deep_translator import GoogleTranslator

# --- Load model and vectorizer ---
model = joblib.load("email_model.pkl")
vectorizer = joblib.load("email_vectorizer.pkl")
feature_names = vectorizer.get_feature_names_out()
explainer = shap.TreeExplainer(model, feature_perturbation="interventional")

# --- Text cleaning ---
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

# --- Ask for input ---
raw_text = input("Paste your email text:\n\n")
try:
    detected_lang = detect(raw_text)
except:
    detected_lang = "unknown"

if detected_lang == "fr":
    translated_text = GoogleTranslator(source='fr', target='en').translate(raw_text)
else:
    translated_text = raw_text

cleaned = clean_text(translated_text)
X = vectorizer.transform([cleaned])
X_dense = X.toarray()

# --- Predict ---
proba = model.predict_proba(X_dense)[0][1]
is_phishing = proba >= 0.5
label = "Phishing" if is_phishing else "Legitimate"

print(f"\n[📨] Prediction: {label}")
print(f"[🔒] Confidence: {proba:.4f}")
print(f"[🌐] Language:   {detected_lang}")

# --- SHAP explanation ---
shap_values = explainer.shap_values(X_dense, check_additivity=False)
if isinstance(shap_values, list) and len(shap_values) > 1:
    shap_row = shap_values[1][0]
elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
    shap_row = shap_values[0, :, 1]
else:
    shap_row = shap_values[0]

nonzero_indices = X_dense[0].nonzero()[0]
if len(nonzero_indices) == 0:
    print("\n[⚠️] No meaningful tokens found.")
else:
    max_val = max(abs(val) for val in shap_row) or 1.0
    normalized = shap_row / max_val

    ranked = sorted(nonzero_indices, key=lambda i: abs(normalized[i]), reverse=True)

    print("\n[🔍] Top SHAP words in input:")
    for i in ranked[:10]:
        word = feature_names[i]
        impact = float(normalized[i])
        print(f"   - {word:>15}: {impact:+.4f}")

    # --- Save bar plot ---
    try:
        plt.figure(figsize=(8, 4))
        bar_words = [feature_names[i] for i in ranked[:10]]
        bar_impacts = [normalized[i] for i in ranked[:10]]
        plt.barh(bar_words[::-1], bar_impacts[::-1], color="red")
        plt.xlabel("Normalized SHAP Impact")
        plt.title("Top SHAP Features (Phishing Explanation)")
        plt.tight_layout()
        plt.savefig("shap_explanation.png")
        plt.close()
        print("[📈] SHAP plot saved to 'shap_explanation.png'")
    except Exception as e:
        print("[⚠️] Could not save SHAP plot:", e)