"""Platform-X FastAPI application entrypoint."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
from app.web.templates import templates  # noqa: F401  (kept for future direct use)

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
