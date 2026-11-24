"""API key hashing, HMAC indexing, and verification.

Design Rationale:
  We HMAC before hashing so a DB leak of `key_hash` does not enable offline
  brute-force of low-entropy keys, and we index on an HMAC prefix so
  verification is O(1) in the number of keys, not O(n).

  API keys have ~256 bits of entropy if generated correctly. Argon2 is
  overkill for that entropy, but it's the right choice because:
  (a) it's the recommended default in 2025,
  (b) it exercises the same code path you'd use for user passwords in a future phase,
  (c) it makes the code defensible in interview.
  Plain SHA-256 without salt/HMAC is avoided as it is vulnerable to offline lookup.
"""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()


def generate_api_key() -> str:
    """Generate a high-entropy URL-safe raw API key."""
    return secrets.token_urlsafe(32)


def compute_hmac(raw_key: str, secret: str) -> str:
    """Compute HMAC-SHA256 of raw_key using the server secret."""
    return hmac.new(
        secret.encode("utf-8"),
        raw_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def compute_hmac_prefix(raw_key: str, secret: str) -> str:
    """Compute the 16-character HMAC prefix used as a fast lookup index."""
    return compute_hmac(raw_key, secret)[:16]


def hash_api_key(raw_key: str) -> str:
    """Hash an API key with argon2.

    Deterministic-in-the-sense-that argon2's verify() will accept the result;
    NOT deterministic in output (argon2 salts internally).
    """
    return _hasher.hash(raw_key)


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """Return True iff verify succeeds.

    Return False on VerifyMismatchError, InvalidHashError, or any exception.
    NEVER raise.
    """
    try:
        return _hasher.verify(stored_hash, raw_key)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False
