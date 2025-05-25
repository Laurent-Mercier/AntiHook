from fastapi import FastAPI
from pydantic import BaseModel
import base64
import io
from PIL import Image
import pytesseract
import joblib  # <-- use joblib here
from fastapi.middleware.cors import CORSMiddleware

# Load model and vectorizer saved with joblib
model = joblib.load("phishing_model.pkl")
vectorizer = joblib.load("vectorizer.pkl")

app = FastAPI()

class ImageRequest(BaseModel):
    image: str  # base64 image string from browser extension

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["moz-extension://<your-id>"] for stricter control
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/predict")
async def predict(req: ImageRequest):
    try:
        # Strip any header like "data:image/png;base64,"
        _, _, base64_data = req.image.partition(',')
        image_data = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_data))

        # Extract text with OCR
        extracted_text = pytesseract.image_to_string(image)

        # Vectorize and predict
        X = vectorizer.transform([extracted_text])
        prediction = model.predict(X)[0]

        return {
            "is_phishing": bool(prediction),
            "extracted_text": extracted_text[:500]  # optional preview
        }

    except Exception as e:
        return {"error": str(e)}