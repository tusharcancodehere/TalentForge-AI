from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend.core.github_engine import (
    get_http_client,
    get_portfolio_payload,
    get_cv_payload,
)
from backend.core.grit_logic import (
    build_career_architect_payload,
)
from backend.agents.architect_agent import (
    generate_market_insights,
    generate_career_architect,
    chat_with_coach_agent,
)
from backend.utils.pdf_gen import build_resume_pdf, build_simple_pdf
from backend.utils.redis_client import redis_client


router = APIRouter(prefix="/api")


RATE_LIMIT_REQUESTS: int = 30
RATE_LIMIT_WINDOW: int = 60
_rate_limit_store: dict[str, list[float]] = {}


async def track_and_rate_limit(request: Request) -> None:
    import time

    client_host: str = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW
    timestamps = _rate_limit_store.get(client_host, [])
    timestamps = [t for t in timestamps if t > window_start]
    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )
    timestamps.append(now)
    _rate_limit_store[client_host] = timestamps


@router.get("/portfolio/{username}")
async def get_portfolio(
    username: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=6, ge=1, le=12),
    _: None = Depends(track_and_rate_limit),
) -> dict[str, Any]:
    http_client = get_http_client()
    try:
        return await get_portfolio_payload(http_client=http_client, username=username, page=page, page_size=page_size)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to reach GitHub API.") from exc


@router.get("/architect/{username}")
async def get_career_architect(
    username: str,
    _: None = Depends(track_and_rate_limit),
) -> dict[str, Any]:
    http_client = get_http_client()
    try:
        base_payload = await build_career_architect_payload(http_client=http_client, username=username)
        analysis = await generate_career_architect(
            profile=base_payload["profile"],
            repos=base_payload["analysis_repos"],
            tech_stack=base_payload["tech_stack"],
            grit_meta=base_payload["grit_meta"],
        )
        return {
            **analysis,
            "user": base_payload["user"],
            "projects": base_payload["projects"],
            "tech_stack": base_payload["tech_stack"],
            "pagination": base_payload["pagination"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to reach GitHub API.") from exc


from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class CoachChatRequest(BaseModel):
    architect_data: dict[str, Any]
    message: str
    history: list[ChatMessage] = []


@router.post("/coach/chat")
async def chat_with_coach(request: CoachChatRequest, _: None = Depends(track_and_rate_limit)) -> dict[str, Any]:
    response_text = await chat_with_coach_agent(request.architect_data, request.message, request.history)
    return {"response": response_text}


class PDFExportRequest(BaseModel):
    username: str
    resume_html: str
    architect_classification: str


@router.post("/cv/export")
async def export_cv(req: PDFExportRequest, _: None = Depends(track_and_rate_limit)) -> StreamingResponse:
    import re
    import html
    import io

    text_content = re.sub(r"<[^>]+>", "", req.resume_html)
    text_content = html.unescape(text_content).strip()
    pdf_bytes = build_simple_pdf(
        username=req.username,
        classification=req.architect_classification,
        text_content=text_content,
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{req.username}_resume.pdf"'},
    )


@router.get("/cv/{username}")
async def get_cv(username: str, _: None = Depends(track_and_rate_limit)) -> StreamingResponse:
    import io

    http_client = get_http_client()
    payload = await get_cv_payload(http_client=http_client, username=username)
    pdf_bytes = build_resume_pdf(portfolio=payload, username=username)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{username}_resume.pdf"'},
    )


@router.get("/stats")
async def get_stats() -> dict[str, int]:
    # Placeholder: Stats tracking moved to Redis or external service.
    # Keeping schema for compatibility.
    return {"active": 0, "total": 0}

