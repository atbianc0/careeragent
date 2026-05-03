from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db.database import get_db
from app.models.application_packet import ApplicationPacket
from app.schemas.application_packet import (
    ApplicationPacketFileResponse,
    ApplicationPacketGenerateRequest,
    ApplicationPacketGenerateResponse,
    ApplicationPacketRead,
)
from app.services.generator import generate_application_packet

router = APIRouter()

PACKET_FILE_FIELD_MAP = {
    "cover_letter": "cover_letter_path",
    "recruiter_message": "recruiter_message_path",
    "application_questions": "application_questions_path",
    "application_notes": "application_notes_path",
    "change_summary": "change_summary_path",
    "tailored_resume_tex": "tailored_resume_tex_path",
    "job_summary": "job_summary_path",
    "packet_metadata": "packet_metadata_path",
}


def _packet_query(db: Session):
    return db.query(ApplicationPacket).options(joinedload(ApplicationPacket.job))


def _get_packet_or_404(db: Session, packet_id: int) -> ApplicationPacket:
    packet = _packet_query(db).filter(ApplicationPacket.id == packet_id).first()
    if packet is None:
        raise HTTPException(status_code=404, detail=f"Packet {packet_id} was not found.")
    return packet


def _resolve_packet_file_path(path_value: str) -> Path:
    raw_path = Path(path_value)
    path = raw_path.resolve() if raw_path.is_absolute() else (settings.project_root / raw_path).resolve()
    try:
        path.relative_to(settings.application_packets_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Packet file path is outside the private application packet directory.") from exc
    return path


def _format_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "markdown"
    if suffix == ".tex":
        return "latex"
    if suffix == ".json":
        return "json"
    return "text"


@router.post("/generate", response_model=ApplicationPacketGenerateResponse)
def generate_packet(
    payload: ApplicationPacketGenerateRequest,
    db: Session = Depends(get_db),
) -> ApplicationPacketGenerateResponse:
    try:
        result = generate_application_packet(db, payload.job_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if "was not found" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc

    packet = _get_packet_or_404(db, result["packet"].id)
    result["packet"] = packet
    return result


@router.get("", response_model=list[ApplicationPacketRead])
def list_packets(db: Session = Depends(get_db)) -> list[ApplicationPacketRead]:
    return (
        _packet_query(db)
        .order_by(
            ApplicationPacket.generated_at.desc().nullslast(),
            ApplicationPacket.created_at.desc(),
            ApplicationPacket.id.desc(),
        )
        .all()
    )


@router.get("/job/{job_id}", response_model=list[ApplicationPacketRead])
def list_packets_for_job(job_id: int, db: Session = Depends(get_db)) -> list[ApplicationPacketRead]:
    return (
        _packet_query(db)
        .filter(ApplicationPacket.job_id == job_id)
        .order_by(
            ApplicationPacket.generated_at.desc().nullslast(),
            ApplicationPacket.created_at.desc(),
            ApplicationPacket.id.desc(),
        )
        .all()
    )


@router.get("/{packet_id}/file", response_model=ApplicationPacketFileResponse)
def get_packet_file(
    packet_id: int,
    file_key: str = Query(..., description="Known packet file key"),
    db: Session = Depends(get_db),
) -> ApplicationPacketFileResponse:
    if file_key not in PACKET_FILE_FIELD_MAP:
        raise HTTPException(status_code=400, detail=f"Unsupported file key: {file_key}")

    packet = _get_packet_or_404(db, packet_id)
    path_value = getattr(packet, PACKET_FILE_FIELD_MAP[file_key])
    if not path_value:
        raise HTTPException(status_code=404, detail=f"File {file_key} is not available for packet {packet_id}.")

    path = _resolve_packet_file_path(path_value)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Stored file for {file_key} could not be found.")

    return ApplicationPacketFileResponse(
        packet_id=packet.id,
        file_key=file_key,
        path=path_value,
        content=path.read_text(encoding="utf-8"),
        format=_format_from_path(path),
    )


@router.get("/{packet_id}", response_model=ApplicationPacketRead)
def get_packet(packet_id: int, db: Session = Depends(get_db)) -> ApplicationPacketRead:
    return _get_packet_or_404(db, packet_id)
