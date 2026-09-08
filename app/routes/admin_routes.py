"""
admin_routes.py
Admin-only endpoints: view/search/filter all complaints, update status,
add remarks, assign department, statistics, and analytics.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models, schemas
from app.auth import get_current_admin
from app.ai import inference

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/complaints", response_model=List[schemas.ComplaintOut])
def list_all_complaints(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
):
    query = db.query(models.Complaint)

    if category:
        query = query.filter(models.Complaint.category == category)
    if priority:
        query = query.filter(models.Complaint.priority == priority)
    if status_filter:
        query = query.filter(models.Complaint.status == status_filter)
    if search:
        search = search.strip()[:200]
        like_pattern = f"%{search}%"
        query = query.filter(
            (models.Complaint.ticket_id.ilike(like_pattern))
            | (models.Complaint.complaint_text.ilike(like_pattern))
        )

    complaints = query.order_by(models.Complaint.created_at.desc()).all()
    return [schemas.ComplaintOut.model_validate(c) for c in complaints]


@router.get("/complaints/{ticket_id}", response_model=schemas.ComplaintOut)
def get_complaint_detail(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    complaint = db.query(models.Complaint).filter(models.Complaint.ticket_id == ticket_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return schemas.ComplaintOut.model_validate(complaint)


@router.put("/complaints/{ticket_id}/status", response_model=schemas.ComplaintOut)
def update_status(
    ticket_id: str,
    payload: schemas.ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    complaint = db.query(models.Complaint).filter(models.Complaint.ticket_id == ticket_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    complaint.status = payload.status
    db.commit()
    db.refresh(complaint)
    return schemas.ComplaintOut.model_validate(complaint)


@router.put("/complaints/{ticket_id}/department", response_model=schemas.ComplaintOut)
def update_department(
    ticket_id: str,
    payload: schemas.ComplaintDepartmentUpdate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    complaint = db.query(models.Complaint).filter(models.Complaint.ticket_id == ticket_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    complaint.department = payload.department
    db.commit()
    db.refresh(complaint)
    return schemas.ComplaintOut.model_validate(complaint)


@router.put("/complaints/{ticket_id}/remark", response_model=schemas.ComplaintOut)
def add_remark(
    ticket_id: str,
    payload: schemas.ComplaintRemarkUpdate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    complaint = db.query(models.Complaint).filter(models.Complaint.ticket_id == ticket_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    complaint.admin_remark = payload.admin_remark
    db.commit()
    db.refresh(complaint)
    return schemas.ComplaintOut.model_validate(complaint)


@router.get("/stats", response_model=schemas.AdminStats)
def get_admin_stats(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    total = db.query(func.count(models.Complaint.id)).scalar() or 0
    pending = db.query(func.count(models.Complaint.id)).filter(models.Complaint.status == "Pending").scalar() or 0
    in_progress = db.query(func.count(models.Complaint.id)).filter(models.Complaint.status == "In Progress").scalar() or 0
    resolved = db.query(func.count(models.Complaint.id)).filter(models.Complaint.status == "Resolved").scalar() or 0
    rejected = db.query(func.count(models.Complaint.id)).filter(models.Complaint.status == "Rejected").scalar() or 0
    high_priority = db.query(func.count(models.Complaint.id)).filter(models.Complaint.priority == "High").scalar() or 0
    critical_priority = db.query(func.count(models.Complaint.id)).filter(models.Complaint.priority == "Critical").scalar() or 0

    return schemas.AdminStats(
        total=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        rejected=rejected,
        high_priority=high_priority,
        critical_priority=critical_priority,
    )


@router.get("/analytics", response_model=schemas.AnalyticsResponse)
def get_analytics(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    category_rows = (
        db.query(models.Complaint.category, func.count(models.Complaint.id))
        .group_by(models.Complaint.category)
        .all()
    )
    priority_rows = (
        db.query(models.Complaint.priority, func.count(models.Complaint.id))
        .group_by(models.Complaint.priority)
        .all()
    )
    status_rows = (
        db.query(models.Complaint.status, func.count(models.Complaint.id))
        .group_by(models.Complaint.status)
        .all()
    )
    sentiment_rows = (
        db.query(models.Complaint.sentiment, func.count(models.Complaint.id))
        .group_by(models.Complaint.sentiment)
        .all()
    )

    avg_rating = db.query(func.avg(models.Feedback.rating)).scalar()
    avg_rating = round(float(avg_rating), 2) if avg_rating else 0.0

    metrics = inference.get_model_metrics()

    return schemas.AnalyticsResponse(
        category_distribution=[schemas.CategoryCount(category=c, count=n) for c, n in category_rows],
        priority_distribution=[schemas.PriorityCount(priority=p, count=n) for p, n in priority_rows],
        status_distribution=[schemas.StatusCount(status=s, count=n) for s, n in status_rows],
        sentiment_distribution=[{"sentiment": s, "count": n} for s, n in sentiment_rows],
        avg_feedback_rating=avg_rating,
        model_metrics=metrics,
    )


@router.get("/feedback", response_model=List[schemas.FeedbackOut])
def list_all_feedback(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    feedback = db.query(models.Feedback).order_by(models.Feedback.created_at.desc()).all()
    return [schemas.FeedbackOut.model_validate(f) for f in feedback]
