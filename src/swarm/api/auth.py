"""Authentication middleware for Claude Swarm.

Validates requests against Zuultimate's identity service.
Supports JWT Bearer tokens, API keys (gzr_ prefix), and
service tokens (X-Service-Token header).

When ``require_auth`` is False (the default for local/dev),
all requests pass through unauthenticated.
"""

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Paths that never require authentication
PUBLIC_PATHS = {"/health", "/", "/docs", "/openapi.json", "/redoc"}


@dataclass
class AuthConfig:
    """Authentication configuration."""
    require_auth: bool = False
    zuultimate_url: str = "http://localhost:8000"
    service_token: str = ""  # Swarm's own service token for Zuul calls
    cache_ttl_seconds: int = 300
    public_paths: List[str] = field(default_factory=lambda: list(PUBLIC_PATHS))


@dataclass
class AuthContext:
    """Authenticated user/service context attached to request state."""
    authenticated: bool = False
    user_id: str = ""
    tenant_id: str = ""
    roles: List[str] = field(default_factory=list)
    auth_method: str = ""  # jwt, api_key, service_token

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authenticated": self.authenticated,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "roles": self.roles,
            "auth_method": self.auth_method,
        }


class ZuultimateAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates auth tokens via Zuultimate.

    Extracts credentials from:
    - ``Authorization: Bearer <jwt>``
    - ``X-API-Key: gzr_...``
    - ``X-Service-Token: <token>``

    When ``require_auth=False`` (default), requests without credentials
    pass through with an unauthenticated context. When ``True``, missing
    or invalid credentials return 401.
    """

    def __init__(self, app, auth_config: Optional[AuthConfig] = None):
        super().__init__(app)
        self.config = auth_config or AuthConfig()
        self._cache: Dict[str, tuple] = {}  # token -> (auth_context, expires_at)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Always allow public paths
        if request.url.path in self.config.public_paths:
            request.state.auth = AuthContext()
            return await call_next(request)

        # WebSocket upgrade — skip auth check (WS auth handled at connect)
        if request.headers.get("upgrade", "").lower() == "websocket":
            request.state.auth = AuthContext()
            return await call_next(request)

        # Extract credentials
        auth_context = self._extract_and_validate(request)

        if not auth_context.authenticated and self.config.require_auth:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.auth = auth_context
        return await call_next(request)

    def _extract_and_validate(self, request: Request) -> AuthContext:
        """Extract credentials from request and validate against Zuultimate."""
        # Try Authorization header (JWT)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return self._validate_jwt(token)

        # Try API key
        api_key = request.headers.get("x-api-key", "")
        if api_key.startswith("gzr_"):
            return self._validate_api_key(api_key)

        # Try service token
        service_token = request.headers.get("x-service-token", "")
        if service_token:
            return self._validate_service_token(service_token)

        return AuthContext()

    def _validate_jwt(self, token: str) -> AuthContext:
        """Validate a JWT token against Zuultimate."""
        cached = self._check_cache(f"jwt:{token}")
        if cached:
            return cached

        result = self._call_zuultimate("/v1/identity/auth/validate", {
            "Authorization": f"Bearer {token}",
        })
        if not result:
            return AuthContext()

        ctx = AuthContext(
            authenticated=True,
            user_id=result.get("user_id", result.get("sub", "")),
            tenant_id=result.get("tenant_id", ""),
            roles=result.get("roles", []),
            auth_method="jwt",
        )
        self._set_cache(f"jwt:{token}", ctx)
        return ctx

    def _validate_api_key(self, api_key: str) -> AuthContext:
        """Validate an API key against Zuultimate."""
        cached = self._check_cache(f"apikey:{api_key}")
        if cached:
            return cached

        result = self._call_zuultimate("/v1/identity/auth/validate", {
            "X-API-Key": api_key,
        })
        if not result:
            return AuthContext()

        ctx = AuthContext(
            authenticated=True,
            user_id=result.get("user_id", ""),
            tenant_id=result.get("tenant_id", ""),
            roles=result.get("roles", []),
            auth_method="api_key",
        )
        self._set_cache(f"apikey:{api_key}", ctx)
        return ctx

    def _validate_service_token(self, token: str) -> AuthContext:
        """Validate a service-to-service token."""
        cached = self._check_cache(f"svc:{token}")
        if cached:
            return cached

        result = self._call_zuultimate("/v1/identity/auth/validate", {
            "X-Service-Token": token,
        })
        if not result:
            return AuthContext()

        ctx = AuthContext(
            authenticated=True,
            user_id="service",
            tenant_id=result.get("tenant_id", ""),
            roles=result.get("roles", ["service"]),
            auth_method="service_token",
        )
        self._set_cache(f"svc:{token}", ctx)
        return ctx

    def _call_zuultimate(
        self, path: str, headers: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Call Zuultimate identity endpoint."""
        url = f"{self.config.zuultimate_url}{path}"
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "Claude-Swarm/1.0")
            if self.config.service_token:
                req.add_header("X-Service-Token", self.config.service_token)
            for key, value in headers.items():
                req.add_header(key, value)

            with urllib.request.urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                logger.debug(f"Auth validation failed: {e.code}")
            else:
                logger.warning(f"Zuultimate call failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Zuultimate unreachable: {e}")
            return None

    def _check_cache(self, key: str) -> Optional[AuthContext]:
        """Check cache for a previously validated token."""
        import time
        entry = self._cache.get(key)
        if entry:
            ctx, expires_at = entry
            if time.time() < expires_at:
                return ctx
            del self._cache[key]
        return None

    def _set_cache(self, key: str, ctx: AuthContext) -> None:
        """Cache a validated auth context."""
        import time
        self._cache[key] = (ctx, time.time() + self.config.cache_ttl_seconds)
