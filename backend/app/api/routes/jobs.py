from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.db.database import get_db
from app.models.job import Job
from app.schemas.job import JobRead

router = APIRouter()


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[Job]:
    return db.query(Job).order_by(Job.overall_priority_score.desc(), Job.id.asc()).all()

