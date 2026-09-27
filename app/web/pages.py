"""HTML page routes (Jinja2)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from app.db.session import get_db
from app.models.tenant import Tenant
from app.services import service_service
from app.web.templates import templates

router = APIRouter(tags=["web"])

# Paths that must never be treated as tenant slugs
RESERVED_SLUGS = {
    "docs", "redoc", "openapi.json", "static", "health",
    "auth", "tenants", "services", "bookings", "orders",
    "payments", "rewards", "referrals", "notifications",
    "analytics", "platform", "businesses", "about", "contact",
    "favicon.ico",
}


def _active_tenants(db: DBSession) -> list[Tenant]:
    return (
        db.query(Tenant)
        .filter(Tenant.status == "active", Tenant.deleted_at.is_(None))
        .order_by(Tenant.name)
        .all()
    )


def _get_tenant_by_slug(db: DBSession, slug: str) -> Tenant | None:
    return (
        db.query(Tenant)
        .filter(
            Tenant.slug == slug,
            Tenant.status == "active",
            Tenant.deleted_at.is_(None),
        )
        .one_or_none()
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


@router.get("/about", response_class=HTMLResponse)
def about(request: Request) -> HTMLResponse:
    """About page."""
    return templates.TemplateResponse(request, "pages/about.html", {"tenant": None})


@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request) -> HTMLResponse:
    """Contact page."""
    return templates.TemplateResponse(request, "pages/contact.html", {"tenant": None})


# ---------- Tenant-scoped pages ----------
# These come last so a slug can never shadow a system route.


@router.get("/{tenant_slug}/", response_class=HTMLResponse)
def tenant_home(
    tenant_slug: str,
    request: Request,
    db: DBSession = Depends(get_db),
) -> HTMLResponse:
    """Tenant landing page (brand-specific)."""
    if tenant_slug in RESERVED_SLUGS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    tenant = _get_tenant_by_slug(db, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    services, _total = service_service.list_services(
        db, tenant_id=tenant.id, status_filter="active", page=1, limit=100
    )
    return templates.TemplateResponse(
        request,
        "pages/tenant_home.html",
        {
            "tenant": tenant,
            "services": services,
        },
    )
