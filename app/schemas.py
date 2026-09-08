"""
schemas.py
Pydantic models used for request validation and response serialization.
"""

import html
import re
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, field_validator, ConfigDict


def sanitize_text(value: str) -> str:
    """
    Neutralizes potentially dangerous input (script tags, HTML) while
    preserving normal punctuation such as apostrophes in names like
    O'Reilly. We HTML-escape the text so it can never be interpreted
    as executable markup when rendered back in templates.
    """
    if value is None:
        return value
    value = value.strip()
    # Strip <script>...</script> blocks entirely (defense in depth on top
    # of Jinja2's autoescaping, which already prevents XSS on render).
    value = re.sub(r"<\s*script.*?>.*?<\s*/\s*script\s*>", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = html.escape(value)
    return value


# ---------------------------------------------------------------------------
# User / Auth Schemas
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "student"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = sanitize_text(v)
        if not v or len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if len(v) > 150:
            raise ValueError("Name is too long (max 150 characters)")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not v or len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        if len(v) > 128:
            raise ValueError("Password is too long (max 128 characters)")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("student", "admin"):
            return "student"
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Complaint Schemas
# ---------------------------------------------------------------------------

class ComplaintAnalyzeRequest(BaseModel):
    complaint_text: str

    @field_validator("complaint_text")
    @classmethod
    def validate_text(cls, v):
        if v is None:
            raise ValueError("Complaint text cannot be empty")
        v = v.strip()
        if len(v) == 0:
            raise ValueError("Complaint text cannot be empty")
        if len(v) < 5:
            raise ValueError("Complaint text is too short. Please describe your issue in more detail.")
        if len(v) > 3000:
            raise ValueError("Complaint text is too long (max 3000 characters)")
        return sanitize_text(v)


class ComplaintCreate(BaseModel):
    complaint_text: str

    @field_validator("complaint_text")
    @classmethod
    def validate_text(cls, v):
        if v is None or len(v.strip()) == 0:
            raise ValueError("Complaint text cannot be empty")
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Complaint text is too short. Please describe your issue in more detail.")
        if len(v) > 3000:
            raise ValueError("Complaint text is too long (max 3000 characters)")
        return sanitize_text(v)


class ComplaintAnalysisResult(BaseModel):
    category: str
    priority: str
    department: str
    sentiment: str
    confidence: float
    is_duplicate: bool
    duplicate_of: Optional[str] = None
    similarity_score: float = 0.0


class ComplaintOut(BaseModel):
    id: int
    ticket_id: str
    user_id: int
    complaint_text: str
    category: str
    priority: str
    department: str
    sentiment: str
    confidence: float
    status: str
    admin_remark: Optional[str] = ""
    is_duplicate: int = 0
    duplicate_of: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"Pending", "In Progress", "Resolved", "Rejected"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class ComplaintDepartmentUpdate(BaseModel):
    department: str

    @field_validator("department")
    @classmethod
    def validate_department(cls, v):
        v = sanitize_text(v)
        if not v or len(v) > 60:
            raise ValueError("Invalid department name")
        return v


class ComplaintRemarkUpdate(BaseModel):
    admin_remark: str

    @field_validator("admin_remark")
    @classmethod
    def validate_remark(cls, v):
        v = sanitize_text(v or "")
        if len(v) > 1000:
            raise ValueError("Remark is too long (max 1000 characters)")
        return v


# ---------------------------------------------------------------------------
# Feedback Schemas
# ---------------------------------------------------------------------------

class FeedbackCreate(BaseModel):
    rating: int
    comment: Optional[str] = ""

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v):
        v = sanitize_text(v or "")
        if len(v) > 1000:
            raise ValueError("Comment is too long (max 1000 characters)")
        return v


class FeedbackOut(BaseModel):
    id: int
    complaint_id: int
    rating: int
    comment: Optional[str] = ""
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Admin / Analytics Schemas
# ---------------------------------------------------------------------------

class AdminStats(BaseModel):
    total: int
    pending: int
    in_progress: int
    resolved: int
    rejected: int
    high_priority: int
    critical_priority: int


class CategoryCount(BaseModel):
    category: str
    count: int


class PriorityCount(BaseModel):
    priority: str
    count: int


class StatusCount(BaseModel):
    status: str
    count: int


class ModelMetrics(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: List[List[int]]
    labels: List[str]


class AnalyticsResponse(BaseModel):
    category_distribution: List[CategoryCount]
    priority_distribution: List[PriorityCount]
    status_distribution: List[StatusCount]
    sentiment_distribution: List[dict]
    avg_feedback_rating: float
    model_metrics: Optional[dict] = None
