"""Security utilities, credential verification, API key hashing, and RBAC authorization."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from enum import Enum

from backend.app.core.config import settings


class Role(str, Enum):
    """System user and client roles."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Scope(str, Enum):
    """Permission scopes for fine-grained authorization boundaries."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    MODELS_READ = "models:read"
    MODELS_WRITE = "models:write"
    EXPERIMENTS_CREATE = "experiments:create"
    SYSTEM_CONFIG = "system:config"


# Role-to-Scope Permissions Mapping Matrix
ROLE_PERMISSIONS: dict[Role, set[Scope]] = {
    Role.ADMIN: {
        Scope.READ,
        Scope.WRITE,
        Scope.ADMIN,
        Scope.MODELS_READ,
        Scope.MODELS_WRITE,
        Scope.EXPERIMENTS_CREATE,
        Scope.SYSTEM_CONFIG,
    },
    Role.OPERATOR: {
        Scope.READ,
        Scope.WRITE,
        Scope.MODELS_READ,
        Scope.MODELS_WRITE,
        Scope.EXPERIMENTS_CREATE,
    },
    Role.VIEWER: {
        Scope.READ,
        Scope.MODELS_READ,
    },
}


@dataclass
class AuthContext:
    """Authenticated identity context representing a user or API client."""

    subject_id: str
    role: Role
    scopes: set[Scope]
    is_authenticated: bool = True
    auth_method: str = "token"

    def has_scope(self, scope: Scope) -> bool:
        """Check if identity context holds a specific permission scope."""
        return scope in self.scopes or Scope.ADMIN in self.scopes


def hash_api_key(api_key: str) -> str:
    """Generate SHA-256 digest of API key to store and compare securely."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def verify_api_key(provided_key: str, expected_key: str) -> bool:
    """Constant-time comparison of API keys to prevent timing attacks."""
    if not provided_key or not expected_key:
        return False
    return hmac.compare_digest(hash_api_key(provided_key), hash_api_key(expected_key))


def generate_secure_api_key(prefix: str = "arm_live_") -> str:
    """Generate a cryptographically secure 256-bit API key."""
    raw_bytes = secrets.token_hex(24)
    return f"{prefix}{raw_bytes}"


def get_default_auth_context() -> AuthContext:
    """Fallback identity context for unauthenticated or development mode access."""
    if settings.app.debug or settings.app.env.value == "development":
        # In development mode, default to OPERATOR role with read/write access
        return AuthContext(
            subject_id="dev-user",
            role=Role.OPERATOR,
            scopes=ROLE_PERMISSIONS[Role.OPERATOR],
            auth_method="development_default",
        )
    return AuthContext(
        subject_id="anonymous",
        role=Role.VIEWER,
        scopes=ROLE_PERMISSIONS[Role.VIEWER],
        is_authenticated=False,
        auth_method="anonymous",
    )
