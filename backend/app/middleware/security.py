"""Security middleware for enterprise-grade protection."""
import logging
import traceback
import time
from typing import Callable, Dict, Tuple
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings

# Configure secure logging (no sensitive data to stdout)
logger = logging.getLogger("snapstyle.security")
logger.setLevel(logging.WARNING if not settings.DEBUG else logging.DEBUG)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    Implements OWASP security best practices.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Content Security Policy - Strict
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # HTTP Strict Transport Security (HSTS)
        # max-age=31536000 = 1 year, includeSubDomains, preload
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy - Strict
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # Remove server identification header
        if "server" in response.headers:
            del response.headers["server"]

        # Add cache control for sensitive endpoints
        if "/api/auth" in str(request.url) or "/api/subscription" in str(request.url):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response


class SecureErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catch all unhandled exceptions and return sanitized error responses.
    Logs full stack traces privately, returns generic messages to clients.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            # Generate unique error ID for tracking
            import uuid
            error_id = str(uuid.uuid4())[:8]

            # Log full details privately (not to stdout in production)
            logger.error(
                f"Unhandled exception [error_id={error_id}] "
                f"path={request.url.path} method={request.method}",
                exc_info=True
            )

            # In development, log to file for debugging
            if settings.DEBUG:
                logger.debug(f"Full traceback for {error_id}:\n{traceback.format_exc()}")

            # Return sanitized error to client - NEVER expose internals
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "An internal error occurred. Please try again later.",
                    "error_id": error_id,
                    "support": "If this persists, contact support with the error_id."
                }
            )


class RateLimitInfo:
    """Rate limiting information for responses."""

    @staticmethod
    def add_headers(response: Response, limit: int, remaining: int, reset: int):
        """Add rate limit headers to response."""
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production, consider using Redis-based rate limiting.

    Rate limits:
    - Auth endpoints (/api/auth/*): 20 requests per minute (prevent brute force)
    - Search endpoints (/api/search/*): 60 requests per minute
    - General API: 120 requests per minute
    """

    def __init__(self, app):
        super().__init__(app)
        # Store: {ip: [(timestamp, count), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        self._cleanup_interval = 60  # Clean old entries every 60 seconds
        self._last_cleanup = time.time()

        # Rate limits per path prefix (requests per minute)
        self._limits = {
            "/api/auth/login": 10,      # Strict limit for login (brute force protection)
            "/api/auth/register": 5,     # Very strict for registration
            "/api/auth/": 20,            # General auth endpoints
            "/api/search/": 60,          # Search endpoints
            "/api/chat/": 30,            # Chat endpoints
            "/api/subscription/webhook": 100,  # Stripe webhooks
            "/api/": 120,                # General API
        }

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, handling proxies."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain (original client)
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_limit_for_path(self, path: str) -> int:
        """Get rate limit for a specific path."""
        for prefix, limit in self._limits.items():
            if path.startswith(prefix):
                return limit
        return 120  # Default limit

    def _cleanup_old_entries(self):
        """Remove expired rate limit entries."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = current_time - 60  # Keep last 60 seconds
        for ip in list(self._requests.keys()):
            self._requests[ip] = [
                (ts, count) for ts, count in self._requests[ip]
                if ts > cutoff
            ]
            if not self._requests[ip]:
                del self._requests[ip]

        self._last_cleanup = current_time

    def _check_rate_limit(self, ip: str, path: str) -> Tuple[bool, int, int, int]:
        """
        Check if request is within rate limit.
        Returns: (allowed, limit, remaining, reset_time)
        """
        current_time = time.time()
        limit = self._get_limit_for_path(path)
        window_start = current_time - 60  # 1 minute window

        # Count requests in current window
        key = f"{ip}:{path.split('/')[2] if len(path.split('/')) > 2 else 'root'}"
        self._requests[key] = [
            (ts, c) for ts, c in self._requests[key]
            if ts > window_start
        ]

        request_count = sum(c for _, c in self._requests[key])
        remaining = max(0, limit - request_count)
        reset_time = int(window_start + 60)

        if request_count >= limit:
            return False, limit, 0, reset_time

        # Record this request
        self._requests[key].append((current_time, 1))
        return True, limit, remaining - 1, reset_time

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and static files
        path = request.url.path
        if path in ["/", "/health"] or path.startswith("/static"):
            return await call_next(request)

        # Periodic cleanup
        self._cleanup_old_entries()

        # Check rate limit
        client_ip = self._get_client_ip(request)
        allowed, limit, remaining, reset_time = self._check_rate_limit(client_ip, path)

        if not allowed:
            logger.warning(f"Rate limit exceeded: IP={client_ip}, path={path}")
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after": reset_time - int(time.time())
                }
            )
            RateLimitInfo.add_headers(response, limit, 0, reset_time)
            response.headers["Retry-After"] = str(reset_time - int(time.time()))
            return response

        # Process request and add rate limit headers
        response = await call_next(request)
        RateLimitInfo.add_headers(response, limit, remaining, reset_time)
        return response


def setup_security_middleware(app: FastAPI) -> None:
    """Configure all security middleware for the application."""
    # Order matters: error handler should be outermost (added last = processes first)
    # Rate limiting should be early to prevent resource exhaustion
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecureErrorHandlerMiddleware)
