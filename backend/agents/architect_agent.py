from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import google.genai as genai
from google.genai import types as genai_types

from backend.core.grit_logic import ROLE_STACKS, find_best_role_and_gaps, SKILL_WHY

logger = logging.getLogger("talentforge.agents")

GEMINI_MODEL_NAME: str = "gemini-1.5-pro"
GEMINI_TIMEOUT_SECONDS: float = 25.0


def _get_gemini_client() -> genai.Client | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — AI features will use deterministic fallback.")
        return None
    return genai.Client(api_key=api_key)


_gemini_client = _get_gemini_client()


async def _call_gemini_with_timeout(prompt: str, response_mime_type: str = "application/json") -> str | None:
    if _gemini_client is None:
        return None
    try:
        response = await asyncio.wait_for(
            _gemini_client.models.generate_content_async(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config=genai_types.GenerateContentConfig(response_mime_type=response_mime_type),
            ),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
        return response.text
    except Exception as exc:
        logger.error("Gemini call failed: %s", exc)
        return None


def _extract_json_object(text: str) -> dict[str, Any] | None:
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


def _build_ai_prompt(
    description: str,
    repo_name: str,
    language: str | None,
    detailed: bool = False,
    readme_content: str | None = None,
) -> str:
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


def _fallback_description(
    description: str, repo_name: str, language: str | None, detailed: bool = False
) -> str:
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


async def _rewrite_repo_description(
    description: str,
    repo_name: str,
    language: str | None,
    detailed: bool = False,
    readme_content: str | None = None,
) -> str:
    fallback = _fallback_description(description, repo_name, language, detailed=detailed)
    if _gemini_client is None:
        return fallback

    prompt = _build_ai_prompt(description, repo_name, language, detailed=detailed, readme_content=readme_content)
    response = await _call_gemini_with_timeout(prompt, response_mime_type="text/plain")
    return response or fallback


async def build_projects_with_ai(
    http_client,
    username: str,
    top_repos: list[dict[str, Any]],
    detailed: bool = False,
) -> list[dict[str, Any]]:
    from backend.core.github_engine import fetch_repo_readme

    if detailed:
        readmes = await asyncio.gather(
            *[fetch_repo_readme(http_client, username, str(r.get("name") or "")) for r in top_repos]
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


async def generate_market_insights(
    profile: dict[str, Any], repos: list[dict[str, Any]], tech_stack: list[str]
) -> dict[str, Any]:
    from backend.main import logger  # reuse central logger
    from math import log10

    fallback = {
        "summary": "Candidate shows practical project execution and improving engineering maturity through public repositories.",
        "selection_probability": 50,
        "confidence": "Medium",
        "recommended_roles": ["Software Engineer", "Backend Developer", "Full-Stack Developer"],
        "market_skill_ratings": [
            {"skill": tech_stack[0], "score": 7},
        ]
        if tech_stack
        else [{"skill": "Software Engineering", "score": 5}],
        "avg_package": {
            "currency": "USD",
            "min": 45000,
            "max": 110000,
            "period": "per year",
            "note": "Estimate varies by region, role seniority, and interview performance.",
        },
        "strengths": [],
        "gaps": [],
        "action_plan": [],
        "career_growth": {
            "current_score": 50,
            "target_score": 65,
            "recommended_skills": [],
            "roadmap_summary": "",
        },
    }
    if _gemini_client is None:
        return fallback

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

    prompt = (
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

    text = await _call_gemini_with_timeout(prompt, response_mime_type="text/plain")
    if not text:
        return fallback

    parsed = _extract_json_object(text)
    if not parsed:
        logger.warning("Gemini returned non-JSON for market insights; using fallback.")
        return fallback

    required_keys = {
        "summary",
        "selection_probability",
        "confidence",
        "recommended_roles",
        "market_skill_ratings",
        "avg_package",
        "strengths",
        "gaps",
        "action_plan",
        "career_growth",
    }
    if not required_keys.issubset(parsed.keys()):
        logger.warning("Gemini JSON missing required keys; using fallback.")
        return fallback

    return parsed


async def generate_career_architect(
    profile: dict[str, Any], repos: list[dict[str, Any]], tech_stack: list[str], grit_meta: dict[str, Any] | None = None
) -> dict[str, Any]:
    from backend.main import logger  # central logger

    from math import log10

    # Reuse the existing JSON schema and Sorting Hat / Market Prediction logic
    from backend.main import _fallback_career_architect, _build_career_architect_prompt  # type: ignore

    fallback = _fallback_career_architect(
        tech_stack=tech_stack,
        repos=repos,
        location=str(profile.get("location") or ""),
        grit_meta=grit_meta,
    )
    if _gemini_client is None:
        return fallback

    prompt = _build_career_architect_prompt(profile, repos, tech_stack, grit_meta=grit_meta)
    text = await _call_gemini_with_timeout(prompt, response_mime_type="text/plain")
    if not text:
        return fallback

    if text.strip().startswith("[TFAI-"):
        return {"error_code": text.strip()[:10], **fallback}

    parsed = _extract_json_object(text)
    if not parsed:
        logger.warning("Gemini returned non-JSON for career architect; using fallback.")
        return fallback

    required_keys = {
        "executive_summary",
        "architect_classification",
        "resume_html",
        "blueprint",
        "economic_analysis",
        "seo_metadata",
        "social_share_narrative",
    }
    if not required_keys.issubset(parsed.keys()):
        logger.warning("Gemini JSON missing required keys for career architect; using fallback.")
        return fallback

    return parsed


async def generate_professional_summary(
    user_name: str, bio: str | None, project_titles: list[str], tech_stack: list[str]
) -> str:
    if _gemini_client is None:
        return str(bio or "")

    skills = ", ".join(tech_stack[:8])
    prompt = (
        "You are a world-class resume writer. Based on the following GitHub profile and technical projects, "
        "write a 3-sentence, high-impact professional summary for a software engineer's resume. "
        "Focus on their core expertise, key achievements in their projects, and their value proposition. "
        "Do not use generic fluff; be specific and technical. Return ONLY the 3-sentence summary.\n"
        f"Name: {user_name}\n"
        f"Bio: {bio}\n"
        f"Top Projects: {', '.join(map(str, project_titles))}\n"
        f"Key Skills: {skills}"
    )
    text = await _call_gemini_with_timeout(prompt, response_mime_type="text/plain")
    return text or str(bio or "")


async def chat_with_coach_agent(request_data: dict[str, Any], message: str, history: list[Any]) -> str:
    if _gemini_client is None:
        return "I'm currently offline, but you can still follow the roadmap above to improve your score!"

    history_text = ""
    if history:
        for msg in history[-4:]:
            history_text += f"{msg.role.upper()}: {msg.content}\n"

    prompt = (
        "**IDENTITY:** You are the TalentForge Agent, a elite Technical Career Coach for the 2026 tech market. You have been provided with the JSON output from the 'Career Architect' analysis of the user's GitHub.\n\n"
        "**YOUR KNOWLEDGE BASE:**\n"
        "- User's Impact Statements (STAR method results).\n"
        "- User's 2026 Readiness Score and identified Skill Gaps.\n"
        "- Current 2026 hiring trends (AI Agents, Cloud-Native, High-Velocity Dev).\n\n"
        "**GOAL:**\n"
        "Help the user bridge the gap between where they are and their target role.\n\n"
        "**COMMUNICATION GUIDELINES:**\n"
        "1. **Be Technical:** If they ask how to fix a skill gap, don't just say 'Learn Docker.' Say 'Containerize your FastAPI backend and deploy it to an EKS cluster using GitHub Actions.'\n"
        "2. **Context-Aware:** If they ask about their summary, refer to specific projects from the JSON.\n"
        "3. **The 'Independent Learner' Bias:** You respect self-taught developers. Encourage their 'proof of work' over traditional credentials.\n"
        "4. **No Clutter:** Keep responses under 100 words. Be punchy, direct, and slightly witty—like a senior dev mentoring a high-performing junior.\n"
        "5. **JSON-Only Context:** Use the provided Architect JSON as the absolute truth. If the JSON says they lack AWS skills, don't tell them they are an AWS expert.\n\n"
        "**RESTRICTION:** Only discuss tech careers and GitHub improvement. If asked about unrelated topics, pivot back to their professional brand.\n\n"
        f"**ARCHITECT JSON DATA:**\n{json.dumps(request_data)}\n\n"
        f"**CHAT HISTORY:**\n{history_text}\n"
        f"**USER MESSAGE:**\n{message}"
    )
    response_text = await _call_gemini_with_timeout(prompt, response_mime_type="text/plain")
    return response_text or "The TalentForge Agent is currently rebooting. Please try again in a moment."

