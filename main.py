"""
RAG Document Assistant — FastAPI Application Entry Point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.connection import init_db
from api.routes import router

app = FastAPI(
    title="RAG Document Assistant",
    description="Intelligent document assistant with page-level retrieval using BM25, snippet extraction, and grounded reasoning.",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(router)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()


@app.get("/")
async def root():
    return {
        "name": "RAG Document Assistant",
        "version": "1.0.0",
        "docs": "/docs",
    }
