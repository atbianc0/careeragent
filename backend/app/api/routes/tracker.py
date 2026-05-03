from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def tracker_overview() -> dict:
    return {
        "status": "placeholder",
        "stage": "Stage 7",
        "message": "Application tracking views and event logging arrive in later stages.",
        "next_focus": [
            "Track saved and verified jobs",
            "Log packet generation and application actions",
            "Record manual review milestones",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
