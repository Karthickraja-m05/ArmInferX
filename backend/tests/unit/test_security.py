"""Unit tests for ArmServe security foundation, headers, auth boundaries, and key hashing."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.app.core.dependencies import require_scope
from backend.app.core.security import (
    AuthContext,
    Scope,
    generate_secure_api_key,
    hash_api_key,
    verify_api_key,
)
from backend.app.main import app


def test_security_headers_present() -> None:
    """Verify response contains all required secure HTTP headers."""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers.get("permissions-policy", "")
    assert "max-age=31536000" in headers.get("strict-transport-security", "")


def test_api_key_hashing_and_verification() -> None:
    """Verify constant-time API key hashing and verification."""
    raw_key = generate_secure_api_key("arm_test_")
    assert raw_key.startswith("arm_test_")

    digest = hash_api_key(raw_key)
    assert len(digest) == 64

    assert verify_api_key(raw_key, raw_key) is True
    assert verify_api_key(raw_key, "wrong_key_12345") is False
    assert verify_api_key("", raw_key) is False


def test_authorization_scope_enforcement() -> None:
    """Verify require_scope dependency enforces RBAC authorization boundaries."""
    test_app = FastAPI()

    @test_app.get("/admin-only")
    async def admin_route(
        auth: AuthContext = Depends(require_scope(Scope.SYSTEM_CONFIG)),
    ) -> dict[str, str]:
        return {"status": "success", "subject": auth.subject_id}

    client = TestClient(test_app)

    # 1. Unauthenticated / insufficient scope fails with HTTP 403
    res_forbidden = client.get("/admin-only")
    assert res_forbidden.status_code == 403
    assert "Permission denied" in res_forbidden.text

    # 2. Request with X-API-Key header granting admin scope succeeds
    res_admin = client.get("/admin-only", headers={"X-API-Key": "arm_live_test_key"})
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "success"
