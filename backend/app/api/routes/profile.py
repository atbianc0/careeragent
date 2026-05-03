from fastapi import APIRouter
from fastapi import HTTPException

from app.schemas.profile import CareerProfile, ProfileDocumentResponse, ProfileStatusResponse
from app.services.profile import (
    create_private_profile_from_example,
    get_profile_status,
    load_profile_document,
    save_profile_data,
)

router = APIRouter()


@router.get("", response_model=ProfileDocumentResponse)
def get_profile() -> ProfileDocumentResponse:
    try:
        return load_profile_document()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("", response_model=ProfileDocumentResponse)
def update_profile(payload: CareerProfile) -> ProfileDocumentResponse:
    return save_profile_data(payload.model_dump(mode="json"))


@router.post("/create-private", response_model=ProfileDocumentResponse)
def create_private_profile() -> ProfileDocumentResponse:
    try:
        return create_private_profile_from_example()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/status", response_model=ProfileStatusResponse)
def profile_status() -> ProfileStatusResponse:
    return get_profile_status()
