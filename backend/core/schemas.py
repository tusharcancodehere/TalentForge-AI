from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class Compensation(BaseModel):
    INR: str
    USD: str


class EconomicAnalysis(BaseModel):
    readiness_score: int
    compensation: Compensation


class Blueprint(BaseModel):
    project_name: str
    elevator_pitch: str
    the_stack: list[str]
    core_architecture: str
    implementation_milestones: list[str]
    market_value_boost: str


class SeoMetadata(BaseModel):
    og_title: str
    og_description: str
    json_ld: Any
    target_keywords: list[str]


class CareerArchitectResponse(BaseModel):
    # Must remain aligned with frontend `src/lib/github.ts` for protocol compatibility.
    executive_summary: str
    architect_classification: Literal["System Architect", "Developer"] | str
    resume_html: str
    blueprint: Blueprint
    economic_analysis: EconomicAnalysis
    seo_metadata: SeoMetadata
    social_share_narrative: str
    error_code: str | None

