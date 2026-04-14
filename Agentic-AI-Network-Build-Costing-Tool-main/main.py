"""FTTP Network Cost Estimation & Optimization - FastAPI application."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pathlib import Path

from api.routes import router
from config import get_settings

app = FastAPI(
    title="FTTP Network Cost Estimator",
    description="Agentic AI FTTP Network Cost Estimation & Optimization",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["api"])

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/static/login.html")


@app.get("/login")
async def login_page():
    return RedirectResponse(url="/static/login.html")


@app.get("/signup")
async def signup_page():
    return RedirectResponse(url="/static/signup.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
