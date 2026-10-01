"""Platform-X FastAPI application entrypoint."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import account_ai as account_ai_router
from app.api import ai as ai_router
from app.api import attractions as attractions_router
from app.api import availability as availability_router
from app.api import analytics as analytics_router
from app.api import auth as auth_router
from app.api import booking_mod as booking_mod_router
from app.api import bookings as bookings_router
from app.api import cancellation as cancellation_router
from app.api import compare as compare_router
from app.api import business as business_router
from app.api import business_api_keys as business_api_keys_router
from app.api import business_exports as business_exports_router
from app.api import business_insights as business_insights_router
from app.api import business_promotions as business_promotions_router
from app.api import business_rate_plans as business_rate_plans_router
from app.api import business_reports as business_reports_router
from app.api import business_reviews as business_reviews_router
from app.api import business_rooms as business_rooms_router
from app.api import business_market as business_market_router
from app.api import business_webhooks as business_webhooks_router
from app.api import business_marketing as business_marketing_router
from app.api import business_no_show as business_no_show_router
from app.api import business_pricing as business_pricing_router
from app.api import groups as groups_router
from app.api import leaderboard as leaderboard_router
from app.api import messages as messages_router
from app.api import notifications as notifications_router
from app.api import orders as orders_router
from app.api import partners as partners_router
from app.api import payments as payments_router
from app.api import platform_admin as platform_admin_router
from app.api import price_alerts as price_alerts_router
from app.api import price_locks as price_locks_router
from app.api import public_v1 as public_v1_router
from app.api import receipts as receipts_router
from app.api import recent_searches as recent_searches_router
from app.api import referrals as referrals_router
from app.api import reviews as reviews_router
from app.api import rewards as rewards_router
from app.api import rewards_redeem as rewards_redeem_router
from app.api import search as search_router
from app.api import services as services_router
from app.api import tenants as tenants_router
from app.api import trust_score as trust_score_router
from app.api import budget_optimizer as budget_optimizer_router
from app.api import bundle_deals as bundle_deals_router
from app.api import business_peer_benchmark as business_peer_benchmark_router
from app.api import upsell as upsell_router
from app.api import installments as installments_router
from app.api import business_groups as business_groups_router
from app.api import business_auto_repricing as business_auto_repricing_router
from app.api import wishlist as wishlist_router
from app.api import waitlist as waitlist_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.https_redirect import HTTPSRedirectMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
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

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Return a clean 429 response when rate limit is exceeded."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please slow down and try again shortly.",
            "retry_after": getattr(exc, "retry_after", None),
        },
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
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


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(HTTPSRedirectMiddleware)


# ---------- API routers ----------

app.include_router(ai_router.router)
app.include_router(availability_router.router)
app.include_router(attractions_router.router)
app.include_router(account_ai_router.router)
app.include_router(ai_router.business_router)
app.include_router(analytics_router.router)
app.include_router(auth_router.router)
app.include_router(bookings_router.router)
app.include_router(booking_mod_router.router)
app.include_router(cancellation_router.router)
app.include_router(compare_router.router)
app.include_router(business_router.router)
app.include_router(business_marketing_router.router)
app.include_router(business_no_show_router.router)
app.include_router(business_api_keys_router.router)
app.include_router(business_exports_router.router)
app.include_router(business_insights_router.router)
app.include_router(business_promotions_router.router)
app.include_router(business_rate_plans_router.router)
app.include_router(business_reports_router.router)
app.include_router(business_reviews_router.router)
app.include_router(business_rooms_router.router)
app.include_router(business_market_router.router)
app.include_router(business_webhooks_router.router)
app.include_router(business_pricing_router.router)
app.include_router(messages_router.router)
app.include_router(messages_router.business_router)
app.include_router(groups_router.router)
app.include_router(leaderboard_router.router)
app.include_router(leaderboard_router.business_router)
app.include_router(leaderboard_router.platform_router)
app.include_router(notifications_router.router)
app.include_router(orders_router.router)
app.include_router(partners_router.router)
app.include_router(payments_router.router)
app.include_router(platform_admin_router.router)
app.include_router(price_alerts_router.router)
app.include_router(price_locks_router.router)
app.include_router(receipts_router.router)
app.include_router(recent_searches_router.router)
app.include_router(referrals_router.router)
app.include_router(public_v1_router.router)
app.include_router(reviews_router.router)
app.include_router(rewards_router.router)
app.include_router(rewards_redeem_router.router)
app.include_router(search_router.router)
app.include_router(services_router.router)
app.include_router(tenants_router.router)
app.include_router(wishlist_router.router)
app.include_router(trust_score_router.router)
app.include_router(budget_optimizer_router.router)
app.include_router(bundle_deals_router.router)
app.include_router(business_peer_benchmark_router.router)
app.include_router(upsell_router.router)
app.include_router(installments_router.router)
app.include_router(business_groups_router.router)
app.include_router(business_auto_repricing_router.router)
app.include_router(waitlist_router.router)


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
