"""
VisualEye FastAPI backend.

Serves the frontend HTML and exposes /analyze endpoint that:
1. Accepts a base64 image, language, and analysis mode
2. Calls Gemma 3 27B via Google's Gemini API for vision understanding
3. Converts the response to speech via gTTS
4. Returns description + audio to the browser
"""

import os
import time
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from utils.gemma import analyze_image, MODEL_ID  # noqa: E402
from utils.tts import text_to_speech_base64, get_supported_languages  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VisualEye API",
    description="AI-powered visual accessibility assistant using Gemma 4 26B MoE via Gemini API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory history — last 5 analyses (per-process, resets on restart)
_history: list[dict] = []
MAX_HISTORY = 5

FRONTEND_PATH = Path(__file__).parent / "frontend" / "index.html"

VALID_MODES = {"describe", "read_text", "hazard", "people"}
VALID_LANGUAGES = {"en", "hi", "ta", "te", "kn", "bn"}


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded JPEG image")
    language: str = Field("en", description="Language code for TTS output")
    mode: str = Field("describe", description="Analysis mode")


class AnalyzeResponse(BaseModel):
    description: str
    audio_base64: str
    model_used: str
    processing_time_ms: int
    error: str | None = None


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the VisualEye frontend."""
    if not FRONTEND_PATH.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return HTMLResponse(content=FRONTEND_PATH.read_text(encoding="utf-8"))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    api_key_set = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "ok",
        "model": MODEL_ID,
        "api_key_configured": api_key_set,
        "languages": get_supported_languages(),
    }


@app.get("/history")
async def get_history():
    """Return last 5 analysis results (descriptions only, no images for privacy)."""
    return {"history": _history}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Analyze an image using Gemma 4 and return description + audio.
    """
    # Validate inputs
    if not request.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    mode = request.mode if request.mode in VALID_MODES else "describe"
    language = request.language if request.language in VALID_LANGUAGES else "en"

    # Strip data URI prefix if the frontend included it
    image_b64 = request.image_base64
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    start_ms = time.time()

    logger.info("Analyzing image — mode=%s lang=%s", mode, language)

    # Step 1: Vision analysis with Gemma 4 via Gemini API
    gemma_result = analyze_image(
        image_base64=image_b64,
        mode=mode,
        language_code=language,
    )

    if gemma_result["error"]:
        elapsed = int((time.time() - start_ms) * 1000)
        return AnalyzeResponse(
            description="",
            audio_base64="",
            model_used=MODEL_ID,
            processing_time_ms=elapsed,
            error=gemma_result["error"],
        )

    description = gemma_result["description"]

    # Step 2: Text-to-speech
    tts_result = text_to_speech_base64(description, language)

    elapsed = int((time.time() - start_ms) * 1000)
    logger.info("Analysis complete in %dms", elapsed)

    # Update in-memory history (keep last MAX_HISTORY entries)
    _history.append(
        {
            "description": description,
            "mode": mode,
            "language": language,
            "processing_time_ms": elapsed,
        }
    )
    if len(_history) > MAX_HISTORY:
        _history.pop(0)

    return AnalyzeResponse(
        description=description,
        audio_base64=tts_result.get("audio_base64", ""),
        model_used=MODEL_ID,
        processing_time_ms=elapsed,
        error=tts_result.get("error"),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
