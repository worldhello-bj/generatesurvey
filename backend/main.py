import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routers import admin_router, download_router, generate_router, questionnaire_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Survey Data Generator",
    version="1.0.0",
    description="Generate synthetic survey data using AI models",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questionnaire_router, prefix="/questionnaire", tags=["questionnaire"])
app.include_router(generate_router, prefix="/generate", tags=["generate"])
app.include_router(download_router, prefix="/download", tags=["download"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])


@app.on_event("startup")
async def on_startup():
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:
        logger.warning("DB init failed (may not be available): %s", exc)


@app.get("/health")
async def health():
    return {"status": "ok"}
