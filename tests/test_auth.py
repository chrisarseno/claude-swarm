"""Tests for Zuultimate authentication middleware."""

import json
import pytest
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from swarm.api.auth import (
    ZuultimateAuthMiddleware,
    AuthConfig,
    AuthContext,
    PUBLIC_PATHS,
)


def _create_app(require_auth: bool = False, **kwargs) -> FastAPI:
    """Create a minimal FastAPI app with the auth middleware."""
    app = FastAPI()
    config = AuthConfig(require_auth=require_auth, **kwargs)
    app.add_middleware(ZuultimateAuthMiddleware, auth_config=config)

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/status")
    async def status(request=None):
        from starlette.requests import Request
        # Access via dependency injection
        return {"auth": "ok"}

    @app.post("/tasks")
    async def submit_task(request=None):
        return {"task_id": "123"}

    return app


class TestAuthMiddleware:
    """Test the ZuultimateAuthMiddleware."""

    def test_public_paths_no_auth_required(self):
        """Health endpoint is always public."""
        app = _create_app(require_auth=True)
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_no_auth_required_passes_all(self):
        """When require_auth=False, all requests pass through."""
        app = _create_app(require_auth=False)
        client = TestClient(app)
        response = client.post("/tasks", json={})
        assert response.status_code == 200

    def test_auth_required_rejects_no_credentials(self):
        """When require_auth=True, requests without credentials get 401."""
        app = _create_app(require_auth=True)
        client = TestClient(app)
        response = client.get("/status")
        assert response.status_code == 401

    def test_jwt_validation_success(self):
        """Valid JWT passes auth."""
        app = _create_app(require_auth=True)
        client = TestClient(app)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "user_id": "user-1",
            "tenant_id": "tenant-1",
            "roles": ["admin"],
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            response = client.get("/status", headers={
                "Authorization": "Bearer valid-token-123"
            })
            assert response.status_code == 200

    def test_api_key_validation_success(self):
        """Valid API key passes auth."""
        app = _create_app(require_auth=True)
        client = TestClient(app)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "user_id": "api-user",
            "tenant_id": "tenant-2",
            "roles": ["api"],
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            response = client.get("/status", headers={
                "X-API-Key": "gzr_test_key_12345"
            })
            assert response.status_code == 200

    def test_service_token_validation_success(self):
        """Valid service token passes auth."""
        app = _create_app(require_auth=True)
        client = TestClient(app)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "tenant_id": "system",
            "roles": ["service"],
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            response = client.get("/status", headers={
                "X-Service-Token": "svc-token-abc"
            })
            assert response.status_code == 200

    def test_invalid_jwt_rejected(self):
        """Invalid JWT gets 401 when auth required."""
        import urllib.error
        app = _create_app(require_auth=True)
        client = TestClient(app)

        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized", hdrs={}, fp=None
        )):
            response = client.get("/status", headers={
                "Authorization": "Bearer invalid-token"
            })
            assert response.status_code == 401

    def test_zuultimate_unreachable_rejects(self):
        """When Zuultimate is unreachable, auth fails."""
        app = _create_app(require_auth=True)
        client = TestClient(app)

        with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            response = client.get("/status", headers={
                "Authorization": "Bearer some-token"
            })
            assert response.status_code == 401

    def test_zuultimate_unreachable_passes_when_not_required(self):
        """When auth not required, Zuultimate being down is fine."""
        app = _create_app(require_auth=False)
        client = TestClient(app)

        with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            response = client.get("/status", headers={
                "Authorization": "Bearer some-token"
            })
            assert response.status_code == 200


class TestAuthContext:
    def test_default_unauthenticated(self):
        ctx = AuthContext()
        assert ctx.authenticated is False
        assert ctx.user_id == ""

    def test_to_dict(self):
        ctx = AuthContext(
            authenticated=True,
            user_id="u1",
            tenant_id="t1",
            roles=["admin"],
            auth_method="jwt",
        )
        d = ctx.to_dict()
        assert d["authenticated"] is True
        assert d["user_id"] == "u1"
        assert d["auth_method"] == "jwt"


class TestAuthConfig:
    def test_defaults(self):
        cfg = AuthConfig()
        assert cfg.require_auth is False
        assert cfg.zuultimate_url == "http://localhost:8000"
        assert cfg.cache_ttl_seconds == 300


class TestAuthCache:
    def test_cache_hit(self):
        """Cached tokens don't re-call Zuultimate."""
        app = _create_app(require_auth=True)
        client = TestClient(app)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "user_id": "cached-user",
            "tenant_id": "t1",
            "roles": [],
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            # First call
            client.get("/status", headers={"Authorization": "Bearer cache-test"})
            # Second call should use cache
            client.get("/status", headers={"Authorization": "Bearer cache-test"})
            # Should only have called urlopen once
            assert mock_open.call_count == 1
