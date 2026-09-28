"""Security headers middleware for Platform-X."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


# Content-Security-Policy
# - default-src 'self': only own origin
# - script-src: 'self' + Cloudflare CDN (for /docs) + inline (needed for our own small scripts)
# - style-src: 'self' + Google Fonts + inline (Tailwind removed, but some inline styles)
# - img-src: 'self' + Unsplash + data URIs (for gradients/placeholders)
# - font-src: 'self' + Google Fonts
# - connect-src: 'self' only
# - frame-ancestors 'none': disallow embedding
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: https://images.unsplash.com https://*.trycloudflare.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )
        response.headers["Content-Security-Policy"] = CSP

        # Only send HSTS in production (avoids forced HTTPS in dev)
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
