# Library imports
from fastapi import FastAPI
from pydantic import BaseModel
import base64
import io
from PIL import Image
import pytesseract
import joblib
import re
from fastapi.middleware.cors import CORSMiddleware

# Words picked up by OCR in Outlook that are not relevant.
OUTLOOK_NOISE = [
    "Inbox", "Sent Items", "Drafts", "Junk Email", "Archive", "Reply", "Replyall",
    "Forward", "Deleted Items", "RSS Feeds", "Ad-Free Outlook", "Sweep", "Help",
    "Move to", "Favorites", "View", "Translate", "sign up", "Go to Groups", "Home",
    "Conversation History", "Rejoindre", "Read / Unread", "To:", "From:", "Subject:",
    "|", "-", "—", "ad blocker"
]


# Text processing after OCR.
def extract_email_body(text: str) -> str:
    lines = text.splitlines()
    content_lines = []

    for line in lines:
        line_clean = line.strip()

        # Skip empty lines or lines that are mostly symbols/short
        if not line_clean:
            continue
        if len(re.sub(r'[^a-zA-Z0-9]', '', line_clean)) < 4:
            continue
        if any(noise.lower() in line_clean.lower() for noise in OUTLOOK_NOISE):
            continue

        content_lines.append(line_clean)

    # Combine filtered lines.
    full_cleaned = '\n'.join(content_lines)

    # Extract longest coherent paragraph block as body.
    paragraphs = full_cleaned.split('\n\n')
    paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 50]

    if paragraphs:
        return max(paragraphs, key=len)
    else:
        return full_cleaned.strip()


# Load model and vectorizer
model = joblib.load("phishing_model_combined.pkl")
vectorizer = joblib.load("vectorizer_combined.pkl")

# Initialize FastAPI
app = FastAPI()

# Class for the image to analyze, has an attribute image which is a base64 string of the image.
class ImageRequest(BaseModel):
    image: str 

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Predict route, determines if the email is phishing or not.
@app.post("/predict")
async def predict(req: ImageRequest):
    try:
        # Strips any header like "data:image/png;base64,"
        _, _, base64_data = req.image.partition(',')
        image_data = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_data))

        # OCR.
        full_text = pytesseract.image_to_string(image)
        print("\n--- OCR Full Extracted Text ---\n")
        print(full_text[:1000])

        # Extract email body.
        cleaned_text = extract_email_body(full_text)
        print("\n--- Extracted Email Body (Filtered) ---\n")
        print(cleaned_text[:1000])

        # Predict
        X = vectorizer.transform([cleaned_text])
        prediction = model.predict(X)[0]
        proba = model.predict_proba(X)[0][1]  # confidence it's phishing

        # Print confidence.
        print(f"\n--- Prediction: {'Phishing' if prediction else 'Safe'} (Confidence: {proba:.4f}) ---\n")

        return {
            "is_phishing": bool(proba > 0.8),
            "confidence": round(proba, 4),
        }

    except Exception as e:
        return {"error": str(e)}
