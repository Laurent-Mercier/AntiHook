# Library imports
from fastapi import FastAPI
from pydantic import BaseModel
import base64
import io
from PIL import Image
import pytesseract
import joblib
from fastapi.middleware.cors import CORSMiddleware

# Load model and vectorizer
model = joblib.load("phishing_model.pkl")
vectorizer = joblib.load("vectorizer.pkl")

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
        # Strips any header like "data:image/png;base64,".
        _, _, base64_data = req.image.partition(',')
        image_data = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_data))

        # Extracts text with OCR.
        extracted_text = pytesseract.image_to_string(image)

        # Vectorizes and predicts.
        X = vectorizer.transform([extracted_text])
        prediction = model.predict(X)[0]

        return {
            "is_phishing": bool(prediction),
            #"extracted_text": extracted_text[:500]  # optional preview
        }

    except Exception as e:
        return {"error": str(e)}