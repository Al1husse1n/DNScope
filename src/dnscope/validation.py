import re
from dataclasses import dataclass

import idna

DOMAIN_REGEX = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


class DomainValidationError(ValueError):
    """Raised when a submitted domain is invalid."""


@dataclass(frozen=True)
class ValidatedDomain:
    original: str
    normalized: str  # lowercase, IDNA-encoded, trailing dot stripped
    is_idn: bool  # True if the input required IDNA conversion


def validate_domain(raw: str) -> ValidatedDomain:
    """Validate and normalize a domain name.

    Rules:
      - Trim whitespace. Reject empty.
      - Reject strings containing a scheme ("http://"), path ("/"), query ("?"),
        fragment ("#"), userinfo ("@"), or port (":", except inside an IPv6 which
        we don't accept as a domain anyway).
      - Strip a single trailing dot if present.
      - Lowercase.
      - Convert unicode labels to IDNA (punycode) form. Track whether conversion
        occurred in `is_idn`.
      - Reject if the resulting ASCII form does not match:
          ^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,63}$
      - Reject labels starting or ending with '-' (already covered by regex,
        but assert explicitly for clearer errors).
      - Reject if there is no dot (TLDs alone like "localhost" are rejected).
    Raises DomainValidationError with a clear message on every rejection path.
    """
    if not isinstance(raw, str):
        raise DomainValidationError("Domain must be a string")

    trimmed = raw.strip()
    if not trimmed:
        raise DomainValidationError("Domain cannot be empty or whitespace only")

    # Reject strings containing scheme, path, query, fragment, userinfo, port
    if "/" in trimmed:
        raise DomainValidationError("Domain contains path or scheme '/'")
    if "?" in trimmed:
        raise DomainValidationError("Domain contains query '?'")
    if "#" in trimmed:
        raise DomainValidationError("Domain contains fragment '#'")
    if "@" in trimmed:
        raise DomainValidationError("Domain contains userinfo '@'")
    if ":" in trimmed:
        raise DomainValidationError("Domain contains port or colon ':'")

    # Strip a single trailing dot if present
    s = trimmed.removesuffix(".")

    if not s:
        raise DomainValidationError("Domain cannot be empty after stripping trailing dot")

    # Lowercase
    s = s.lower()

    # Reject if there is no dot (TLDs alone like "localhost" are rejected)
    if "." not in s:
        raise DomainValidationError(
            f"Domain '{s}' must contain at least one dot (single-label domains like 'localhost' are rejected)"
        )

    # Reject empty labels (e.g. ".." or leading/trailing dots)
    if ".." in s or s.startswith(".") or s.endswith("."):
        raise DomainValidationError("Domain cannot contain empty labels")

    # Reject domain exceeding 253 chars
    if len(s) > 253:
        raise DomainValidationError(
            f"Domain '{s}' exceeds maximum length of 253 characters (valid domain format)"
        )

    # Reject labels starting or ending with '-' or exceeding 63 chars
    raw_labels = s.split(".")
    for rlabel in raw_labels:
        if not rlabel:
            raise DomainValidationError("Domain cannot contain empty labels")
        if len(rlabel) > 63:
            raise DomainValidationError(
                f"Domain label '{rlabel}' exceeds maximum length of 63 characters (valid domain format)"
            )
        if rlabel.startswith("-") or rlabel.endswith("-"):
            raise DomainValidationError(
                f"Domain label '{rlabel}' cannot start or end with a hyphen"
            )

    # Convert unicode labels to IDNA (punycode) form. Track whether conversion occurred in `is_idn`.
    is_idn = False
    try:
        if any(ord(c) >= 128 for c in s):
            encoded = idna.encode(s, uts46=True).decode("ascii")
            is_idn = True
        else:
            encoded = idna.encode(s, uts46=True).decode("ascii")
            if encoded != s:
                is_idn = True
    except idna.IDNAError as e:
        raise DomainValidationError(f"Invalid IDNA domain: {e}") from e

    # Check for empty labels or labels starting/ending with '-' explicitly on encoded form
    labels = encoded.split(".")
    for label in labels:
        if not label:
            raise DomainValidationError("Domain cannot contain empty labels")
        if label.startswith("-") or label.endswith("-"):
            raise DomainValidationError(f"Domain label '{label}' cannot start or end with a hyphen")

    # Check against spec regex
    if not DOMAIN_REGEX.match(encoded):
        raise DomainValidationError(
            f"Domain '{encoded}' does not match valid domain format (length, characters, or TLD)"
        )

    return ValidatedDomain(original=raw, normalized=encoded, is_idn=is_idn)
