from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "careeragent-backend",
        "stage": "Stage 6 - Application Packet Generation",
    }
