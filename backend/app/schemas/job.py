from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FlexibleJobModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class JobBase(FlexibleJobModel):
    company: str = "Unknown Company"
    title: str = "Unknown Title"
    location: str = "Unknown"
    url: str = ""
    source: str = "manual"
    job_description: str = ""
    employment_type: str | None = None
    remote_status: str | None = None
    role_category: str | None = None
    seniority_level: str | None = None
    years_experience_min: int | None = None
    years_experience_max: int | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    application_questions: list[str] = Field(default_factory=list)
    raw_parsed_data: dict[str, Any] = Field(default_factory=dict)
    verification_evidence: list[str] = Field(default_factory=list)
    verification_raw_data: dict[str, Any] = Field(default_factory=dict)
    last_verification_error: str | None = None
    posted_date: date | None = None
    first_seen_date: date | None = None
    last_seen_date: date | None = None
    last_checked_date: date | None = None
    closed_date: date | None = None
    verification_status: str = "unknown"
    verification_score: float = 0.0
    likely_closed_score: float = 0.0
    skill_match_score: float = 0.0
    role_match_score: float = 0.0
    experience_fit_score: float = 0.0
    profile_keyword_score: float = 0.0
    resume_match_score: float = 0.0
    freshness_score: float = 0.0
    location_score: float = 0.0
    application_ease_score: float = 0.0
    overall_priority_score: float = 0.0
    scoring_status: str = "unscored"
    scoring_evidence: dict[str, Any] = Field(default_factory=dict)
    scoring_raw_data: dict[str, Any] = Field(default_factory=dict)
    scored_at: datetime | None = None
    application_status: str = "found"
    application_link_opened_at: datetime | None = None
    packet_generated_at: datetime | None = None
    applied_at: datetime | None = None
    follow_up_at: datetime | None = None
    interview_at: datetime | None = None
    rejected_at: datetime | None = None
    offer_at: datetime | None = None
    withdrawn_at: datetime | None = None
    closed_before_apply_at: datetime | None = None
    user_notes: str | None = None
    next_action: str | None = None
    next_action_due_at: datetime | None = None

    @field_validator(
        "required_skills",
        "preferred_skills",
        "responsibilities",
        "requirements",
        "education_requirements",
        "application_questions",
        "verification_evidence",
        mode="before",
    )
    @classmethod
    def default_list_fields(cls, value: list[str] | None) -> list[str]:
        return value or []

    @field_validator("raw_parsed_data", "verification_raw_data", "scoring_evidence", "scoring_raw_data", mode="before")
    @classmethod
    def default_raw_parsed_data(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        return value or {}


class JobCreate(JobBase):
    pass


class JobUpdate(FlexibleJobModel):
    company: str | None = None
    title: str | None = None
    location: str | None = None
    url: str | None = None
    source: str | None = None
    job_description: str | None = None
    employment_type: str | None = None
    remote_status: str | None = None
    role_category: str | None = None
    seniority_level: str | None = None
    years_experience_min: int | None = None
    years_experience_max: int | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    responsibilities: list[str] | None = None
    requirements: list[str] | None = None
    education_requirements: list[str] | None = None
    application_questions: list[str] | None = None
    raw_parsed_data: dict[str, Any] | None = None
    verification_evidence: list[str] | None = None
    verification_raw_data: dict[str, Any] | None = None
    last_verification_error: str | None = None
    posted_date: date | None = None
    first_seen_date: date | None = None
    last_seen_date: date | None = None
    last_checked_date: date | None = None
    closed_date: date | None = None
    verification_status: str | None = None
    verification_score: float | None = None
    likely_closed_score: float | None = None
    skill_match_score: float | None = None
    role_match_score: float | None = None
    experience_fit_score: float | None = None
    profile_keyword_score: float | None = None
    resume_match_score: float | None = None
    freshness_score: float | None = None
    location_score: float | None = None
    application_ease_score: float | None = None
    overall_priority_score: float | None = None
    scoring_status: str | None = None
    scoring_evidence: dict[str, Any] | None = None
    scoring_raw_data: dict[str, Any] | None = None
    scored_at: datetime | None = None
    application_status: str | None = None
    application_link_opened_at: datetime | None = None
    packet_generated_at: datetime | None = None
    applied_at: datetime | None = None
    follow_up_at: datetime | None = None
    interview_at: datetime | None = None
    rejected_at: datetime | None = None
    offer_at: datetime | None = None
    withdrawn_at: datetime | None = None
    closed_before_apply_at: datetime | None = None
    user_notes: str | None = None
    next_action: str | None = None
    next_action_due_at: datetime | None = None


class JobRead(JobBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobImportRequest(FlexibleJobModel):
    input_type: Literal["description", "url"]
    content: str
    source: str = "manual"


class JobParseResult(JobBase):
    input_type: Literal["description", "url"]
    parse_mode: str = "rule_based_v1"


class JobVerificationResult(FlexibleJobModel):
    verification_status: str
    verification_score: float
    likely_closed_score: float
    evidence: list[str] = Field(default_factory=list)
    checked_at: str
    http_status: int | None = None
    final_url: str = ""
    redirected: bool = False
    page_title: str = ""
    days_since_posted: int | None = None
    days_since_first_seen: int | None = None
    last_checked_date: date | None = None
    last_seen_date: date | None = None
    closed_date: date | None = None
    freshness_score: float = 0.0
    overall_priority_score: float = 0.0
    verification_raw_data: dict[str, Any] = Field(default_factory=dict)
    last_verification_error: str | None = None


class JobVerificationResponse(FlexibleJobModel):
    job: JobRead
    verification: JobVerificationResult


class JobScoreResult(FlexibleJobModel):
    skill_match_score: float = 0.0
    role_match_score: float = 0.0
    experience_fit_score: float = 0.0
    profile_keyword_score: float = 0.0
    resume_match_score: float = 0.0
    freshness_score: float = 0.0
    location_score: float = 0.0
    application_ease_score: float = 0.0
    verification_score: float = 0.0
    overall_priority_score: float = 0.0
    scoring_status: str = "unscored"
    scored_at: str | None = None
    evidence: list[str] = Field(default_factory=list)
    scoring_evidence: dict[str, Any] = Field(default_factory=dict)
    scoring_raw_data: dict[str, Any] = Field(default_factory=dict)


class JobScoringResponse(FlexibleJobModel):
    job: JobRead
    score: JobScoreResult


class TopJobSummary(FlexibleJobModel):
    id: int
    company: str
    title: str
    overall_priority_score: float
    resume_match_score: float
    verification_status: str


class ScoreAllSummary(FlexibleJobModel):
    total_jobs: int
    scored_count: int
    skipped_count: int
    average_resume_match_score: float = 0.0
    average_overall_priority_score: float = 0.0
    top_jobs: list[TopJobSummary] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RecommendationResponse(FlexibleJobModel):
    count: int
    jobs: list[JobRead] = Field(default_factory=list)


class VerifyAllSummary(FlexibleJobModel):
    total_jobs: int
    verified_count: int
    skipped_count: int
    open_count: int
    probably_open_count: int
    unknown_count: int
    possibly_closed_count: int
    likely_closed_count: int
    closed_count: int
    errors: list[str] = Field(default_factory=list)


class VerifyUrlRequest(FlexibleJobModel):
    url: str
    first_seen_date: date | None = None
    posted_date: date | None = None
