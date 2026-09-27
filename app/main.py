"""Platform-X FastAPI application entrypoint."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import analytics as analytics_router
from app.api import auth as auth_router
from app.api import bookings as bookings_router
from app.api import notifications as notifications_router
from app.api import orders as orders_router
from app.api import payments as payments_router
from app.api import platform_admin as platform_admin_router
from app.api import referrals as referrals_router
from app.api import rewards as rewards_router
from app.api import services as services_router
from app.api import tenants as tenants_router
from app.core.config import settings
from app.web import pages as web_pages

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.APP_DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _tenant_path(request: Request, suffix: str = "") -> str:
    """Build a path scoped to the current tenant slug in the URL (if present)."""
    # Reserved prefixes that are NOT tenant slugs
    reserved = {"docs", "redoc", "openapi.json", "static", "health",
                "auth", "tenants", "services", "bookings", "orders",
                "payments", "rewards", "referrals", "notifications",
                "analytics", "platform", "businesses", "about", "contact"}
    parts = [p for p in request.url.path.split("/") if p]
    tenant_slug = parts[0] if parts and parts[0] not in reserved else None
    base = f"/{tenant_slug}" if tenant_slug else ""
    suffix = suffix.lstrip("/")
    return f"{base}/{suffix}" if suffix else (base or "/")


templates.env.globals["now_year"] = datetime.now(timezone.utc).year
templates.env.globals["tenant_path"] = _tenant_path


# ---------- API routers ----------

app.include_router(analytics_router.router)
app.include_router(auth_router.router)
app.include_router(bookings_router.router)
app.include_router(notifications_router.router)
app.include_router(orders_router.router)
app.include_router(payments_router.router)
app.include_router(platform_admin_router.router)
app.include_router(referrals_router.router)
app.include_router(rewards_router.router)
app.include_router(services_router.router)
app.include_router(tenants_router.router)


# ---------- Web (HTML pages) ----------

app.include_router(web_pages.router)


# ---------- Health ----------


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
    }
