"""HTML page routes (Jinja2)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from app.core.i18n import resolve_language, translate
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services import service_service
from app.web.templates import templates

# ---------- Leaderboard badges helper (Phase 29) ----------


def _badges_by_tenant(db) -> dict[str, str]:
    """Return {tenant_id: 'gold'|'silver'|'bronze'} for the current period.

    Only tenants ranked 1..3 in their category get a badge.
    Safe when no scores exist yet (returns {}).
    """
    try:
        from app.models.business_score import BusinessScore
        from app.services.scoring_engine import current_period

        ps, pe = current_period()
        rows = (
            db.query(BusinessScore)
            .filter(
                BusinessScore.period_start == ps,
                BusinessScore.period_end == pe,
                BusinessScore.rank_in_category.in_([1, 2, 3]),
            )
            .all()
        )
        mapping = {1: "gold", 2: "silver", 3: "bronze"}
        return {r.tenant_id: mapping[r.rank_in_category] for r in rows if r.rank_in_category in mapping}
    except Exception:
        return {}



router = APIRouter(tags=["web"])

# Paths that must never be treated as tenant slugs
RESERVED_SLUGS = {
    "docs", "redoc", "openapi.json", "static", "health",
    "auth", "tenants", "login", "register", "services", "bookings", "orders",
    "payments", "rewards", "referrals", "notifications",
    "analytics", "platform", "businesses", "about", "contact",
    "hotels", "restaurants", "travel", "entertainment", "partners", "docs", "admin", "roadmap", "forgot-password", "reset-password", "business",
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


def _counts_by_type(tenants: list[Tenant]) -> dict[str, int]:
    """Count active tenants by config.type."""
    counts: dict[str, int] = {}
    for t in tenants:
        if isinstance(t.config, dict):
            tp = str(t.config.get("type", "")).lower()
            if tp:
                counts[tp] = counts.get(tp, 0) + 1
    return counts


def _top_by_type(tenants: list[Tenant], ttype: str, n: int = 3) -> list[Tenant]:
    """Top N tenants of a given type, sorted by rating desc."""
    wanted = [t for t in tenants if isinstance(t.config, dict)
              and str(t.config.get("type", "")).lower() == ttype]
    return sorted(wanted, key=lambda t: t.config.get("rating", 0), reverse=True)[:n]


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: DBSession = Depends(get_db)) -> HTMLResponse:
    """Platform-X landing page."""
    _lang = resolve_language(request)
    tenants = _active_tenants(db)
    counts = _counts_by_type(tenants)

    featured = [
        {
            "eyebrow": translate("nav.hotels", _lang),
            "title": translate("home.featured_hotels", _lang),
            "label": translate("categories.hotels_title", _lang),
            "pill": "px-cat-hotels",
            "href": "/hotels",
            "count": counts.get("hotel", 0),
            "items": _top_by_type(tenants, "hotel", 3),
        },
        {
            "eyebrow": translate("nav.restaurants", _lang),
            "title": translate("home.featured_restaurants", _lang),
            "label": translate("categories.restaurants_title", _lang),
            "pill": "px-cat-restaurants",
            "href": "/restaurants",
            "count": counts.get("restaurant", 0),
            "items": _top_by_type(tenants, "restaurant", 3),
        },
        {
            "eyebrow": translate("nav.travel", _lang),
            "title": translate("home.featured_travel", _lang),
            "label": translate("categories.travel_title", _lang),
            "pill": "px-cat-travel",
            "href": "/travel",
            "count": counts.get("travel_agency", 0),
            "items": _top_by_type(tenants, "travel_agency", 3),
        },
        {
            "eyebrow": translate("nav.entertainment", _lang),
            "title": translate("home.featured_entertainment", _lang),
            "label": translate("categories.entertainment_title", _lang),
            "pill": "px-cat-entertainment",
            "href": "/entertainment",
            "count": counts.get("entertainment", 0),
            "items": _top_by_type(tenants, "entertainment", 3),
        },
    ]

    # Stats
    from app.models.service import Service as _Service
    total_services = db.query(_Service).filter(_Service.status == "active").count()
    cities = set()
    for t in tenants:
        if isinstance(t.config, dict):
            loc = t.config.get("location", "")
            if loc:
                cities.add(loc.split(",")[-1].strip())

    stats = {
        "businesses": len(tenants),
        "services": total_services,
        "categories": sum(1 for c in counts.values() if c > 0),
        "cities": len(cities) if cities else 1,
    }

    return templates.TemplateResponse(
        request,
        "pages/platform_home.html",
        {
            "tenant": None,
            "businesses": tenants,
            "counts": counts,
            "featured": featured,
            "stats": stats,
            "show_lang_switcher": True,
        },
    )


@router.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_page(request: Request) -> HTMLResponse:
    """Public leaderboard page (data loaded client-side from /leaderboard API)."""
    return templates.TemplateResponse(
        request,
        "pages/leaderboard.html",
        {
            "active_nav": "leaderboard",
        },
    )


@router.get("/businesses", response_class=HTMLResponse)
def businesses(request: Request, db: DBSession = Depends(get_db)) -> HTMLResponse:
    """List of businesses (kept for legacy links).

    Logged-in users coming from /login or /register are redirected to /account.
    """
    from fastapi.responses import RedirectResponse

    referer = request.headers.get("referer", "")
    if "/login" in referer or "/register" in referer:
        return RedirectResponse(url="/account", status_code=302)

    return templates.TemplateResponse(
        request,
        "pages/businesses.html",
        {
            "tenant": None,
            "badges": _badges_by_tenant(db),
            "businesses": _active_tenants(db),
        },
    )


@router.get("/login", response_class=HTMLResponse)
def auth_login_page(request: Request) -> HTMLResponse:
    """Login page."""
    return templates.TemplateResponse(request, "pages/login.html", {"tenant": None})


@router.get("/register", response_class=HTMLResponse)
def auth_register_page(request: Request) -> HTMLResponse:
    """Register page."""
    return templates.TemplateResponse(request, "pages/register.html", {"tenant": None})



# ---------- Category pages ----------


CATEGORIES = {
    "hotels": {
        "label": "Hotels",
        "icon": "🏨",
        "class": "px-cat-hotels",
        "types": ["hotel"],
        "description": "Boutique, luxury, and business stays across the platform.",
    },
    "restaurants": {
        "label": "Restaurants",
        "icon": "🍽",
        "class": "px-cat-restaurants",
        "types": ["restaurant"],
        "description": "Fine dining, casual, and authentic cuisine — reserve a table.",
    },
    "travel": {
        "label": "Travel",
        "icon": "✈️",
        "class": "px-cat-travel",
        "types": ["travel_agency", "agency"],
        "description": "Agencies, packages, and flights for every journey.",
    },
    "entertainment": {
        "label": "Entertainment",
        "icon": "🎢",
        "class": "px-cat-entertainment",
        "types": ["entertainment"],
        "description": "Attractions, activities, and experiences for all ages.",
    },
}


def _businesses_by_types(db: DBSession, types: list[str]) -> list[Tenant]:
    """Return active tenants whose config.type is in types."""
    all_tenants = _active_tenants(db)
    wanted = {t.lower() for t in types}
    return [
        t for t in all_tenants
        if isinstance(t.config, dict) and str(t.config.get("type", "")).lower() in wanted
    ]


def _render_category(
    request: Request, db: DBSession, slug: str
) -> HTMLResponse:
    _lang = resolve_language(request)
    meta = CATEGORIES[slug]
    businesses = _businesses_by_types(db, meta["types"])
    return templates.TemplateResponse(
        request,
        "pages/platform_category.html",
        {
            "tenant": None,
            "cat_label": translate(f"categories.{slug}_title", _lang),
            "cat_icon": meta["icon"],
            "cat_class": meta["class"],
            "cat_description": translate(f"categories.{slug}_sub", _lang),
            "businesses": businesses,
        },
    )


@router.get("/hotels", response_class=HTMLResponse)
def hotels_page(request: Request, db: DBSession = Depends(get_db)) -> HTMLResponse:
    return _render_category(request, db, "hotels")


@router.get("/restaurants", response_class=HTMLResponse)
def restaurants_page(request: Request, db: DBSession = Depends(get_db)) -> HTMLResponse:
    return _render_category(request, db, "restaurants")


@router.get("/travel", response_class=HTMLResponse)
def travel_page(request: Request, db: DBSession = Depends(get_db)) -> HTMLResponse:
    return _render_category(request, db, "travel")


@router.get("/entertainment", response_class=HTMLResponse)
def entertainment_page(request: Request, db: DBSession = Depends(get_db)) -> HTMLResponse:
    return _render_category(request, db, "entertainment")




@router.get("/account", response_class=HTMLResponse)
def account_page_platform(
    request: Request,
    db: DBSession = Depends(get_db),
) -> HTMLResponse:
    """Account dashboard (platform-level, no tenant slug)."""
    return templates.TemplateResponse(
        request,
        "pages/tenant_account.html",
        {"tenant": None},
    )




@router.get("/partners/apply", response_class=HTMLResponse)
def partners_apply_page(request: Request) -> HTMLResponse:
    """Public partner onboarding form."""
    return templates.TemplateResponse(
        request,
        "pages/partners_apply.html",
        {"tenant": None},
    )


@router.get("/partners/thanks", response_class=HTMLResponse)
def partners_thanks_page(request: Request) -> HTMLResponse:
    """Thank-you page after partner application submission."""
    return templates.TemplateResponse(
        request,
        "pages/partners_thanks.html",
        {"tenant": None},
    )




# ---------- Docs (PDF-ready documents) ----------

DOCS = {
    "overview": {
        "template": "docs/overview.html",
        "title": "Platform-X — Overview",
    },
}


@router.get("/docs/{doc_name}", response_class=HTMLResponse)
def docs_page(doc_name: str, request: Request) -> HTMLResponse:
    """Render a PDF-ready document by name."""
    if doc_name not in DOCS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    meta = DOCS[doc_name]
    return templates.TemplateResponse(
        request,
        meta["template"],
        {"tenant": None},
    )




# ---------- Admin Panel (HTML) ----------


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request) -> HTMLResponse:
    """Admin login page (no layout sidebar)."""
    return templates.TemplateResponse(
        request,
        "admin/admin_login.html",
        {"admin": None},
    )


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard_page(request: Request) -> HTMLResponse:
    """Admin dashboard (placeholder; JS loads real data)."""
    return templates.TemplateResponse(
        request,
        "admin/admin_dashboard.html",
        {"admin": True, "active_nav": "dashboard"},
    )




@router.get("/admin/tenants", response_class=HTMLResponse)
def admin_tenants_page(request: Request) -> HTMLResponse:
    """Admin tenants list."""
    return templates.TemplateResponse(
        request,
        "admin/admin_tenants.html",
        {"admin": True, "active_nav": "tenants"},
    )




@router.get("/admin/tenants/{tenant_id}", response_class=HTMLResponse)
def admin_tenant_detail_page(tenant_id: str, request: Request) -> HTMLResponse:
    """Admin tenant detail."""
    return templates.TemplateResponse(
        request,
        "admin/admin_tenant_detail.html",
        {"admin": True, "active_nav": "tenants", "tenant_id": tenant_id},
    )




@router.get("/admin/applications", response_class=HTMLResponse)
def admin_applications_page(request: Request) -> HTMLResponse:
    """Admin applications list."""
    return templates.TemplateResponse(
        request,
        "admin/admin_applications.html",
        {"admin": True, "active_nav": "applications"},
    )




@router.get("/admin/audit-logs", response_class=HTMLResponse)
def admin_audit_logs_page(request: Request) -> HTMLResponse:
    """Admin audit logs viewer."""
    return templates.TemplateResponse(
        request,
        "admin/admin_audit_logs.html",
        {"admin": True, "active_nav": "audit"},
    )




@router.get("/admin/subscriptions", response_class=HTMLResponse)
def admin_subscriptions_page(request: Request) -> HTMLResponse:
    """Admin subscriptions management."""
    return templates.TemplateResponse(
        request,
        "admin/admin_subscriptions.html",
        {"admin": True, "active_nav": "subscriptions"},
    )




@router.get("/roadmap", response_class=HTMLResponse)
def roadmap_page(request: Request) -> HTMLResponse:
    """Visual project roadmap for partners."""
    return templates.TemplateResponse(
        request,
        "pages/roadmap.html",
        {"tenant": None},
    )




@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request) -> HTMLResponse:
    """Forgot password page."""
    return templates.TemplateResponse(
        request, "pages/forgot_password.html", {"tenant": None}
    )


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request) -> HTMLResponse:
    """Reset password page (with ?token=...)."""
    return templates.TemplateResponse(
        request, "pages/reset_password.html", {"tenant": None}
    )




# ---------- Business Panel (HTML) ----------


@router.get("/business/login", response_class=HTMLResponse)
def business_login_page(request: Request) -> HTMLResponse:
    """Business owner login page."""
    return templates.TemplateResponse(
        request,
        "business/business_login.html",
        {"business_user": None},
    )


@router.get("/business/dashboard", response_class=HTMLResponse)
def business_dashboard_page(request: Request) -> HTMLResponse:
    """Business owner dashboard (data loaded via JS)."""
    # The token will be checked by JS; we just render shell.
    return templates.TemplateResponse(
        request,
        "business/business_dashboard.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},  # JS validates
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",  # JS will fetch actual
            "active_nav": "dashboard",
        },
    )




@router.get("/business/services", response_class=HTMLResponse)
def business_services_page(request: Request) -> HTMLResponse:
    """Business services management page."""
    return templates.TemplateResponse(
        request,
        "business/business_services.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "services",
        },
    )




@router.get("/business/bookings", response_class=HTMLResponse)
def business_bookings_page(request: Request) -> HTMLResponse:
    """Business bookings inbox."""
    return templates.TemplateResponse(
        request,
        "business/business_bookings.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "bookings",
        },
    )


@router.get("/business/customers", response_class=HTMLResponse)
def business_customers_page(request: Request) -> HTMLResponse:
    """Business customers list."""
    return templates.TemplateResponse(
        request,
        "business/business_customers.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "customers",
        },
    )


@router.get("/business/analytics", response_class=HTMLResponse)
def business_analytics_page(request: Request) -> HTMLResponse:
    """Business analytics page."""
    return templates.TemplateResponse(
        request,
        "business/business_analytics.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "analytics",
        },
    )




@router.get("/business/staff", response_class=HTMLResponse)
def business_staff_page(request: Request) -> HTMLResponse:
    """Business staff management."""
    return templates.TemplateResponse(
        request,
        "business/business_staff.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "staff",
        },
    )


@router.get("/business/settings", response_class=HTMLResponse)
def business_settings_page(request: Request) -> HTMLResponse:
    """Business settings (placeholder)."""
    return templates.TemplateResponse(
        request,
        "business/business_settings.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "settings",
        },
    )




@router.get("/business/ai", response_class=HTMLResponse)
def business_ai_page(request: Request) -> HTMLResponse:
    """Business AI assistant page."""
    return templates.TemplateResponse(
        request,
        "business/business_ai.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "ai",
        },
    )


@router.get("/business/score", response_class=HTMLResponse)
def business_score_page(request: Request) -> HTMLResponse:
    """My Score widget for the current business."""
    return templates.TemplateResponse(
        request,
        "business/business_score.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "score",
        },
    )


@router.get("/business/content", response_class=HTMLResponse)
def business_content_page(request: Request) -> HTMLResponse:
    """Content Studio for the current business."""
    return templates.TemplateResponse(
        request,
        "business/business_content.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "content",
        },
    )


@router.get("/business/marketing", response_class=HTMLResponse)
def business_marketing_page(request: Request) -> HTMLResponse:
    """Marketing Copilot page for the current business."""
    from app.services.ai import discount_suggester

    return templates.TemplateResponse(
        request,
        "business/business_marketing.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "marketing",
            "max_discount_pct": discount_suggester.MAX_DISCOUNT_PCT,
        },
    )


@router.get("/business/insights", response_class=HTMLResponse)
def business_insights_page(request: Request) -> HTMLResponse:
    """Insights page for the current business."""
    return templates.TemplateResponse(
        request,
        "business/business_insights.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "insights",
        },
    )


@router.get("/business/market", response_class=HTMLResponse)
def business_market_page(request: Request) -> HTMLResponse:
    """Market Insights page for the current business."""
    return templates.TemplateResponse(
        request,
        "business/business_market.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "market",
        },
    )


@router.get("/business/pricing", response_class=HTMLResponse)
def business_pricing_page(request: Request) -> HTMLResponse:
    """Pricing Rules builder for the current business."""
    return templates.TemplateResponse(
        request,
        "business/business_pricing.html",
        {
            "business_user": {"first_name": "Owner", "last_name": ""},
            "tenant_name": "Business",
            "tenant_slug": "trianon-hotel",
            "active_nav": "pricing",
        },
    )




@router.get("/account/ai", response_class=HTMLResponse)
def account_ai_page(request: Request) -> HTMLResponse:
    """User AI Assistant full page."""
    return templates.TemplateResponse(
        request,
        "pages/account_ai.html",
        {"tenant": None},
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


@router.get("/{tenant_slug}/account", response_class=HTMLResponse)
def tenant_account_page(
    tenant_slug: str,
    request: Request,
    db: DBSession = Depends(get_db),
) -> HTMLResponse:
    """User account dashboard for a tenant."""
    if tenant_slug in RESERVED_SLUGS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    tenant = _get_tenant_by_slug(db, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request,
        "pages/tenant_account.html",
        {"tenant": tenant},
    )




@router.get("/{tenant_slug}/pay/order", response_class=HTMLResponse)
def tenant_pay_order_page(
    tenant_slug: str,
    request: Request,
    order: str | None = None,
    db: DBSession = Depends(get_db),
) -> HTMLResponse:
    """Payment page for an order (restaurant)."""
    if tenant_slug in RESERVED_SLUGS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    tenant = _get_tenant_by_slug(db, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request,
        "pages/tenant_pay_order.html",
        {"tenant": tenant, "order_id": order or ""},
    )


@router.get("/{tenant_slug}/pay", response_class=HTMLResponse)
def tenant_pay_page(
    tenant_slug: str,
    request: Request,
    booking: str | None = None,
    db: DBSession = Depends(get_db),
) -> HTMLResponse:
    """Payment page for a booking."""
    if tenant_slug in RESERVED_SLUGS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    tenant = _get_tenant_by_slug(db, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request,
        "pages/tenant_pay.html",
        {
            "tenant": tenant,
            "booking_id": booking or "",
        },
    )




@router.get("/{tenant_slug}/order", response_class=HTMLResponse)
def tenant_order_page(
    tenant_slug: str,
    request: Request,
    db: DBSession = Depends(get_db),
) -> HTMLResponse:
    """Order food page (for restaurants and similar)."""
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
        "pages/tenant_order.html",
        {"tenant": tenant, "services": services},
    )


@router.get("/{tenant_slug}/book", response_class=HTMLResponse)
def tenant_book_page(
    tenant_slug: str,
    request: Request,
    service: str | None = None,
    db: DBSession = Depends(get_db),
) -> HTMLResponse:
    """Booking form for a tenant service."""
    if tenant_slug in RESERVED_SLUGS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    tenant = _get_tenant_by_slug(db, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    services, _total = service_service.list_services(
        db, tenant_id=tenant.id, status_filter="active", page=1, limit=100
    )
    selected = None
    if service:
        selected = next((s for s in services if s.id == service), None)

    return templates.TemplateResponse(
        request,
        "pages/tenant_book.html",
        {
            "tenant": tenant,
            "services": services,
            "selected_service": selected,
        },
    )


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


# ---------- 404 (must stay last) ----------


@router.get("/{any_path:path}", response_class=HTMLResponse)
def not_found_page(any_path: str, request: Request) -> HTMLResponse:
    """Fallback 404 page for any unmatched web route."""
    return templates.TemplateResponse(
        request,
        "pages/404.html",
        {"tenant": None},
        status_code=404,
    )
