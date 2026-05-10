"""FastAPI backend for TalentForge AI — portfolio and CV generation."""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import math
import os
import re
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any

import google.generativeai as genai
from google.genai import types as genai_types
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("talentforge")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GITHUB_API_BASE: str = "https://api.github.com"
GEMINI_MODEL_NAME: str = "gemini-1.5-pro"
GITHUB_TIMEOUT_SECONDS: float = 10.0
GEMINI_TIMEOUT_SECONDS: float = 25.0  # hard timeout for every Gemini call
TOP_PORTFOLIO_PROJECTS: int = 6
TOP_CV_PROJECTS: int = 8
MAX_PORTFOLIO_PAGE_SIZE: int = 12

# Rate-limiting: per-IP sliding-window (no Redis required)
RATE_LIMIT_REQUESTS: int = 30   # max requests …
RATE_LIMIT_WINDOW: int = 60     # … per N seconds

# CORS — lock this down to your real frontend origin(s) in production.
# Keep "*" only while running locally; replace before going live.
ALLOWED_ORIGINS: list[str] = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

ROLE_STACKS: dict[str, list[str]] = {
    "Full Stack": ["React", "Node.js", "TypeScript", "SQL", "Docker", "AWS", "Redis"],
    "Backend": ["Python", "Go", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis"],
    "Frontend": ["React", "TypeScript", "TailwindCSS", "Next.js", "GraphQL", "Framer Motion"],
    "AI Engineer": ["Python", "PyTorch", "FastAPI", "Scikit-Learn", "Docker", "LangChain"],
    "DevOps": ["Terraform", "Docker", "Kubernetes", "AWS", "CI/CD", "Linux"],
    "Mobile": ["React Native", "Flutter", "Swift", "Kotlin", "Firebase"],
}

SKILL_WHY: dict[str, str] = {
    "Docker": "Industry-standard for containerization; required in 78% of backend/full-stack job postings.",
    "AWS": "Leading cloud platform; cloud fluency is a baseline expectation for mid-to-senior roles.",
    "Kubernetes": "Orchestration skill in high demand for scalable microservice architectures.",
    "Redis": "Essential for caching, real-time features, and high-throughput system design.",
    "TypeScript": "Dominant in modern frontend and full-stack roles; reduces production bugs significantly.",
    "SQL": "Foundational data skill; required across nearly all engineering disciplines.",
    "PostgreSQL": "Most popular open-source RDBMS; critical for backend and data-heavy applications.",
    "GraphQL": "Growing API standard for complex frontends; valued in product engineering teams.",
    "Next.js": "React meta-framework dominating full-stack and frontend hiring requirements.",
    "FastAPI": "Fastest-growing Python API framework; preferred for modern microservices.",
    "PyTorch": "Leading ML framework; essential for any AI/ML engineering position.",
    "LangChain": "Core framework for LLM-powered applications; highest-growth AI skill in 2025-2026.",
    "Terraform": "Infrastructure-as-code standard; critical for DevOps and platform engineering.",
    "CI/CD": "Continuous integration/deployment is a must-have for production-grade engineering teams.",
    "React": "Most in-demand frontend library; core requirement for full-stack positions.",
    "Node.js": "Dominant server-side JavaScript runtime; essential for full-stack development.",
    "Go": "High-performance backend language gaining rapid adoption in cloud-native systems.",
    "Firebase": "Key platform for mobile and serverless apps; speeds up MVPs and prototyping.",
    "Flutter": "Cross-platform mobile framework with strong market growth.",
    "Scikit-Learn": "Standard ML library for classical machine learning workflows.",
    "TailwindCSS": "Utility-first CSS framework dominating modern frontend development.",
    "Framer Motion": "Premium animation library valued in product-focused frontend roles.",
    "Linux": "Server administration fundamental; expected knowledge for all infrastructure roles.",
    "React Native": "Leading cross-platform mobile framework; bridges web and mobile skill sets.",
    "Swift": "Required for native iOS development.",
    "Kotlin": "Preferred language for modern Android development.",
}

# ---------------------------------------------------------------------------
# In-process rate limiter (token-bucket / sliding-window hybrid)
# ---------------------------------------------------------------------------
# Maps IP -> list[float] of request timestamps within the current window.
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def _is_rate_limited(ip: str) -> bool:
    """Return True if *ip* has exceeded RATE_LIMIT_REQUESTS in the last window."""
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW
    timestamps = _rate_limit_store[ip]
    # Evict stale entries
    _rate_limit_store[ip] = [t for t in timestamps if t > window_start]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_REQUESTS:
        return True
    _rate_limit_store[ip].append(now)
    return False


# ---------------------------------------------------------------------------
# Analytics tracker
# ---------------------------------------------------------------------------
STATS_FILE = "visitor_stats.json"


class AnalyticsTracker:
    """Lightweight in-process visitor tracker with JSON persistence."""

    def __init__(self) -> None:
        self.active_users: dict[str, float] = {}   # ip -> last_seen_timestamp
        self.total_unique_ips: set[str] = set()
        self._load_stats()

    def _load_stats(self) -> None:
        if not os.path.exists(STATS_FILE):
            return
        try:
            with open(STATS_FILE) as f:
                data = json.load(f)
                self.total_unique_ips = set(data.get("unique_ips", []))
        except Exception:
            logger.warning("Could not load visitor stats; starting fresh.")
            self.total_unique_ips = set()

    def _save_stats(self) -> None:
        try:
            with open(STATS_FILE, "w") as f:
                json.dump({"unique_ips": list(self.total_unique_ips)}, f)
        except Exception:
            logger.warning("Could not persist visitor stats.")

    def record_visit(self, ip: str) -> None:
        self.active_users[ip] = time.time()
        if ip not in self.total_unique_ips:
            self.total_unique_ips.add(ip)
            self._save_stats()

    def get_stats(self) -> dict[str, int]:
        now = time.time()
        self.active_users = {
            ip: ts for ip, ts in self.active_users.items() if now - ts < 300
        }
        return {"active": len(self.active_users), "total": len(self.total_unique_ips)}


tracker = AnalyticsTracker()

# ---------------------------------------------------------------------------
# Gemini setup
# ---------------------------------------------------------------------------
_gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
if _gemini_api_key:
    _gemini_client: genai.Client | None = genai.Client(api_key=_gemini_api_key)
else:
    _gemini_client = None
    logger.warning("GEMINI_API_KEY not set — AI features will use deterministic fallback.")


# ---------------------------------------------------------------------------
# Application lifespan (shared async resources)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Create and clean up the shared httpx client."""
    github_token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {github_token}"} if github_token else {}
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(GITHUB_TIMEOUT_SECONDS),
        headers=headers,
    )
    logger.info("httpx client initialised. GitHub auth: %s", "yes" if github_token else "no (unauthenticated — 60 req/hr)")
    yield
    await app.state.http_client.aclose()
    logger.info("httpx client closed.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="TalentForge AI Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # FIX: was allow_origins=["*"]. Wildcard + allow_credentials=True is
    # rejected by browsers AND is a security hole. Use explicit origins.
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],        # this API is read-only; lock it down
    allow_headers=["Content-Type", "Authorization"],
)


# ---------------------------------------------------------------------------
# Middleware: analytics + rate limiting
# ---------------------------------------------------------------------------
@app.middleware("http")
async def track_and_rate_limit(request: Request, call_next):
    """Record visitor IPs and enforce per-IP rate limits on /api/ routes."""
    client_host: str = request.client.host if request.client else "unknown"

    if request.url.path.startswith("/api/"):
        tracker.record_visit(client_host)

        if _is_rate_limited(client_host):
            logger.warning("Rate limit hit: %s on %s", client_host, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
            )

    return await call_next(request)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------
def _build_ai_prompt(
    description: str,
    repo_name: str,
    language: str | None,
    detailed: bool = False,
    readme_content: str | None = None,
) -> str:
    """Build the recruiter-focused AI rewrite prompt for Gemini."""
    language_label: str = language or "Unknown"
    context: str = f"Description: {description.strip()}"
    if readme_content:
        context += f"\nREADME Content (truncated):\n{readme_content[:4000]}"

    if detailed:
        return (
            "You are an elite Technical Recruiter. Rewrite the GitHub project details into "
            "a strong resume achievement statement with concrete business and engineering impact. "
            "Use 35 to 55 words, start with a strong action verb, and keep it ATS-friendly. "
            "Focus on the 'how' and 'why' based on the provided description and README context.\n"
            f"Repo Name: {repo_name}\nPrimary Language: {language_label}\n{context}"
        )
    return (
        "You are an elite Tech Recruiter. Rewrite the following GitHub project description "
        "into a single, high-impact, professional resume bullet point starting with a strong "
        "action verb. Max 25 words.\n"
        f"Repo Name: {repo_name}\nPrimary Language: {language_label}\n{context}"
    )


def _build_market_insight_prompt(
    profile: dict[str, Any], repos: list[dict[str, Any]], tech_stack: list[str]
) -> str:
    """Build a structured market-analysis prompt for Gemini."""
    top_repos = sorted(repos, key=lambda r: int(r.get("stargazers_count", 0)), reverse=True)[:12]
    compact_repos: list[dict[str, Any]] = [
        {
            "name": r.get("name"),
            "description": r.get("description"),
            "language": r.get("language"),
            "stars": r.get("stargazers_count", 0),
        }
        for r in top_repos
    ]

    return (
        "You are a senior technical recruiter and compensation analyst with deep knowledge of the CURRENT "
        "job market as of 2026. Given this GitHub profile and repositories, evaluate job-market readiness realistically. "
        "Scoring must be scientific: penalize for low star counts or missing fundamental tools that the market demands RIGHT NOW, "
        "reward for diverse stacks, trending technologies, and active contribution history.\n\n"
        "IMPORTANT CONTEXT: The tech market in 2026 heavily values cloud-native skills (Docker, Kubernetes, AWS/GCP), "
        "AI/LLM tooling (LangChain, RAG, vector databases), modern TypeScript stacks, and infrastructure-as-code. "
        "Your skill gap recommendations MUST reflect what employers are actively hiring for TODAY, not generic advice.\n\n"
        "Return only valid JSON with this schema:\n"
        '{"summary": string, "selection_probability": integer(0-100), "confidence": "Low"|"Medium"|"High", '
        '"recommended_roles": string[], "market_skill_ratings": [{"skill": string, "score": integer(1-10)}], '
        '"avg_package": {"currency": string, "min": number, "max": number, "period": string, "note": string}, '
        '"strengths": string[], "gaps": string[], "action_plan": string[], '
        '"career_growth": {"current_score": integer, "target_score": integer, '
        '"recommended_skills": [{"skill": string, "why": string}], "roadmap_summary": string}}\n\n'
        "Specific Roadmap Requirement:\n"
        "1. Analyse the user's ACTUAL tech_stack vs current market demands for their best-fit role.\n"
        "2. Identify exactly 2-3 high-demand tools they are GENUINELY missing.\n"
        "3. The 'why' for each skill must reference real market demand.\n"
        "4. Calculate 'target_score' as the realistic probability if they mastered those skills.\n"
        "5. Format 'roadmap_summary' exactly as: 'To increase your Selection Probability from X% to Y%, you should master [Skill 1] and [Skill 2].'\n\n"
        f"Profile: {json.dumps({'name': profile.get('name'), 'bio': profile.get('bio'), 'location': profile.get('location')})}\n"
        f"Tech stack: {json.dumps(tech_stack)}\n"
        f"Top repositories: {json.dumps(compact_repos)}\n"
        f"Ideal Stacks for reference: {json.dumps(ROLE_STACKS)}"
    )


# ---------------------------------------------------------------------------
# Fallback helpers (deterministic — no AI required)
# ---------------------------------------------------------------------------
def _fallback_description(
    description: str, repo_name: str, language: str | None, detailed: bool = False
) -> str:
    """Return a robust fallback description when AI output is unavailable."""
    if description and description.strip():
        if detailed:
            return (
                f"Led development of {repo_name} using {language or 'modern software engineering'}; "
                "delivered production-ready features, improved reliability, and strengthened developer "
                "workflow through structured implementation and maintainable code quality."
            )
        return description.strip()
    language_label: str = language or "software"
    if detailed:
        return (
            f"Built and iterated {repo_name}, a {language_label}-driven project, by shipping "
            "scalable features, improving maintainability, and applying strong engineering standards "
            "to support long-term product growth."
        )
    return f"Built and maintained a {language_label}-based project in {repo_name}."


def _find_best_role_and_gaps(tech_stack: list[str]) -> tuple[str, list[str]]:
    """Find the best-matching role and return missing skills sorted by market impact."""
    user_stack_lower: set[str] = {s.lower() for s in tech_stack}
    best_role, best_overlap = "Full Stack", 0

    for role, ideal_stack in ROLE_STACKS.items():
        overlap = sum(1 for s in ideal_stack if s.lower() in user_stack_lower)
        if overlap > best_overlap:
            best_overlap, best_role = overlap, role

    missing = [s for s in ROLE_STACKS[best_role] if s.lower() not in user_stack_lower]
    return best_role, missing


def _build_dynamic_career_growth(
    tech_stack: list[str], current_score: int, target_score: int
) -> dict[str, Any]:
    """Build career_growth deterministically by comparing stack against market demands."""
    best_role, missing_skills = _find_best_role_and_gaps(tech_stack)

    recommended: list[dict[str, str]] = [
        {"skill": s, "why": SKILL_WHY.get(s, f"High-demand skill for {best_role} roles.")}
        for s in missing_skills[:3]
    ]

    if not recommended:
        user_lower = {s.lower() for s in tech_stack}
        for s in ("Docker", "AWS", "Kubernetes"):
            if s.lower() not in user_lower and len(recommended) < 2:
                recommended.append({"skill": s, "why": SKILL_WHY.get(s, "")})

    skill_names = [s["skill"] for s in recommended[:2]]
    roadmap_text = (
        f"To increase your Selection Probability from {current_score}% to {target_score}%, "
        f"you should master {' and '.join(skill_names)}."
    )
    return {
        "current_score": current_score,
        "target_score": target_score,
        "recommended_skills": recommended,
        "roadmap_summary": roadmap_text,
    }


def _fallback_market_insights(
    tech_stack: list[str], repos: list[dict[str, Any]], location: str | None
) -> dict[str, Any]:
    """Generate deterministic market insights when Gemini is unavailable."""
    total_stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
    repo_count = len(repos)
    star_bonus = min(25, int(math.log10(total_stars + 1) * 10)) if total_stars > 0 else 0
    base_score = 30 + min(15, repo_count * 3) + star_bonus + min(20, len(tech_stack) * 2)
    selection_probability = max(10, min(base_score, 92))
    target_score = min(98, selection_probability + 12)

    skill_ratings = [
        {"skill": skill, "score": max(5, min(9, 5 + idx // 2))}
        for idx, skill in enumerate(tech_stack[:6])
    ] or [{"skill": "Software Engineering", "score": 5}]

    is_india = bool(location and "india" in location.lower())
    package = (
        {"currency": "INR (LPA)", "min": 6, "max": 18, "period": "per year",
         "note": "Estimate for product/startup roles based on public project evidence."}
        if is_india
        else {"currency": "USD", "min": 45000, "max": 110000, "period": "per year",
              "note": "Estimate varies by region, role seniority, and interview performance."}
    )

    return {
        "summary": "Candidate shows practical project execution and improving engineering maturity through public repositories.",
        "selection_probability": selection_probability,
        "confidence": "Medium",
        "recommended_roles": ["Software Engineer", "Backend Developer", "Full-Stack Developer"],
        "market_skill_ratings": skill_ratings,
        "avg_package": package,
        "strengths": [
            f"Demonstrates hands-on development across {repo_count} original repositories.",
            "Public code portfolio supports technical screening discussions.",
            "Clear stack specialisation visible through repository language trends.",
        ],
        "gaps": [
            "Limited proof of production-scale architecture and reliability ownership.",
            "Business impact metrics are not consistently documented in project READMEs.",
        ],
        "action_plan": [
            "Add measurable outcomes to top project READMEs (latency, reliability, adoption).",
            "Showcase one end-to-end deployed project with CI/CD and observability.",
        ],
        "career_growth": _build_dynamic_career_growth(tech_stack, selection_probability, target_score),
    }


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------
def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract and parse a JSON object from model output text."""
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Gemini wrappers — every call has an explicit asyncio timeout
# ---------------------------------------------------------------------------
async def _gemini_generate(prompt: str) -> str:
    """
    Call Gemini inside asyncio.to_thread with a hard timeout.

    Returns empty string on any failure so callers can fall back gracefully.
    """
    if _gemini_client is None:
        return ""
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                _gemini_client.models.generate_content,
                model=GEMINI_MODEL_NAME,
                contents=prompt,
            ),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
        return (response.text or "").strip() if response else ""
    except asyncio.TimeoutError:
        logger.warning("Gemini call timed out after %ss.", GEMINI_TIMEOUT_SECONDS)
        return ""
    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return ""


async def _rewrite_repo_description(
    description: str,
    repo_name: str,
    language: str | None,
    detailed: bool = False,
    readme_content: str | None = None,
) -> str:
    """Rewrite a repository description using Gemini with graceful fallback."""
    fallback = _fallback_description(description, repo_name, language, detailed=detailed)
    if _gemini_client is None:
        return fallback

    prompt = _build_ai_prompt(description, repo_name, language, detailed=detailed, readme_content=readme_content)
    text = await _gemini_generate(prompt)
    return text if text else fallback


async def _generate_market_insights(
    profile: dict[str, Any], repos: list[dict[str, Any]], tech_stack: list[str]
) -> dict[str, Any]:
    """Generate market-readiness insights using Gemini with robust fallback."""
    fallback = _fallback_market_insights(
        tech_stack=tech_stack,
        repos=repos,
        location=str(profile.get("location") or ""),
    )
    if _gemini_client is None:
        return fallback

    prompt = _build_market_insight_prompt(profile, repos, tech_stack)
    text = await _gemini_generate(prompt)
    if not text:
        return fallback

    parsed = _extract_json_object(text)
    if not parsed:
        logger.warning("Gemini returned non-JSON for market insights; using fallback.")
        return fallback

    required_keys = {
        "summary", "selection_probability", "confidence", "recommended_roles",
        "market_skill_ratings", "avg_package", "strengths", "gaps",
        "action_plan", "career_growth",
    }
    if not required_keys.issubset(parsed.keys()):
        logger.warning("Gemini JSON missing required keys; using fallback.")
        return fallback

    return parsed


async def _generate_professional_summary(
    portfolio: dict[str, Any], tech_stack: list[str]
) -> str:
    """Generate a high-impact professional summary using Gemini."""
    if _gemini_client is None:
        return str(portfolio["user"].get("bio") or "")

    project_titles = [p.get("title") for p in portfolio.get("projects", [])]
    skills = ", ".join(tech_stack[:8])
    prompt = (
        "You are a world-class resume writer. Based on the following GitHub profile and technical projects, "
        "write a 3-sentence, high-impact professional summary for a software engineer's resume. "
        "Focus on their core expertise, key achievements in their projects, and their value proposition. "
        "Do not use generic fluff; be specific and technical. Return ONLY the 3-sentence summary.\n"
        f"Name: {portfolio['user'].get('name')}\n"
        f"Bio: {portfolio['user'].get('bio')}\n"
        f"Top Projects: {', '.join(map(str, project_titles))}\n"
        f"Key Skills: {skills}"
    )
    text = await _gemini_generate(prompt)
    return text if text else str(portfolio["user"].get("bio") or "")


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------
def _check_github_rate_limit(response: httpx.Response) -> None:
    """Log a warning when the GitHub rate-limit is low."""
    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining is not None and int(remaining) < 5:
        reset_ts = response.headers.get("X-RateLimit-Reset", "unknown")
        logger.warning(
            "GitHub rate limit almost exhausted! %s remaining; resets at %s. "
            "Set GITHUB_TOKEN env var to raise the limit to 5,000 req/hr.",
            remaining, reset_ts,
        )


async def _fetch_github_profile(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """Fetch the public GitHub profile for a user."""
    response = await client.get(f"{GITHUB_API_BASE}/users/{username}")
    _check_github_rate_limit(response)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub user not found.")
    if response.status_code == 403:
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded. Try again later.")
    response.raise_for_status()
    return response.json()


async def _fetch_github_repos(client: httpx.AsyncClient, username: str) -> list[dict[str, Any]]:
    """Fetch user repositories sorted by stargazers from GitHub."""
    response = await client.get(
        f"{GITHUB_API_BASE}/users/{username}/repos",
        params={"sort": "stargazers", "per_page": 50},
    )
    _check_github_rate_limit(response)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub user not found.")
    if response.status_code == 403:
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded. Try again later.")
    response.raise_for_status()
    return response.json()


async def _fetch_repo_readme(
    client: httpx.AsyncClient, username: str, repo_name: str
) -> str | None:
    """Fetch and decode the README for a repository."""
    try:
        response = await client.get(f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/readme")
        if response.status_code != 200:
            return None
        content_b64: str = response.json().get("content", "")
        return base64.b64decode(content_b64).decode("utf-8", errors="ignore")
    except Exception:
        return None


def _extract_tech_stack(repos: list[dict[str, Any]]) -> list[str]:
    """Create a unique, sorted list of languages across all repositories."""
    return sorted({
        repo["language"]
        for repo in repos
        if isinstance(repo.get("language"), str) and repo.get("language")
    })


def _filter_original_repos(repos: list[dict[str, Any]], username: str) -> list[dict[str, Any]]:
    """Filter out forks and profile README repositories."""
    return [
        r for r in repos
        if not r.get("fork") and str(r.get("name", "")).lower() != username.lower()
    ]


def _rank_top_original_repos(
    repos: list[dict[str, Any]], username: str, limit: int = TOP_PORTFOLIO_PROJECTS
) -> list[dict[str, Any]]:
    """Filter and rank original repositories by star count."""
    filtered = _filter_original_repos(repos, username)
    return sorted(filtered, key=lambda r: int(r.get("stargazers_count", 0)), reverse=True)[:limit]


# ---------------------------------------------------------------------------
# Core payload builders
# ---------------------------------------------------------------------------
async def _build_projects_with_ai(
    username: str, top_repos: list[dict[str, Any]], detailed: bool = False
) -> list[dict[str, Any]]:
    """Transform top repositories into AI-enhanced project summaries.

    For the detailed (CV) path we first fetch all READMEs concurrently, then
    fan out Gemini rewrites — also concurrently.  The two gather() calls are
    intentionally sequential: we must have the READMEs before we can build the
    AI prompts.  Within each phase, full concurrency is preserved.
    """
    client: httpx.AsyncClient = app.state.http_client

    if detailed:
        readmes = await asyncio.gather(
            *[_fetch_repo_readme(client, username, str(r.get("name") or "")) for r in top_repos]
        )
    else:
        readmes = [None] * len(top_repos)

    rewritten_descriptions: list[str] = await asyncio.gather(
        *[
            _rewrite_repo_description(
                description=str(r.get("description") or ""),
                repo_name=str(r.get("name") or "Untitled Project"),
                language=r.get("language"),
                detailed=detailed,
                readme_content=readme,
            )
            for r, readme in zip(top_repos, readmes)
        ]
    )

    return [
        {
            "title": r.get("name"),
            "ai_description": desc,
            "language": r.get("language"),
            "stars": r.get("stargazers_count", 0),
            "url": r.get("html_url"),
        }
        for r, desc in zip(top_repos, rewritten_descriptions)
    ]


async def _get_portfolio_payload(
    username: str, page: int = 1, page_size: int = TOP_PORTFOLIO_PROJECTS
) -> dict[str, Any]:
    """Build the complete portfolio payload for API responses."""
    client: httpx.AsyncClient = app.state.http_client

    # Phase 1 — fetch profile and repos in parallel (no dependency between them)
    profile, repos = await asyncio.gather(
        _fetch_github_profile(client, username),
        _fetch_github_repos(client, username),
    )

    all_original_repos = _rank_top_original_repos(repos, username, limit=10_000)
    total_projects = len(all_original_repos)
    start_idx = (page - 1) * page_size
    paginated_repos = all_original_repos[start_idx : start_idx + page_size]
    tech_stack = _extract_tech_stack(repos)

    # Phase 2 — AI work for projects and market insights runs in parallel
    projects, market_insights = await asyncio.gather(
        _build_projects_with_ai(username, paginated_repos),
        _generate_market_insights(profile=profile, repos=all_original_repos, tech_stack=tech_stack),
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


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------
def _pdf_to_bytes(pdf: FPDF) -> bytes:
    """Convert FPDF output into bytes for streaming."""
    raw_output: Any = pdf.output(dest="S")
    if isinstance(raw_output, (bytes, bytearray)):
        return bytes(raw_output)
    return str(raw_output).encode("latin-1")


def _build_resume_pdf(portfolio: dict[str, Any], username: str) -> bytes:
    """Generate a polished PDF resume in memory from portfolio data."""
    user: dict[str, Any] = portfolio["user"]
    top_projects: list[dict[str, Any]] = portfolio["projects"][:TOP_CV_PROJECTS]
    tech_stack: list[str] = portfolio.get("tech_stack", [])
    prof_summary: str = portfolio.get("professional_summary", "")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(left=15, top=15, right=15)

    name = str(user.get("name") or username)
    github_url = str(user.get("github_url") or f"https://github.com/{username}")
    location = str(user.get("location") or "Location not specified")

    # Header
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 12, name, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"{github_url}  |  {location}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    # Professional Summary
    if prof_summary:
        pdf.set_draw_color(0, 102, 204)
        pdf.set_line_width(0.5)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(4)
        pdf.set_text_color(35, 35, 35)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 7, "Professional Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 6, prof_summary)
        pdf.ln(3)

    # Technical Skills
    if tech_stack:
        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(4)
        pdf.set_text_color(35, 35, 35)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 7, "Core Technical Skills", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 6, ", ".join(tech_stack[:15]))
        pdf.ln(3)

    # Technical Projects
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)
    pdf.set_text_color(35, 35, 35)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Selected Technical Projects", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    for project in top_projects:
        title = str(project.get("title") or "Untitled Project")
        language = str(project.get("language") or "Unknown")
        ai_description = " ".join(str(project.get("ai_description") or "").split())
        stars = int(project.get("stars") or 0)
        project_url = str(project.get("url") or "")

        pdf.set_text_color(20, 20, 20)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(pdf.w - pdf.l_margin - pdf.r_margin - 40, 7, title)
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(40, 7, f"[{language}]", align="R", new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(120, 120, 120)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, f"Stars: {stars}  |  {project_url}", new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(50, 50, 50)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_x(pdf.l_margin + 3)
        pdf.multi_cell(0, 6, f"- {ai_description}")
        pdf.ln(2.5)

    # Footer
    pdf.set_y(-20)
    pdf.set_draw_color(230, 230, 230)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)
    pdf.set_text_color(150, 150, 150)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Generated by TalentForge AI Resume Engine", align="C")

    return _pdf_to_bytes(pdf)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.get("/api/portfolio/{username}")
async def get_portfolio(
    username: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=TOP_PORTFOLIO_PROJECTS, ge=1, le=MAX_PORTFOLIO_PAGE_SIZE),
) -> dict[str, Any]:
    """Return AI-enhanced portfolio data for a GitHub username."""
    try:
        return await _get_portfolio_payload(username=username, page=page, page_size=page_size)
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="GitHub API error.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Unable to reach GitHub API.")


@app.get("/api/cv/{username}")
async def get_cv(username: str) -> StreamingResponse:
    """Generate and stream a professional PDF resume for the given username."""
    try:
        client: httpx.AsyncClient = app.state.http_client

        # Phase 1 — parallel GitHub fetches
        profile, repos = await asyncio.gather(
            _fetch_github_profile(client, username),
            _fetch_github_repos(client, username),
        )

        top_repos_for_cv = _rank_top_original_repos(repos, username, limit=TOP_CV_PROJECTS)
        tech_stack = _extract_tech_stack(repos)

        # Phase 2 — parallel: AI project rewrites + professional summary
        cv_projects, professional_summary = await asyncio.gather(
            _build_projects_with_ai(username, top_repos_for_cv, detailed=True),
            # summary needs a skeleton portfolio dict — build it cheaply here
            _generate_professional_summary(
                portfolio={
                    "user": {
                        "name": profile.get("name") or profile.get("login"),
                        "bio": profile.get("bio"),
                    },
                    "projects": [
                        {"title": r.get("name")}
                        for r in top_repos_for_cv
                    ],
                },
                tech_stack=tech_stack,
            ),
        )

        portfolio: dict[str, Any] = {
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

        pdf_bytes = _build_resume_pdf(portfolio=portfolio, username=username)

    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="GitHub API error.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Unable to reach GitHub API.")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{username}_resume.pdf"'},
    )


@app.get("/api/stats")
async def get_stats() -> dict[str, int]:
    """Return visitor statistics."""
    return tracker.get_stats()


# ---------------------------------------------------------------------------
# *** DO NOT MODIFY — Static file serving for all-in-one Render deployment ***
# ---------------------------------------------------------------------------
# Serve static assets (CSS, JS, etc.)
if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")


# The catch-all: sends the user to the React UI
@app.get("/{catchall:path}")
async def serve_frontend(catchall: str):
    if catchall.startswith("api"):
        return JSONResponse(status_code=404, content={"error": "API route not found"})
    if os.path.exists("dist/index.html"):
        return FileResponse("dist/index.html")
    return JSONResponse(
        status_code=503,
        content={"error": "Frontend build not found. Ensure 'npm run build' completed."},
    )


# Serve the React build (all-in-one container)
_dist_path = os.path.join(os.path.dirname(__file__), "dist")
if os.path.isdir(_dist_path):
    app.mount("/", StaticFiles(directory=_dist_path, html=True), name="static")
# ---------------------------------------------------------------------------
# *** END — Static file serving block ***
# ---------------------------------------------------------------------------
