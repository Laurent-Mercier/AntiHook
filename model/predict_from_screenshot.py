import pytesseract
from PIL import Image
import joblib
import re

# --- Load trained model and vectorizer ---
model = joblib.load("phishing_model.pkl")
vectorizer = joblib.load("vectorizer.pkl")

# --- Load and OCR the screenshot ---
image_path = "email_screenshot.jpg"
img = Image.open(image_path)
ocr_text = pytesseract.image_to_string(img)

print("\n--- Extracted OCR Text ---")
print(ocr_text[:1000])  # Show a snippet for inspection

# --- Optionally: extract fields (Subject, From, Body) if formatted ---
subject = re.search(r'Subject:\s*(.*)', ocr_text, re.IGNORECASE)
sender = re.search(r'From:\s*(.*)', ocr_text, re.IGNORECASE)

subject = subject.group(1).strip() if subject else ""
sender = sender.group(1).strip() if sender else ""
body = ocr_text.replace(subject, "").replace(sender, "")

# Combine fields for prediction
email_text = subject + " " + sender + " " + body

# --- Vectorize and predict ---
X_input = vectorizer.transform([email_text])
prediction = model.predict(X_input)[0]
proba = model.predict_proba(X_input)[0]

# --- Display result ---
print("\n--- Prediction ---")
print("⚠️  Phishing Email" if prediction == 1 else "✅ Legitimate Email")
print(f"Confidence: Phishing={proba[1]:.2%}, Legit={proba[0]:.2%}")