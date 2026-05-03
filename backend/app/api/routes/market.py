from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.market.analytics import get_market_summary

router = APIRouter()


@router.get("/summary")
def market_summary(db: Session = Depends(get_db)) -> dict:
    return get_market_summary(db)
