"""Pydantic-схемы запросов/ответов API Evergreen (контракт фронта и бэка)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---- Auth ----
class RegisterCompanyIn(BaseModel):
    company_name: str
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9\-]{1,62}$")
    owner_email: str
    owner_password: str = Field(min_length=6)
    owner_name: str = ""


class LoginIn(BaseModel):
    slug: str
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    company_id: str


class MeOut(BaseModel):
    user_id: str
    company_id: str
    role: str
    point_id: Optional[str] = None


class CreateUserIn(BaseModel):
    email: str
    password: str = Field(min_length=6)
    role: str
    full_name: str = ""
    point_id: Optional[str] = None


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    full_name: str = ""
    point_id: Optional[str] = None


# ---- Documents (M1) ----
class IngestTextIn(BaseModel):
    title: str
    content: str
    category: str = ""
    publish: bool = True
    # Аудитория стандарта (M1.5). Пусто/None → виден всем ролям/точкам.
    audience_roles: Optional[List[str]] = None
    point_id: Optional[str] = None


class NewVersionIn(BaseModel):
    content: str


class StatusIn(BaseModel):
    status: str


class AudienceIn(BaseModel):
    """Назначить аудиторию документа (M1.5)."""
    audience_roles: Optional[List[str]] = None
    point_id: Optional[str] = None


class DocumentOut(BaseModel):
    id: str
    title: str
    category: str
    status: str
    current_version_id: Optional[str] = None
    audience_roles: List[str] = []
    point_id: Optional[str] = None


# ---- Chat (M2) ----
class ChatIn(BaseModel):
    question: str


class SourceOut(BaseModel):
    document_id: str
    document_title: str
    score: float


class ChatOut(BaseModel):
    answer: str
    refused: bool
    sources: List[SourceOut] = []
    best_score: float = 0.0


# ---- Gaps ----
class GapOut(BaseModel):
    id: str
    question: str
    best_score: float
    resolved: bool


# ---- Onboarding / Quiz (M3) ----
class QuizGenIn(BaseModel):
    num_questions: int = Field(default=5, ge=1, le=20)


class QuizQuestionOut(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    source_quote: str = ""


class QuizOut(BaseModel):
    document_id: str
    questions: List[QuizQuestionOut]


class GradeIn(BaseModel):
    quiz: List[QuizQuestionOut]
    answers: List[int]


class GradeDetailOut(BaseModel):
    question: str
    given_index: Optional[int] = None
    correct_index: int
    is_correct: bool
    source_quote: str = ""


class GradeOut(BaseModel):
    total: int
    correct: int
    score: float
    passed: bool
    details: List[GradeDetailOut]


# ---- Tracks / Onboarding progress (M3) ----
class TrackIn(BaseModel):
    title: str
    description: str = ""


class TrackOut(BaseModel):
    id: str
    title: str
    description: str = ""
    status: str


class TrackStepIn(BaseModel):
    document_id: str
    title: str = ""
    require_quiz: bool = True
    pass_score: float = Field(default=0.8, ge=0.0, le=1.0)
    num_questions: int = Field(default=5, ge=1, le=20)


class TrackStepOut(BaseModel):
    id: str
    document_id: str
    ordinal: int
    title: str = ""
    require_quiz: bool
    pass_score: float
    num_questions: int


class TrackDetailOut(TrackOut):
    steps: List[TrackStepOut] = []


class TrackStatusIn(BaseModel):
    status: str


class EnrollIn(BaseModel):
    user_id: str


class EnrollmentOut(BaseModel):
    id: str
    track_id: str
    user_id: str
    status: str


class StepProgressOut(BaseModel):
    step_id: str
    status: str
    score: float
    attempts: int


class EnrollmentStepOut(TrackStepOut):
    progress: StepProgressOut


class MyEnrollmentOut(BaseModel):
    enrollment_id: str
    status: str
    track: TrackOut
    steps: List[EnrollmentStepOut] = []


class SubmitStepIn(BaseModel):
    quiz: Optional[List[QuizQuestionOut]] = None
    answers: Optional[List[int]] = None


class SubmitStepOut(BaseModel):
    step_status: str
    score: float
    attempts: int
    enrollment_status: str
    grade: Optional[GradeOut] = None


class TrackProgressRowOut(BaseModel):
    enrollment_id: str
    user_id: str
    status: str
    passed_steps: int
    total_steps: int
