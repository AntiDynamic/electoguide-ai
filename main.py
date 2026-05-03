"""
ElectoGuide AI — Main FastAPI Application
==========================================
AI-powered Election Process Education Assistant
Deployed on Google Cloud Run
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from routes import chat, quiz, factcheck, tts, countries

# ── Bootstrap ────────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🗳️  ElectoGuide AI starting up — ready to educate!")
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("⚠️  GEMINI_API_KEY not configured properly!")
    else:
        logger.info("✅ Gemini API key loaded successfully")
    yield
    logger.info("👋 ElectoGuide AI shutting down")


# ── App Factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="ElectoGuide AI",
    description=(
        "An AI-powered Election Process Education Assistant that helps citizens "
        "understand election processes, timelines, and civic participation worldwide."
    ),
    version="1.0.0",
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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    max_age=600,
)

# ── Static & Templates ────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(chat.router,        prefix="/api", tags=["Chat"])
app.include_router(quiz.router,        prefix="/api", tags=["Quiz"])
app.include_router(factcheck.router,   prefix="/api", tags=["Fact Check"])
app.include_router(tts.router,         prefix="/api", tags=["Text-to-Speech"])
app.include_router(countries.router,   prefix="/api", tags=["Countries"])


# ── Core Routes ───────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request) -> HTMLResponse:
    """Serve the main Single Page Application."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health", tags=["System"])
async def health_check() -> JSONResponse:
    """Health check endpoint for Cloud Run."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "ElectoGuide AI",
            "version": "1.0.0",
            "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite"),
        }
    )


@app.get("/api/config", tags=["System"])
async def get_config() -> JSONResponse:
    """Return safe, non-secret app configuration for the frontend."""
    return JSONResponse(
        content={
            "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite"),
            "tts_enabled": True,  # Browser TTS is always available
            "version": "1.0.0",
        }
    )


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT", "production") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
    )
