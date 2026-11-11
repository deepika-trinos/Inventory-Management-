"""Password hashing and JWT login tokens.

PASSWORD HASHING (PRD AUTH-06)
  A "hash" is a one-way scrambled fingerprint of a password. We store only the
  hash. At login we hash what the user typed and compare. Nobody, including
  us, can turn the hash back into the password. We use Argon2 (via pwdlib),
  which is deliberately slow and adds a random "salt", so stolen hashes are
  very hard to crack and two equal passwords get different hashes.

JWT (JSON Web Token)
  After a successful login the server gives the browser a signed "pass":
      header . payload . signature
  The payload says who you are (user id) and when the pass expires. The
  signature is made with JWT_SECRET_KEY, so if anyone changes the payload the
  signature no longer matches and the server rejects it. The browser sends the
  token with every request in the header:  Authorization: Bearer <token>
  Note: a JWT is signed, not encrypted. Anyone holding it can READ the payload,
  so we never put secrets in it.
"""

from datetime import timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings
from app.core.database import utc_now

_password_hash = PasswordHash((Argon2Hasher(),))

# A hash of a random throwaway value. When someone logs in with an email that
# does not exist we still "check" a password against this, so the response
# takes the same time and nobody can discover which emails exist.
_DUMMY_HASH = _password_hash.hash("not-a-real-password-used-only-for-timing")


# ---- Passwords ---------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """Check a password. Returns (is_correct, new_hash_or_None).

    new_hash is set when the stored hash uses older settings and should be
    replaced (pwdlib upgrades hashes automatically over time).
    """
    if password_hash is None:
        _password_hash.verify(plain_password, _DUMMY_HASH)  # same timing as a real check
        return False, None
    return _password_hash.verify_and_update(plain_password, password_hash)


# ---- JWT tokens --------------------------------------------------------------
class TokenError(Exception):
    """The token is missing, malformed, tampered with or expired."""


def create_access_token(user_id: int) -> tuple[str, int]:
    """Make a signed token for this user. Returns (token, seconds_until_expiry)."""
    settings = get_settings()
    now = utc_now()
    expires_in = settings.access_token_expire_minutes * 60
    payload: dict[str, Any] = {
        "sub": str(user_id),  # "subject": who the token belongs to
        "type": "access",
        "iat": now,  # issued at
        "exp": now + timedelta(seconds=expires_in),  # expires at
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> int:
    """Check the signature and expiry. Returns the user id, or raises TokenError."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],  # never accept other algorithms
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("type") != "access":
        raise TokenError("Wrong token type.")
    try:
        return int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise TokenError("Bad subject.") from exc
