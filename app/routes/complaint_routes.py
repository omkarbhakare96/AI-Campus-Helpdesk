"""
complaint_routes.py
Complaint analysis, creation, retrieval, and feedback endpoints.
Students can only access their own complaints.
"""

import random
import string
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, get_current_student
from app.ai import inference

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])


def generate_ticket_id(db: Session) -> str:
    """Generates a unique, human-readable ticket ID, e.g. TCK-2026-A1B2C3"""
    year = datetime.utcnow().year
    for _ in range(20):
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        ticket_id = f"TCK-{year}-{suffix}"
        exists = db.query(models.Complaint).filter(models.Complaint.ticket_id == ticket_id).first()
        if not exists:
            return ticket_id
    # Extremely unlikely fallback
    return f"TCK-{year}-{int(datetime.utcnow().timestamp())}"


@router.post("/analyze", response_model=schemas.ComplaintAnalysisResult)
def analyze_complaint(
    payload: schemas.ComplaintAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Runs the AI pipeline on the given text WITHOUT creating a ticket.
    Used by the 'Analyze before submission' feature on the frontend.
    """
    existing = db.query(models.Complaint.complaint_text, models.Complaint.ticket_id).all()
    existing_texts = [row[0] for row in existing]
    existing_ticket_ids = [row[1] for row in existing]

    try:
        result = inference.analyze_complaint(payload.complaint_text, existing_texts)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result["is_duplicate"] and result["duplicate_of"] is not None:
        idx = result["duplicate_of"]
        result["duplicate_of"] = existing_ticket_ids[idx] if 0 <= idx < len(existing_ticket_ids) else None

    return schemas.ComplaintAnalysisResult(**result)


@router.post("", response_model=schemas.ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(
    payload: schemas.ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_student),
):
    """Creates a new complaint ticket, running the full AI pipeline first."""
    existing = db.query(models.Complaint.complaint_text, models.Complaint.ticket_id).all()
    existing_texts = [row[0] for row in existing]
    existing_ticket_ids = [row[1] for row in existing]

    try:
        result = inference.analyze_complaint(payload.complaint_text, existing_texts)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    duplicate_of_ticket = None
    if result["is_duplicate"] and result["duplicate_of"] is not None:
        idx = result["duplicate_of"]
        if 0 <= idx < len(existing_ticket_ids):
            duplicate_of_ticket = existing_ticket_ids[idx]

    ticket_id = generate_ticket_id(db)

    complaint = models.Complaint(
        ticket_id=ticket_id,
        user_id=current_user.id,
        complaint_text=payload.complaint_text,
        category=result["category"],
        priority=result["priority"],
        department=result["department"],
        sentiment=result["sentiment"],
        confidence=result["confidence"],
        status="Pending",
        admin_remark="",
        is_duplicate=1 if result["is_duplicate"] else 0,
        duplicate_of=duplicate_of_ticket,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return schemas.ComplaintOut.model_validate(complaint)


@router.get("/mine", response_model=list[schemas.ComplaintOut])
def get_my_complaints(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_student),
):
    complaints = (
        db.query(models.Complaint)
        .filter(models.Complaint.user_id == current_user.id)
        .order_by(models.Complaint.created_at.desc())
        .all()
    )
    return [schemas.ComplaintOut.model_validate(c) for c in complaints]


@router.get("/ticket/{ticket_id}", response_model=schemas.ComplaintOut)
def get_complaint_by_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ticket_id = ticket_id.strip()
    if not ticket_id or len(ticket_id) > 40:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format.")

    complaint = db.query(models.Complaint).filter(models.Complaint.ticket_id == ticket_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint with this ticket ID was not found.")

    # Role-based access control: students can only view their own complaints
    if current_user.role == "student" and complaint.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this complaint.")

    return schemas.ComplaintOut.model_validate(complaint)


@router.post("/{ticket_id}/feedback", response_model=schemas.FeedbackOut, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    ticket_id: str,
    payload: schemas.FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_student),
):
    complaint = db.query(models.Complaint).filter(models.Complaint.ticket_id == ticket_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint with this ticket ID was not found.")

    if complaint.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only give feedback on your own complaints.")

    if complaint.status != "Resolved":
        raise HTTPException(status_code=400, detail="Feedback can only be submitted after the complaint is resolved.")

    existing_feedback = db.query(models.Feedback).filter(models.Feedback.complaint_id == complaint.id).first()
    if existing_feedback:
        raise HTTPException(status_code=400, detail="Feedback has already been submitted for this complaint.")

    feedback = models.Feedback(
        complaint_id=complaint.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return schemas.FeedbackOut.model_validate(feedback)


@router.get("/{ticket_id}/feedback", response_model=schemas.FeedbackOut)
def get_feedback(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    complaint = db.query(models.Complaint).filter(models.Complaint.ticket_id == ticket_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint with this ticket ID was not found.")

    if current_user.role == "student" and complaint.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this complaint's feedback.")

    feedback = db.query(models.Feedback).filter(models.Feedback.complaint_id == complaint.id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="No feedback has been submitted for this complaint yet.")

    return schemas.FeedbackOut.model_validate(feedback)
