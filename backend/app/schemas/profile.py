from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class PersonalSection(FlexibleModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""


class EducationSection(FlexibleModel):
    school: str = ""
    degree: str = ""
    graduation: str = ""


class LinksSection(FlexibleModel):
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""


class ApplicationDefaultsSection(FlexibleModel):
    work_authorized_us: bool = False
    need_sponsorship_now: bool = False
    need_sponsorship_future: bool = False
    willing_to_relocate: bool = False
    preferred_locations: list[str] = Field(default_factory=list)


class QuestionPolicySection(FlexibleModel):
    answer_work_authorization: bool = False
    answer_sponsorship: bool = False
    answer_relocation: bool = False
    answer_salary_expectation: str = ""
    answer_demographic_questions: str = ""
    never_lie: bool = True


class WritingStyleSection(FlexibleModel):
    tone: str = ""
    avoid: list[str] = Field(default_factory=list)


class CareerProfile(FlexibleModel):
    personal: PersonalSection = Field(default_factory=PersonalSection)
    education: EducationSection = Field(default_factory=EducationSection)
    links: LinksSection = Field(default_factory=LinksSection)
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    application_defaults: ApplicationDefaultsSection = Field(default_factory=ApplicationDefaultsSection)
    question_policy: QuestionPolicySection = Field(default_factory=QuestionPolicySection)
    writing_style: WritingStyleSection = Field(default_factory=WritingStyleSection)


class ProfileDocumentResponse(BaseModel):
    source: Literal["private", "example"]
    path: str
    profile: CareerProfile
    message: str | None = None


class ProfileStatusResponse(BaseModel):
    private_profile_exists: bool
    example_profile_exists: bool
    active_source: Literal["private", "example", "missing"]
    private_profile_path: str
    example_profile_path: str
    github_safety_note: str
