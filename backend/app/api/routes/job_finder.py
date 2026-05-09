from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pathlib import Path

from app.db.database import get_db
from app.models.job_finder import JobCandidate, JobDiscoveryRun, JobSource
from app.schemas.job_finder import (
    JobCandidateImportResponse,
    JobCandidateImportSelectedRequest,
    JobCandidateImportSelectedResponse,
    JobCandidateRead,
    JobDiscoveryRunDetail,
    JobDiscoveryRunRead,
    JobFinderQueryRequest,
    JobFinderQueryResponse,
    JobFinderRunRequest,
    JobFinderRunResponse,
    JobSourceImportFileRequest,
    JobSourceImportFileResponse,
    JobSourceRead,
    JobSourceSummaryResponse,
    JobSourceUpdateRequest,
    RunCandidatePageResponse,
    SavedSourceSearchRequest,
    SavedSourceSearchResponse,
    JobFinderStatusResponse,
)
from app.services.job_finder import (
    generate_queries,
    get_run_candidate_page,
    get_run,
    import_candidate,
    job_finder_status,
    list_candidates,
    list_runs,
    run_discovery,
    search_saved_sources,
)
from app.services.job_finder.source_database_importer import (
    DEFAULT_SOURCE_CSV_PATH,
    DEFAULT_SOURCE_JSON_PATH,
    import_sources_to_db,
    load_sources_from_csv,
    load_sources_from_json,
)

router = APIRouter()
SOURCE_IMPORT_DIR = Path("job-database-script/outputs/source_discovery")
VALID_SOURCE_STATUSES = {"valid", "partial", "working", "ok"}


def _safe_source_import_path(path: str | None, format_name: str) -> Path:
    default_path = DEFAULT_SOURCE_CSV_PATH if format_name == "csv" else DEFAULT_SOURCE_JSON_PATH
    requested = Path(path or default_path)
    if not requested.is_absolute():
        requested = Path.cwd() / requested
    resolved = requested.resolve()
    allowed = (Path.cwd() / SOURCE_IMPORT_DIR).resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Source imports are only allowed from {SOURCE_IMPORT_DIR.as_posix()}.",
        ) from exc
    if resolved.suffix.lower() != f".{format_name}":
        raise HTTPException(status_code=400, detail=f"Import format is {format_name}, but file extension is {resolved.suffix}.")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Source import file was not found: {path or default_path}")
    return resolved


@router.get("/status", response_model=JobFinderStatusResponse)
def status() -> JobFinderStatusResponse:
    return JobFinderStatusResponse(**job_finder_status())


@router.post("/generate-queries", response_model=JobFinderQueryResponse)
def generate_job_finder_queries(payload: JobFinderQueryRequest) -> JobFinderQueryResponse:
    return JobFinderQueryResponse(**generate_queries(use_ai=payload.use_ai, provider=payload.provider))


@router.post("/run", response_model=JobFinderRunResponse)
def run_job_finder(payload: JobFinderRunRequest, db: Session = Depends(get_db)) -> JobFinderRunResponse:
    result = run_discovery(db, payload.model_dump())
    return JobFinderRunResponse(**result)


@router.post("/sources/import-file", response_model=JobSourceImportFileResponse)
def import_source_file(payload: JobSourceImportFileRequest, db: Session = Depends(get_db)) -> JobSourceImportFileResponse:
    safe_path = _safe_source_import_path(payload.path, payload.format)
    records = load_sources_from_csv(str(safe_path)) if payload.format == "csv" else load_sources_from_json(str(safe_path))
    summary = import_sources_to_db(records, db, skip_existing=payload.skip_existing, replace_existing=payload.replace_existing)
    return JobSourceImportFileResponse(success=True, summary=summary)


@router.get("/sources/summary", response_model=JobSourceSummaryResponse)
def source_summary(db: Session = Depends(get_db)) -> JobSourceSummaryResponse:
    sources = db.query(JobSource).all()
    by_ats_type: dict[str, int] = {}
    enabled_sources = 0
    valid_sources = 0
    partial_sources = 0
    last_imported_at = None
    for source in sources:
        ats_type = source.ats_type or source.source_type
        by_ats_type[ats_type] = by_ats_type.get(ats_type, 0) + 1
        if source.enabled:
            enabled_sources += 1
        source_status = (source.status or "").lower()
        if source_status in VALID_SOURCE_STATUSES:
            valid_sources += 1
        if source_status == "partial":
            partial_sources += 1
        if source.imported_at and (last_imported_at is None or source.imported_at > last_imported_at):
            last_imported_at = source.imported_at
    last_discovery_run = db.query(JobDiscoveryRun).order_by(JobDiscoveryRun.started_at.desc()).first()
    return JobSourceSummaryResponse(
        total_sources=len(sources),
        enabled_sources=enabled_sources,
        valid_sources=valid_sources,
        partial_sources=partial_sources,
        by_ats_type=by_ats_type,
        last_imported_at=last_imported_at,
        last_discovery_run_at=last_discovery_run.started_at if last_discovery_run else None,
    )


@router.get("/sources", response_model=list[JobSourceRead])
def saved_sources(
    ats_type: str | None = None,
    enabled: bool | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[JobSourceRead]:
    query = db.query(JobSource)
    if ats_type:
        query = query.filter((JobSource.ats_type == ats_type) | (JobSource.source_type == ats_type))
    if enabled is not None:
        query = query.filter(JobSource.enabled.is_(enabled))
    if status:
        query = query.filter(JobSource.status == status)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter((JobSource.name.ilike(term)) | (JobSource.base_url.ilike(term)) | (JobSource.notes.ilike(term)))
    return query.order_by(JobSource.id.asc()).offset(offset).limit(limit).all()


@router.put("/sources/{source_id}", response_model=JobSourceRead)
def update_saved_source(source_id: int, payload: JobSourceUpdateRequest, db: Session = Depends(get_db)) -> JobSourceRead:
    source = db.query(JobSource).filter(JobSource.id == source_id).first()
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source {source_id} was not found.")
    if payload.enabled is not None:
        source.enabled = payload.enabled
    if payload.name is not None or payload.company is not None:
        source.name = (payload.name or payload.company or source.name).strip() or source.name
    if payload.notes is not None:
        source.notes = payload.notes
    db.commit()
    db.refresh(source)
    return source


@router.post("/sources/search-saved", response_model=SavedSourceSearchResponse)
def search_saved_job_sources(payload: SavedSourceSearchRequest, db: Session = Depends(get_db)) -> SavedSourceSearchResponse:
    result = search_saved_sources(db, payload.model_dump())
    return SavedSourceSearchResponse(**result)


@router.get("/runs", response_model=list[JobDiscoveryRunRead])
def job_finder_runs(db: Session = Depends(get_db)) -> list[JobDiscoveryRunRead]:
    return list_runs(db)


@router.get("/runs/{run_id}", response_model=JobDiscoveryRunDetail)
def job_finder_run(run_id: int, db: Session = Depends(get_db)) -> JobDiscoveryRunDetail:
    run = get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Discovery run {run_id} was not found.")
    return run


@router.get("/runs/{run_id}/candidates", response_model=RunCandidatePageResponse)
def job_finder_run_candidates(
    run_id: int,
    limit: int = Query(default=5, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> RunCandidatePageResponse:
    page = get_run_candidate_page(db, run_id, limit=limit, offset=offset)
    if page is None:
        raise HTTPException(status_code=404, detail=f"Discovery run {run_id} was not found.")
    return RunCandidatePageResponse(**page)


@router.get("/candidates", response_model=list[JobCandidateRead])
def job_finder_candidates(
    run_id: int | None = None,
    filter_status: str | None = None,
    source_type: str | None = None,
    search: str | None = None,
    min_relevance_score: float | None = Query(default=None, ge=0, le=100),
    db: Session = Depends(get_db),
) -> list[JobCandidateRead]:
    return list_candidates(
        db,
        run_id=run_id,
        filter_status=filter_status,
        source_type=source_type,
        search=search,
        min_relevance_score=min_relevance_score,
    )


@router.post("/candidates/import-selected", response_model=JobCandidateImportSelectedResponse)
def import_selected_candidates(
    payload: JobCandidateImportSelectedRequest,
    db: Session = Depends(get_db),
) -> JobCandidateImportSelectedResponse:
    jobs = []
    errors: list[str] = []
    for candidate_id in payload.candidate_ids:
        try:
            result = import_candidate(db, candidate_id, auto_verify=payload.auto_verify, auto_score=payload.auto_score)
            jobs.append(result["job"])
        except ValueError as exc:
            errors.append(str(exc))
    return JobCandidateImportSelectedResponse(
        imported_count=len(jobs),
        skipped_count=len(errors),
        jobs=jobs,
        errors=errors,
    )


@router.post("/candidates/{candidate_id}/import", response_model=JobCandidateImportResponse)
def import_one_candidate(
    candidate_id: int,
    auto_verify: bool = False,
    auto_score: bool = False,
    db: Session = Depends(get_db),
) -> JobCandidateImportResponse:
    try:
        result = import_candidate(db, candidate_id, auto_verify=auto_verify, auto_score=auto_score)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JobCandidateImportResponse(**result)


@router.delete("/candidates/{candidate_id}", response_model=JobCandidateRead)
def exclude_candidate(candidate_id: int, db: Session = Depends(get_db)) -> JobCandidateRead:
    candidate = db.query(JobCandidate).filter(JobCandidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} was not found.")
    candidate.filter_status = "excluded"
    candidate.filter_reasons = list(candidate.filter_reasons or []) + ["Manually excluded by user."]
    db.commit()
    db.refresh(candidate)
    return candidate
