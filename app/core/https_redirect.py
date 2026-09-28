"""HTTPS enforcement middleware for production."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.core.config import settings


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP → HTTPS in production.

    In production, all HTTP requests are redirected to their HTTPS equivalent.
    This middleware trusts X-Forwarded-Proto (set by Cloudflare/Nginx).
    In development, it does nothing.
    """

    async def dispatch(self, request: Request, call_next):
        if settings.APP_ENV != "production":
            return await call_next(request)

        # Trust X-Forwarded-Proto from proxy (Cloudflare, Nginx)
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        if proto != "https":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(url), status_code=301)

        return await call_next(request)
