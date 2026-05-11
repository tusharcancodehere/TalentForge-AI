from __future__ import annotations

import asyncio
import json
import logging
import math
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


def _build_career_architect_prompt(
    profile: dict[str, Any],
    repos: list[dict[str, Any]],
    tech_stack: list[str],
    grit_meta: dict[str, Any] | None = None,
) -> str:
    top_repos = sorted(repos, key=lambda r: int(r.get("stargazers_count", 0)), reverse=True)[:8]
    compact_repos = [
        {
            "name": r.get("name"),
            "description": r.get("description"),
            "language": r.get("language"),
            "stars": r.get("stargazers_count", 0),
            "topics": r.get("topics", []),
            "readme_excerpt": (r.get("readme_content") or "")[:2500] if r.get("readme_content") else None,
        }
        for r in top_repos
    ]

    grit_block = ""
    if grit_meta:
        grit_block = (
            "\n**GRIT INTELLIGENCE (calculated from GitHub Events API):**\n"
            f"- Commits (last 90 days): {grit_meta.get('total_commits_90d', 0)}\n"
            f"- Active weeks: {grit_meta.get('active_weeks_90d', 0)}/13\n"
            f"- Grit Score: {grit_meta.get('grit_score', 0)}/100\n"
            f"- Project Velocity: {grit_meta.get('project_velocity', 'Unknown')}\n"
            f"- Language Diversity: {', '.join(grit_meta.get('language_diversity', []))}\n"
            f"- CI/CD detected: {grit_meta.get('has_ci_cd', False)}\n"
            f"- Containerization detected: {grit_meta.get('has_docker', False)}\n"
            f"- Agentic/AI patterns detected: {grit_meta.get('has_agentic_patterns', False)}\n"
            f"- Original repos: {grit_meta.get('original_repo_count', 0)}\n"
        )

        sem = grit_meta.get("semantic_links") if isinstance(grit_meta, dict) else None
        if sem and sem.get("links"):
            grit_block += (
                f"\n**SEMANTIC INTELLIGENCE (cross-repo architectural analysis):**\n"
                f"- Classification: {sem.get('classification')}\n"
                f"- System Architecture Score: {sem.get('system_score')}/100\n"
                f"- Detected Links:\n"
            )
            for link in sem.get("links", []):
                grit_block += f"  * {link}\n"

        grit_block += (
            f"\n**PEER INTELLIGENCE & PERCENTILE RANKING:**\n"
            f"You are evaluating User #{grit_meta.get('total_users', 0)}. Based on the platform's distribution, "
            f"this user's Grit Score of {grit_meta.get('grit_score', 0)} places them in the {grit_meta.get('percentile', 50)}th "
            f"percentile of all analyzed developers.\n\n"
            "**THE 'SORTING HAT' LOGIC (Execute in the Executive Summary):**\n"
            "Based on their percentile and Architect Classification, deliver a brutally honest 'Market Prediction' regarding where they would be hired today.\n"
            "- Bottom 50% (The Reality Check): 'Currently tracking for: Low-tier IT Services or un-funded agency. Your architecture is fundamentally generic. To break out of the 50th percentile, you must master [Missing Advanced Skill].'\n"
            "- 50% - 85% (The Danger Zone): 'Currently tracking for: Series A/B Startups. You are a capable builder, but you lack the \"Agentic Edge\" to command Top-Tier compensation. You are stuck in the middle of the bell curve.'\n"
            "- Top 15% (The Elite Induction): 'Currently tracking for: Tier-1 Tech (FAANG / Breakout AI Startups). Welcome to the top [X]%. Your [Specific Repo Pattern] proves you don't just write code; you engineer systems.'\n\n"
            "**SOCIAL FLEX GENERATOR:**\n"
            "If the user is in the Top 15%, update the `og_description` to explicitly state their percentile: "
            "'Scored in the Top [X]% of engineers on TalentForge AI. Currently tracking for Tier-1 Market Readiness.'\n"
        )

    return (
        "**ROLE:** You are the 'TalentForge Executive Architect,' an elite Technical Headhunter "
        "and Engineering Manager specializing in the 2026 Global Tech Market.\n\n"
        "**2026 MARKET CONTEXT:**\n"
        "The market ignores generic tutorials and to-do apps. It values:\n"
        "1. **Agentic Orchestration:** LLMs as tools (MCP, tool-use, RAG pipelines).\n"
        "2. **System Resilience:** Distributed systems, containerization, edge computing, observability.\n"
        "3. **Proof of Work:** Shipped products over traditional degrees.\n"
        "4. **Cloud-Native Fluency:** IaC (Terraform), CI/CD, managed services.\n\n"
        "**LOGIC RULES:**\n"
        "- **10/90 Rule:** Top 10% of repos get 90% of the analysis. Ignore boilerplate.\n"
        "- **STAR Method:** Every achievement: [Situation/Task] -> [Action] -> [Quantifiable Result].\n"
        "- **Skill Verification:** Only list skills evidenced by actual code. Do NOT hallucinate.\n"
        "- **README Deep-Dive:** Extract 'Engineering Intent' (the Why), not just features.\n\n"
        f"{grit_block}\n"
        "**STRICT OUTPUT — JSON ONLY (no markdown fences, no explanation):**\n"
        "{\n"
        '  "executive_summary": "3-sentence high-impact narrative. No clichés. Engineering language.",\n'
        '  "architect_classification": "System Architect | Developer",\n'
        '  "resume_html": "<div class=\\"bg-slate-900 text-white p-8 space-y-6...\\">...</div>",\n'
        '  "blueprint": {\n'
        '    "project_name": "Striking title",\n'
        '    "elevator_pitch": "The hook combining 2 skill gaps",\n'
        '    "the_stack": ["Tool 1", "Tool 2"],\n'
        '    "core_architecture": "Flow description (Agentic, Event-Driven, etc)",\n'
        '    "implementation_milestones": ["M1", "M2", "M3"],\n'
        '    "market_value_boost": "+X%"\n'
        "  },\n"
        '  "economic_analysis": {\n'
        '    "readiness_score": 75,\n'
        '    "compensation": { "INR": "Range in Lakhs", "USD": "Global remote range" }\n'
        "  },\n"
        '  "seo_metadata": {\n'
        '    "og_title": "...",\n'
        '    "og_description": "...",\n'
        '    "json_ld": {"@context":"https://schema.org","@type":"Person",...},\n'
        '    "target_keywords": ["Keyword1", "Keyword2"]\n'
        "  },\n"
        '  "social_share_narrative": "Just got my engineering audit from TalentForge AI...",\n'
        '  "error_code": null\n'
        "}\n\n"
        "**THE SECRET ERROR PROTOCOL:**\n"
        "If failure occurs or input is invalid, output ONLY the error code (e.g., `[TFAI-010]`). "
        "Use [TFAI-001] for Timeout, [TFAI-040] for Shadow/Fork Profile, [TFAI-051] for Hallucinated Skills, [TFAI-014] for Off-topic.\n\n"
        "**TONE:** Technical, assertive, zero-fluff. Action Verbs: Architected, Orchestrated, Decoupled, Hardened.\n\n"
        f"Profile: {json.dumps({'name': profile.get('name'), 'bio': profile.get('bio'), 'location': profile.get('location')})}\n"
        f"Tech stack: {json.dumps(tech_stack)}\n"
        f"Top repositories: {json.dumps(compact_repos)}\n"
    )


def _fallback_career_architect(
    tech_stack: list[str],
    repos: list[dict[str, Any]],
    location: str | None,
    grit_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sem = (grit_meta or {}).get("semantic_links", {}) if isinstance(grit_meta, dict) else {}
    arch_class = sem.get("classification", "Developer")

    total_stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
    repo_count = len([r for r in repos if not r.get("fork")])
    base = 30 + min(15, repo_count * 2) + min(20, len(tech_stack) * 2)
    star_bonus = min(15, int(math.log10(total_stars + 1) * 8)) if total_stars > 0 else 0
    grit_bonus = (int(grit_meta.get("grit_score", 0)) // 5) if grit_meta else 0
    sys_score = int(sem.get("system_score", 0) or 0)
    arch_bonus = min(10, sys_score // 5)
    score = max(15, min(95, base + star_bonus + grit_bonus + arch_bonus))

    best_role, missing_skills = find_best_role_and_gaps(tech_stack)
    if arch_class == "System Architect":
        best_role = "System Architect"

    gaps = missing_skills[:3]
    critical = ["Docker", "Kubernetes", "AWS/GCP", "LangChain/CrewAI", "Vector Databases", "Terraform", "CI/CD Pipelines"]
    for g in critical:
        if len(gaps) >= 5:
            break
        base_name = g.split("/")[0].split("(")[0].strip()
        if base_name.lower() not in {s.lower() for s in tech_stack} and g not in gaps:
            gaps.append(g)
    gaps = gaps[:5]

    percentile = int(grit_meta.get("percentile", 50)) if grit_meta else 50
    if percentile >= 85:
        tracking_statement = (
            f"Currently tracking for: Tier-1 Tech (FAANG / Breakout AI Startups). "
            f"Welcome to the top {100 - percentile}%. Your cross-repo architecture proves you don't just write code; you engineer systems."
        )
        og_desc = (
            f"Scored in the Top {100 - percentile}% of engineers on TalentForge AI. "
            "Currently tracking for Tier-1 Market Readiness."
        )
    elif percentile >= 50:
        tracking_statement = (
            "Currently tracking for: Series A/B Startups. You are a capable builder, but you lack the 'Agentic Edge' "
            "to command Top-Tier compensation. You are stuck in the middle of the bell curve."
        )
        og_desc = f"View the career trajectory for a {arch_class} with a {score} readiness score."
    else:
        tracking_statement = (
            "Currently tracking for: Low-tier IT Services or un-funded agency. Your architecture is fundamentally generic. "
            f"To break out of the 50th percentile, you must master {gaps[0] if gaps else 'advanced systems'}."
        )
        og_desc = f"View the career trajectory for a {arch_class} with a {score} readiness score."

    comp = {
        "INR": "6-15 LPA" if score < 65 else "12-25 LPA",
        "USD": "35k-70k" if score < 65 else "65k-120k",
    }

    return {
        "executive_summary": (
            f"Results-driven Software Engineer with demonstrated proficiency in {', '.join(tech_stack[:3]) or 'modern frameworks'}. "
            f"Built {repo_count} original repositories with a focus on {best_role.lower()} architecture. "
            f"{tracking_statement}"
        ),
        "architect_classification": arch_class,
        "resume_html": (
            f"<div class='bg-slate-900 text-white p-8 space-y-6'>"
            f"<h1>{best_role}</h1><p>Deterministic Resume Generated. {repo_count} Repositories evaluated.</p></div>"
        ),
        "blueprint": {
            "project_name": "Gap-Closer System",
            "elevator_pitch": "A concrete portfolio upgrade designed to close market gaps with one shipped, production-grade system.",
            "the_stack": tech_stack[:4] or ["Software Engineering"],
            "core_architecture": "A modular service with clear boundaries, observable runtime, and deployable pipeline.",
            "implementation_milestones": ["M1: Ship a deployable API", "M2: Add CI/CD + observability", "M3: Publish a measurable case study"],
            "market_value_boost": "+15%",
        },
        "economic_analysis": {"readiness_score": score, "compensation": comp},
        "seo_metadata": {
            "og_title": f"{best_role} Profile | TalentForge",
            "og_description": og_desc,
            "json_ld": {"@context": "https://schema.org", "@type": "Person", "jobTitle": best_role},
            "target_keywords": tech_stack[:5] or ["Software Engineering"],
        },
        "social_share_narrative": (
            f"Just got my engineering audit from TalentForge AI. Officially classified as a '{arch_class}'. "
            f"My Readiness Score just hit {score}/100."
        ),
        "error_code": None,
    }


async def generate_career_architect(
    profile: dict[str, Any], repos: list[dict[str, Any]], tech_stack: list[str], grit_meta: dict[str, Any] | None = None
) -> dict[str, Any]:
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

