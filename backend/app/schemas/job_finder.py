from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.job import JobRead


class JobFinderSourceStatus(BaseModel):
    source_type: str
    label: str
    implemented: bool
    configured: bool
    manual_only: bool = False
    notes: str


class JobFinderStatusResponse(BaseModel):
    stage: str
    message: str
    sources: list[JobFinderSourceStatus]
    safety_rules: list[str]


class JobFinderQueryRequest(BaseModel):
    use_ai: bool = False
    user_enabled: bool = False
    user_triggered: bool = True


class JobFinderQueryResponse(BaseModel):
    search_profile: dict[str, Any] = Field(default_factory=dict)
    queries: list[str] = Field(default_factory=list)
    default_queries: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    api_used: bool = False
    provider: str | None = None
    api_action: str | None = None
    model: str | None = None
    blocked_reason: str | None = None


class JobFinderRunRequest(BaseModel):
    source_types: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    location: str = "Bay Area"
    source_urls: list[str] = Field(default_factory=list)
    manual_links: list[str] = Field(default_factory=list)
    max_jobs: int = Field(default=50, ge=1, le=200)
    use_ai_queries: bool = False
    auto_verify: bool = False
    auto_score: bool = False
    match_mode: str = Field(default="balanced", pattern="^(strict|balanced|broad)$")
    target_experience_levels: list[str] = Field(default_factory=lambda: ["new_grad_entry", "early_career", "unknown"])
    excluded_experience_levels: list[str] = Field(default_factory=lambda: ["senior"])
    degree_filter: dict[str, bool] = Field(
        default_factory=lambda: {
            "allow_no_degree": True,
            "allow_bachelors": True,
            "allow_masters_preferred": True,
            "allow_masters_required": False,
            "allow_phd_preferred": True,
            "allow_phd_required": False,
            "allow_unknown": True,
        }
    )
    allow_unknown_location: bool = True
    location_filter: dict[str, bool] = Field(
        default_factory=lambda: {
            "allow_bay_area": True,
            "allow_remote_us": True,
            "allow_unknown": True,
            "allow_non_bay_area_california": False,
            "allow_other_us": False,
            "allow_international": False,
        }
    )

    @field_validator("source_types", "queries", "source_urls", "manual_links", "target_experience_levels", "excluded_experience_levels", mode="before")
    @classmethod
    def normalize_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        return [str(item).strip() for item in value if str(item).strip()]


class JobSourceImportFileRequest(BaseModel):
    format: str = Field(pattern="^(csv|json)$")
    path: str | None = None
    skip_existing: bool = True
    replace_existing: bool = False


class JobSourceImportFileResponse(BaseModel):
    success: bool
    summary: dict[str, Any] = Field(default_factory=dict)


class JobSourceSummaryResponse(BaseModel):
    total_sources: int
    enabled_sources: int
    valid_sources: int
    partial_sources: int = 0
    by_ats_type: dict[str, int] = Field(default_factory=dict)
    last_imported_at: datetime | None = None
    last_discovery_run_at: datetime | None = None


class JobSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    base_url: str
    normalized_url: str = ""
    ats_type: str | None = None
    enabled: bool
    status: str | None = None
    jobs_found: int | None = None
    last_error: str | None = None
    discovery_method: str | None = None
    warnings: list[str] = Field(default_factory=list)
    imported_at: datetime | None = None
    last_checked_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("warnings", mode="before")
    @classmethod
    def warnings_default(cls, value: Any) -> list[str]:
        return list(value or [])


class JobSourceUpdateRequest(BaseModel):
    enabled: bool | None = None
    company: str | None = None
    name: str | None = None
    notes: str | None = None


class SavedSourceSearchRequest(BaseModel):
    ats_types: list[str] = Field(default_factory=list)
    source_ids: list[int] = Field(default_factory=list)
    use_enabled_sources: bool = True
    limit: int = Field(default=5, ge=1, le=50)
    offset: int = Field(default=0, ge=0)
    location: str = "Bay Area"
    queries: list[str] = Field(default_factory=list)
    exclude_duplicates: bool = True
    exclude_imported: bool = True
    max_sources: int = Field(default=25, ge=1, le=200)
    match_mode: str = Field(default="balanced", pattern="^(strict|balanced|broad)$")
    target_experience_levels: list[str] = Field(default_factory=lambda: ["new_grad_entry", "early_career", "unknown"])
    excluded_experience_levels: list[str] = Field(default_factory=lambda: ["senior"])
    degree_filter: dict[str, bool] = Field(
        default_factory=lambda: {
            "allow_no_degree": True,
            "allow_bachelors": True,
            "allow_masters_preferred": True,
            "allow_masters_required": False,
            "allow_phd_preferred": True,
            "allow_phd_required": False,
            "allow_unknown": True,
        }
    )
    allow_unknown_location: bool = True
    location_filter: dict[str, bool] = Field(
        default_factory=lambda: {
            "allow_bay_area": True,
            "allow_remote_us": True,
            "allow_unknown": True,
            "allow_non_bay_area_california": False,
            "allow_other_us": False,
            "allow_international": False,
        }
    )

    @field_validator("ats_types", "queries", "target_experience_levels", "excluded_experience_levels", mode="before")
    @classmethod
    def normalize_string_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        return [str(item).strip() for item in value if str(item).strip()]


class SavedSourceResult(BaseModel):
    source_id: int | None = None
    company: str | None = None
    ats_type: str
    base_url: str
    status: str
    jobs_fetched: int = 0
    matches: int = 0
    candidates_saved: int = 0
    good_match: int = 0
    weak_match: int = 0
    excluded: int = 0
    duplicate: int = 0
    duplicates: int = 0
    skipped_incomplete: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class JobCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    discovery_run_id: int
    source_type: str
    source_name: str | None = None
    company: str
    title: str
    location: str
    url: str
    description_snippet: str | None = None
    job_description: str | None = None
    role_category: str | None = None
    experience_level: str | None = None
    seniority_level: str | None = None
    level_confidence: float | None = None
    location_fit: str | None = None
    remote_status: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    years_experience_min: int | None = None
    years_experience_max: int | None = None
    experience_requirement_text: str | None = None
    experience_requirement_strength: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    education_requirement: str | None = None
    degree_level: str | None = None
    degree_requirement_strength: str | None = None
    masters_required: bool = False
    phd_required: bool = False
    bachelors_required: bool = False
    degree_requirement_text: str | None = None
    metadata_confidence: float | None = None
    missing_fields: list[str] = Field(default_factory=list)
    posted_date: date | None = None
    discovered_at: datetime
    relevance_score: float
    filter_status: str
    filter_reasons: list[str] = Field(default_factory=list)
    duplicate_key: str
    duplicate_of_job_id: int | None = None
    imported_job_id: int | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator("required_skills", "preferred_skills", "filter_reasons", "missing_fields", mode="before")
    @classmethod
    def list_default(cls, value: Any) -> list[str]:
        return list(value or [])

    @field_validator("raw_data", mode="before")
    @classmethod
    def dict_default(cls, value: Any) -> dict[str, Any]:
        return dict(value or {})

    @model_validator(mode="after")
    def hydrate_requirement_fields(self) -> "JobCandidateRead":
        normalizer = self.raw_data.get("normalizer") if isinstance(self.raw_data, dict) else {}
        normalizer = normalizer if isinstance(normalizer, dict) else {}
        level = normalizer.get("level") if isinstance(normalizer.get("level"), dict) else {}
        degree = normalizer.get("degree") if isinstance(normalizer.get("degree"), dict) else {}

        self.experience_requirement_text = self.experience_requirement_text or level.get("years_text") or None
        self.experience_requirement_strength = self.experience_requirement_strength or level.get("requirement_strength") or None
        self.degree_level = self.degree_level or degree.get("degree_level") or None
        self.degree_requirement_strength = self.degree_requirement_strength or degree.get("degree_requirement_strength") or None
        self.masters_required = bool(self.masters_required or degree.get("masters_required"))
        self.phd_required = bool(self.phd_required or degree.get("phd_required"))
        self.bachelors_required = bool(self.bachelors_required or degree.get("bachelors_required"))
        self.degree_requirement_text = self.degree_requirement_text or degree.get("degree_text") or None
        return self


class RunCandidatePageResponse(BaseModel):
    success: bool = True
    run_id: int
    limit: int
    offset: int
    next_offset: int | None = None
    has_more: bool
    total_matches: int
    candidates: list[JobCandidateRead] = Field(default_factory=list)


class SavedSourceSearchResponse(RunCandidatePageResponse):
    summary: dict[str, int] = Field(default_factory=dict)
    source_results: list[SavedSourceResult] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class JobFinderSourceResult(BaseModel):
    source_url: str
    source_type: str
    status: str
    found: int = 0
    jobs_fetched: int = 0
    saved_candidates: int = 0
    candidates_saved: int = 0
    good_match: int = 0
    weak_match: int = 0
    excluded: int = 0
    duplicate: int = 0
    duplicates: int = 0
    skipped_incomplete: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class JobDiscoveryRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    query: str
    location: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    total_found: int
    total_candidates: int
    total_imported: int
    errors: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator("errors", mode="before")
    @classmethod
    def errors_default(cls, value: Any) -> list[str]:
        return list(value or [])

    @field_validator("metadata_json", mode="before")
    @classmethod
    def metadata_default(cls, value: Any) -> dict[str, Any]:
        return dict(value or {})


class JobDiscoveryRunDetail(JobDiscoveryRunRead):
    candidates: list[JobCandidateRead] = Field(default_factory=list)


class JobFinderRunResponse(BaseModel):
    run: JobDiscoveryRunRead
    candidates: list[JobCandidateRead]
    summary: dict[str, int] = Field(default_factory=dict)
    source_results: list[JobFinderSourceResult] = Field(default_factory=list)
    message: str = ""
    errors: list[str] = Field(default_factory=list)


class JobCandidateImportSelectedRequest(BaseModel):
    candidate_ids: list[int]
    auto_verify: bool = False
    auto_score: bool = False


class JobCandidateImportResponse(BaseModel):
    candidate: JobCandidateRead
    job: JobRead
    verified: bool = False
    scored: bool = False
    warnings: list[str] = Field(default_factory=list)


class JobCandidateImportSelectedResponse(BaseModel):
    imported_count: int
    skipped_count: int
    jobs: list[JobRead] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
