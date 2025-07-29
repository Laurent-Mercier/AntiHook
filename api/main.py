# api/main.py

from fastapi import FastAPI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.analyze import router as analyze_router

app = FastAPI(
    title="AntiHook Phishing Analysis API",
    description="Analyze emails (text+links) for phishing risk",
    version="1.0.0"
)

# Allow CORS from anywhere.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the analyze endpoint.
app.include_router(analyze_router, prefix="", tags=["analysis"])