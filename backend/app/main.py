"""FastAPI 진입점 (Design 1, 4)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import analyze, editing, projects, subtitle

app = FastAPI(title="CapCut Auto Editor", version="0.1.0")

# 로컬 프론트엔드(Vite) 개발 서버 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(analyze.router)
app.include_router(subtitle.router)
app.include_router(editing.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
