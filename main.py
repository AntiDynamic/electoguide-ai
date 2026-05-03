"""
ElectoGuide AI — Main FastAPI Application
==========================================
Google Cloud Services integrated:
  • Gemini 1.5 Flash      — AI chat, quiz, fact-check, country info
  • Cloud Firestore        — Persistent chat sessions
  • Cloud Translation API  — Multi-language support
  • Cloud Natural Language — Entity extraction for context enrichment
  • Cloud Text-to-Speech   — Voice narration (+ browser fallback)
  • Cloud Logging          — Structured request telemetry
  • Cloud Run              — Deployment target
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from routes import chat, countries, factcheck, quiz, sessions, translate, tts

# ── Bootstrap ─────────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(name)-28s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🗳️  ElectoGuide AI starting up")
    logger.info("   Model    : %s", os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    logger.info("   Project  : %s", os.getenv("GCP_PROJECT_ID", "promptwars-495214"))
    logger.info("   Env      : %s", os.getenv("ENVIRONMENT", "production"))

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("⚠️  GEMINI_API_KEY not configured properly!")
    else:
        logger.info("✅ Gemini API key loaded")
    yield
    logger.info("👋 ElectoGuide AI shutting down")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ElectoGuide AI",
    description=(
        "AI-powered Election Process Education Assistant — "
        "powered by Google Gemini 1.5 Flash, Cloud Firestore, "
        "Cloud Translation, Cloud NL API, and Cloud Run."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    max_age=600,
)

# ── Static & Templates ────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(chat.router,      prefix="/api", tags=["Chat"])
app.include_router(sessions.router,  prefix="/api", tags=["Sessions"])
app.include_router(translate.router, prefix="/api", tags=["Translation"])
app.include_router(quiz.router,      prefix="/api", tags=["Quiz"])
app.include_router(factcheck.router, prefix="/api", tags=["Fact Check"])
app.include_router(tts.router,       prefix="/api", tags=["Text-to-Speech"])
app.include_router(countries.router, prefix="/api", tags=["Countries"])


# ── Core Routes ───────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request) -> HTMLResponse:
    """Serve the Single Page Application."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health", tags=["System"])
async def health_check() -> JSONResponse:
    """Health check for Cloud Run liveness probe."""
    return JSONResponse(content={
        "status": "healthy",
        "service": "ElectoGuide AI",
        "version": "2.0.0",
        "model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        "project": os.getenv("GCP_PROJECT_ID", "promptwars-495214"),
    })


@app.get("/api/config", tags=["System"])
async def get_config() -> JSONResponse:
    """Return safe (non-secret) app configuration for the frontend."""
    return JSONResponse(content={
        "version": "2.0.0",
        "model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        "tts_available": True,   # Browser TTS always available
        "project_id": os.getenv("GCP_PROJECT_ID", "promptwars-495214"),
    })


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
    )
