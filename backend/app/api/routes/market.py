from fastapi import APIRouter

from app.services.market.analytics import get_market_summary_placeholder

router = APIRouter()


@router.get("/summary")
def market_summary() -> dict:
    return get_market_summary_placeholder()

