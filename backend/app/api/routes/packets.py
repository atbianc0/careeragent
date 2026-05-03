from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def packet_overview() -> dict:
    return {
        "status": "placeholder",
        "stage": "Stage 1",
        "message": "Application packet generation is scaffolded and will be implemented in later stages.",
        "planned_outputs": [
            "Tailored resume",
            "Cover letter",
            "Recruiter message",
            "Application question drafts",
            "Change summary",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

