from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router as api_router
from backend.core.github_engine import lifespan


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("talentforge")

ALLOWED_ORIGINS: list[str] = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

app = FastAPI(title="TalentForge AI Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(api_router)

_base_path = os.path.dirname(os.path.abspath(__file__))
_dist_path = os.path.join(_base_path, "dist")
_client_path = os.path.join(_dist_path, "client")
_frontend_dist = _client_path if os.path.isdir(_client_path) else _dist_path

if os.path.isdir(_frontend_dist):
    _assets_path = os.path.join(_frontend_dist, "assets")
    if os.path.isdir(_assets_path):
        app.mount("/assets", StaticFiles(directory=_assets_path), name="assets")

    @app.get("/{catchall:path}")
    async def serve_frontend(catchall: str):
        if catchall.startswith("api"):
            return JSONResponse(status_code=404, content={"detail": "API route not found"})

        _index_file = os.path.join(_frontend_dist, "index.html")
        if os.path.isfile(_index_file):
            return FileResponse(_index_file)
        return JSONResponse(status_code=404, content={"error": "Frontend index.html not found"})
else:

    @app.get("/{catchall:path}")
    async def _no_frontend(catchall: str):
        return JSONResponse(
            status_code=503,
            content={"error": "Frontend build not found. Ensure 'npm run build' completed."},
        )

