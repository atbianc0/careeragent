from typing import Any

from pydantic import BaseModel


class ProfileResponse(BaseModel):
    personal: dict[str, Any]
    education: dict[str, Any]
    links: dict[str, Any]
    target_roles: list[str]
    skills: list[str]
    application_defaults: dict[str, Any]
    question_policy: dict[str, Any]
    writing_style: dict[str, Any]

