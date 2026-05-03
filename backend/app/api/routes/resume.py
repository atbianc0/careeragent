from fastapi import APIRouter
from fastapi import HTTPException

from app.schemas.resume import (
    ResumeCompileResponse,
    ResumeDocumentResponse,
    ResumeSaveRequest,
    ResumeStatusResponse,
)
from app.services.resume import (
    compile_latex_resume,
    create_private_resume_from_example,
    get_resume_status,
    load_resume_document,
    save_resume_content,
)

router = APIRouter()


@router.get("", response_model=ResumeDocumentResponse)
def get_resume() -> ResumeDocumentResponse:
    try:
        return load_resume_document()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("", response_model=ResumeDocumentResponse)
def update_resume(payload: ResumeSaveRequest) -> ResumeDocumentResponse:
    return save_resume_content(payload.content)


@router.post("/create-private", response_model=ResumeDocumentResponse)
def create_private_resume() -> ResumeDocumentResponse:
    try:
        return create_private_resume_from_example()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/compile", response_model=ResumeCompileResponse)
def compile_resume() -> ResumeCompileResponse:
    return compile_latex_resume()


@router.get("/status", response_model=ResumeStatusResponse)
def resume_status() -> ResumeStatusResponse:
    return get_resume_status()

