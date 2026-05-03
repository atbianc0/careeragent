from fastapi import APIRouter

from app.services.browser_agent.autofill import launch_autofill_placeholder

router = APIRouter()


@router.get("/status")
def autofill_status() -> dict:
    return launch_autofill_placeholder()

