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
from app.api import partners as partners_router
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



# ---------- Redirect trailing slashes on reserved paths ----------

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse as StarletteRedirect


class TrailingSlashRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect /foo/ to /foo for reserved (non-tenant) paths."""

    RESERVED = {
        "docs", "redoc", "openapi.json", "static", "health",
        "auth", "tenants", "services", "bookings", "orders",
        "payments", "rewards", "referrals", "notifications",
        "analytics", "platform", "businesses", "about", "contact",
        "login", "register", "hotels", "restaurants", "travel",
        "entertainment", "favicon.ico",
    }

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path.endswith("/") and len(path) > 1:
            first = path.strip("/").split("/", 1)[0]
            if first in self.RESERVED:
                new_path = path.rstrip("/")
                if request.url.query:
                    new_path += "?" + request.url.query
                return StarletteRedirect(url=new_path, status_code=307)
        return await call_next(request)


app.add_middleware(TrailingSlashRedirectMiddleware)




class NoCacheHTMLMiddleware(BaseHTTPMiddleware):
    """Ensure HTML pages are never cached; static files keep their cache."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        # Only apply to HTML-ish requests (not /static, not /docs, not API paths)
        if not path.startswith("/static") and not path.startswith("/docs") and not path.startswith("/redoc"):
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                response.headers["Pragma"] = "no-cache"
        return response


app.add_middleware(NoCacheHTMLMiddleware)


# ---------- API routers ----------

app.include_router(analytics_router.router)
app.include_router(auth_router.router)
app.include_router(bookings_router.router)
app.include_router(notifications_router.router)
app.include_router(orders_router.router)
app.include_router(partners_router.router)
app.include_router(payments_router.router)
app.include_router(platform_admin_router.router)
app.include_router(referrals_router.router)
app.include_router(rewards_router.router)
app.include_router(services_router.router)
app.include_router(tenants_router.router)


# ---------- Health (before web catch-all) ----------


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
    }


# ---------- Web (HTML pages, catch-all 404 stays last) ----------

app.include_router(web_pages.router)
