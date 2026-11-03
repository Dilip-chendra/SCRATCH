import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from app.core.config import settings

# Initialize Argon2id hasher with OWASP-recommended parameters
hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False
    except Exception:
        return False


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a short-lived signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access"
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]}
        )
        if payload.get("type") != "access":
            return None
        return payload
    except (jwt.PyJWTError, Exception):
        return None


def generate_refresh_token() -> tuple[str, str]:
    """
    Generate a cryptographically random refresh token.
    Returns:
        (raw_token, token_hash)
        raw_token: sent to user in httpOnly cookie
        token_hash: SHA-256 digest stored in database
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    return raw_token, token_hash


def hash_token(token: str) -> str:
    """Compute SHA-256 hash of a token string for secure database lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token(session_key: str) -> str:
    """Generate a signed HMAC-SHA256 CSRF token bound to a session key."""
    salt = secrets.token_hex(8)
    message = f"{session_key}:{salt}".encode("utf-8")
    signature = hmac.new(settings.CSRF_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"{salt}:{signature}"


def verify_csrf_token(csrf_token: str, session_key: str) -> bool:
    """Validate that the CSRF token matches the session signature."""
    try:
        parts = csrf_token.split(":")
        if len(parts) != 2:
            return False
        salt, signature = parts
        expected_message = f"{session_key}:{salt}".encode("utf-8")
        expected_signature = hmac.new(
            settings.CSRF_SECRET.encode("utf-8"), expected_message, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False
