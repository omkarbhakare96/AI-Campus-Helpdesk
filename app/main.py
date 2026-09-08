"""
main.py
Entry point for the AI-Based Campus Helpdesk FastAPI application.
Wires together the database, API routers, static files, and HTML templates.
"""

import os

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.database import Base, engine, SessionLocal
from app import models
from app.auth import hash_password
from app.routes import auth_routes, complaint_routes, admin_routes

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ---------------------------------------------------------------------------
# Create tables
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)


def seed_default_admin():
    """Creates a default admin account on first run for easy testing."""
    db = SessionLocal()
    try:
        existing_admin = db.query(models.User).filter(models.User.role == "admin").first()
        if not existing_admin:
            admin = models.User(
                name="System Administrator",
                email="admin@campus.edu",
                password_hash=hash_password("Admin@123"),
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("Seeded default admin account -> email: admin@campus.edu | password: Admin@123")
    finally:
        db.close()


seed_default_admin()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI-Based Campus Helpdesk",
    description="Intelligent Complaint Classification, Priority Prediction and Resolution Tracking System",
    version="1.0.0",
)
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "AI Campus Helpdesk API is running."
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ---------------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------------
app.include_router(auth_routes.router)
app.include_router(complaint_routes.router)
app.include_router(admin_routes.router)


# ---------------------------------------------------------------------------
# Global error handlers (never crash on bad input)
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(x) for x in err.get("loc", []))
        errors.append(f"{loc}: {err.get('msg')}")
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# HTML Page Routes (Jinja2 templates)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# HTML Page Routes (Jinja2 templates)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request}
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request}
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"request": request}
    )


@app.get("/dashboard", response_class=HTMLResponse)
def student_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="student_dashboard.html",
        context={"request": request}
    )


@app.get("/submit-complaint", response_class=HTMLResponse)
def submit_complaint_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="submit_complaint.html",
        context={"request": request}
    )


@app.get("/my-complaints", response_class=HTMLResponse)
def my_complaints_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="my_complaints.html",
        context={"request": request}
    )


@app.get("/complaint/{ticket_id}", response_class=HTMLResponse)
def complaint_detail_page(request: Request, ticket_id: str):
    return templates.TemplateResponse(
        request=request,
        name="complaint_details.html",
        context={
            "request": request,
            "ticket_id": ticket_id
        }
    )


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={"request": request}
    )


@app.get("/admin/analytics", response_class=HTMLResponse)
def admin_analytics_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context={"request": request}
    )


@app.get("/feedback/{ticket_id}", response_class=HTMLResponse)
def feedback_page(request: Request, ticket_id: str):
    return templates.TemplateResponse(
        request=request,
        name="feedback.html",
        context={
            "request": request,
            "ticket_id": ticket_id
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
