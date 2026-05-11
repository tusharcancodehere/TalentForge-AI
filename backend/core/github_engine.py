from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException

GITHUB_API_BASE: str = "https://api.github.com"
GITHUB_TIMEOUT_SECONDS: float = 10.0
TOP_PORTFOLIO_PROJECTS: int = 6
TOP_CV_PROJECTS: int = 8
MAX_PORTFOLIO_PAGE_SIZE: int = 12


async def _check_github_rate_limit(response: httpx.Response) -> None:
    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining is not None and int(remaining) < 5:
        # Logging kept minimal here; callers can attach loggers if needed.
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    github_token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {github_token}"} if github_token else {}
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(GITHUB_TIMEOUT_SECONDS),
        headers=headers,
    )
    yield
    await app.state.http_client.aclose()


def get_http_client() -> httpx.AsyncClient:
    # This assumes FastAPI app has attached the client on state in lifespan.
    from backend.main import app  # type: ignore

    return app.state.http_client


async def fetch_github_profile(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    response = await client.get(f"{GITHUB_API_BASE}/users/{username}")
    await _check_github_rate_limit(response)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub user not found.")
    if response.status_code == 403:
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded. Try again later.")
    response.raise_for_status()
    return response.json()


async def fetch_github_repos(client: httpx.AsyncClient, username: str) -> list[dict[str, Any]]:
    response = await client.get(
        f"{GITHUB_API_BASE}/users/{username}/repos",
        params={"sort": "stargazers", "per_page": 50},
    )
    await _check_github_rate_limit(response)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub user not found.")
    if response.status_code == 403:
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded. Try again later.")
    response.raise_for_status()
    return response.json()


async def fetch_repo_readme(client: httpx.AsyncClient, username: str, repo_name: str) -> str | None:
    try:
        response = await client.get(f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/readme")
        if response.status_code != 200:
            return None
        content_b64: str = response.json().get("content", "")
        import base64

        return base64.b64decode(content_b64).decode("utf-8", errors="ignore")
    except Exception:
        return None


async def fetch_user_events(client: httpx.AsyncClient, username: str) -> list[dict[str, Any]]:
    try:
        response = await client.get(
            f"{GITHUB_API_BASE}/users/{username}/events/public",
            params={"per_page": 100},
        )
        return response.json() if response.status_code == 200 else []
    except Exception:
        return []


def extract_tech_stack(repos: list[dict[str, Any]]) -> list[str]:
    return sorted({
        repo["language"]
        for repo in repos
        if isinstance(repo.get("language"), str) and repo.get("language")
    })


def filter_original_repos(repos: list[dict[str, Any]], username: str) -> list[dict[str, Any]]:
    return [
        r for r in repos
        if not r.get("fork") and str(r.get("name", "")).lower() != username.lower()
    ]


def rank_top_original_repos(
    repos: list[dict[str, Any]], username: str, limit: int = TOP_PORTFOLIO_PROJECTS
) -> list[dict[str, Any]]:
    filtered = filter_original_repos(repos, username)
    return sorted(filtered, key=lambda r: int(r.get("stargazers_count", 0)), reverse=True)[:limit]


async def get_portfolio_payload(
    http_client: httpx.AsyncClient, username: str, page: int = 1, page_size: int = TOP_PORTFOLIO_PROJECTS
) -> dict[str, Any]:
    from backend.agents.architect_agent import build_projects_with_ai, generate_market_insights

    profile, repos = await asyncio.gather(
        fetch_github_profile(http_client, username),
        fetch_github_repos(http_client, username),
    )

    all_original_repos = rank_top_original_repos(repos, username, limit=10_000)
    total_projects = len(all_original_repos)
    start_idx = (page - 1) * page_size
    paginated_repos = all_original_repos[start_idx : start_idx + page_size]
    tech_stack = extract_tech_stack(repos)

    projects, market_insights = await asyncio.gather(
        build_projects_with_ai(http_client, username, paginated_repos),
        generate_market_insights(profile=profile, repos=all_original_repos, tech_stack=tech_stack),
    )

    total_pages = max(1, (total_projects + page_size - 1) // page_size)

    return {
        "user": {
            "name": profile.get("name") or profile.get("login"),
            "avatar_url": profile.get("avatar_url"),
            "bio": profile.get("bio"),
            "location": profile.get("location"),
            "github_url": profile.get("html_url"),
        },
        "projects": projects,
        "tech_stack": tech_stack,
        "market_insights": market_insights,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_projects": total_projects,
            "total_pages": total_pages,
        },
    }


import asyncio


async def get_cv_payload(http_client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    from backend.agents.architect_agent import build_projects_with_ai, generate_professional_summary

    profile, repos = await asyncio.gather(
        fetch_github_profile(http_client, username),
        fetch_github_repos(http_client, username),
    )

    top_repos_for_cv = rank_top_original_repos(repos, username, limit=TOP_CV_PROJECTS)
    tech_stack = extract_tech_stack(repos)

    cv_projects, professional_summary = await asyncio.gather(
        build_projects_with_ai(http_client, username, top_repos_for_cv, detailed=True),
        generate_professional_summary(
            user_name=profile.get("name") or profile.get("login"),
            bio=profile.get("bio"),
            project_titles=[r.get("name") for r in top_repos_for_cv],
            tech_stack=tech_stack,
        ),
    )

    return {
        "user": {
            "name": profile.get("name") or profile.get("login"),
            "avatar_url": profile.get("avatar_url"),
            "bio": profile.get("bio"),
            "location": profile.get("location"),
            "github_url": profile.get("html_url"),
        },
        "projects": cv_projects,
        "tech_stack": tech_stack,
        "professional_summary": professional_summary,
    }

import os
import base64
import logging
import httpx
from typing import Any
from fastapi import HTTPException

GITHUB_API_BASE: str = "https://api.github.com"
GITHUB_TIMEOUT_SECONDS: float = 10.0
TOP_PORTFOLIO_PROJECTS: int = 6
TOP_CV_PROJECTS: int = 8

logger = logging.getLogger("talentforge.github")

def _check_github_rate_limit(response: httpx.Response) -> None:
    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining is not None and int(remaining) < 5:
        reset_ts = response.headers.get("X-RateLimit-Reset", "unknown")
        logger.warning(f"GitHub rate limit almost exhausted! {remaining} remaining; resets at {reset_ts}.")

async def fetch_github_profile(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    response = await client.get(f"{GITHUB_API_BASE}/users/{username}")
    _check_github_rate_limit(response)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub user not found.")
    if response.status_code == 403:
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded.")
    response.raise_for_status()
    return response.json()

async def fetch_github_repos(client: httpx.AsyncClient, username: str) -> list[dict[str, Any]]:
    response = await client.get(f"{GITHUB_API_BASE}/users/{username}/repos", params={"sort": "stargazers", "per_page": 50})
    _check_github_rate_limit(response)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub user not found.")
    if response.status_code == 403:
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded.")
    response.raise_for_status()
    return response.json()

async def fetch_repo_readme(client: httpx.AsyncClient, username: str, repo_name: str) -> str | None:
    try:
        response = await client.get(f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/readme")
        if response.status_code != 200:
            return None
        content_b64: str = response.json().get("content", "")
        return base64.b64decode(content_b64).decode("utf-8", errors="ignore")
    except Exception:
        return None

async def fetch_user_events(client: httpx.AsyncClient, username: str) -> list[dict[str, Any]]:
    try:
        response = await client.get(f"{GITHUB_API_BASE}/users/{username}/events/public", params={"per_page": 100})
        return response.json() if response.status_code == 200 else []
    except Exception:
        return []

def extract_tech_stack(repos: list[dict[str, Any]]) -> list[str]:
    return sorted({repo["language"] for repo in repos if isinstance(repo.get("language"), str) and repo.get("language")})

def rank_top_original_repos(repos: list[dict[str, Any]], username: str, limit: int = TOP_PORTFOLIO_PROJECTS) -> list[dict[str, Any]]:
    filtered = [r for r in repos if not r.get("fork") and str(r.get("name", "")).lower() != username.lower()]
    return sorted(filtered, key=lambda r: int(r.get("stargazers_count", 0)), reverse=True)[:limit]
