"""HTML page routes (Jinja2)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session as DBSession

from app.db.session import get_db
from app.models.tenant import Tenant

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["web"])


def _active_tenants(db: DBSession) -> list[Tenant]:
    return (
        db.query(Tenant)
        .filter(Tenant.status == "active", Tenant.deleted_at.is_(None))
        .order_by(Tenant.name)
        .all()
    )


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: DBSession = Depends(get_db)) -> HTMLResponse:
    """Platform-X landing page."""
    return templates.TemplateResponse(
        request,
        "pages/home.html",
        {
            "tenant": None,
            "businesses": _active_tenants(db),
        },
    )


@router.get("/businesses", response_class=HTMLResponse)
def businesses(request: Request, db: DBSession = Depends(get_db)) -> HTMLResponse:
    """List of businesses on the platform."""
    return templates.TemplateResponse(
        request,
        "pages/businesses.html",
        {
            "tenant": None,
            "businesses": _active_tenants(db),
        },
    )
