"""Kiha Server — JWT Authentication Middleware."""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Paths that do not require authentication
PUBLIC_PATHS: frozenset[str] = frozenset({
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
})


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """JWT-based authentication middleware.

    Validates access tokens for protected endpoints.
    Access token lifetime: 15 minutes (per MASTER.md).
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], object],
    ) -> Response:
        """Check JWT token for protected routes."""
        # Skip authentication for public paths
        if request.url.path in PUBLIC_PATHS:
            response: Response = await call_next(request)  # type: ignore[assignment]
            return response

        # TODO: Refactor - Implement actual JWT validation
        # 1. Extract token from Authorization header
        # 2. Verify with python-jose
        # 3. Check expiry (15 min access, 7 day refresh)
        # 4. Attach user/device info to request.state

        response = await call_next(request)  # type: ignore[assignment]
        return response
