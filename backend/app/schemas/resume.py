from typing import Literal

from pydantic import BaseModel


class ResumeSaveRequest(BaseModel):
    content: str


class ResumeDocumentResponse(BaseModel):
    source: Literal["private", "example"]
    path: str
    content: str
    message: str | None = None


class ResumeStatusResponse(BaseModel):
    private_resume_exists: bool
    example_resume_exists: bool
    active_source: Literal["private", "example", "missing"]
    private_resume_path: str
    example_resume_path: str
    latex_compiler_available: bool
    compiler_name: str | None = None
    last_compile_output_path: str | None = None
    github_safety_note: str


class ResumeCompileResponse(BaseModel):
    success: bool
    source: Literal["private", "example", "missing"]
    compiler: str | None = None
    input_path: str
    output_path: str | None = None
    message: str
    logs: str = ""

