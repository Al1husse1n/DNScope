import pytest

from dnscope.validation import DomainValidationError, ValidatedDomain, validate_domain


def test_valid_simple() -> None:
    res = validate_domain("example.com")
    assert res == ValidatedDomain(original="example.com", normalized="example.com", is_idn=False)


def test_valid_with_subdomain() -> None:
    res = validate_domain("sub.example.com")
    assert res.normalized == "sub.example.com"
    assert res.is_idn is False


def test_valid_deep_subdomain() -> None:
    res = validate_domain("deep.nested.sub.domain.co.uk")
    assert res.normalized == "deep.nested.sub.domain.co.uk"
    assert res.is_idn is False


def test_valid_with_hyphens() -> None:
    res = validate_domain("my-cool-domain.org")
    assert res.normalized == "my-cool-domain.org"
    assert res.is_idn is False


def test_valid_numbers_in_label() -> None:
    res = validate_domain("123-service-456.net")
    assert res.normalized == "123-service-456.net"
    assert res.is_idn is False


def test_valid_single_char_labels() -> None:
    res = validate_domain("a.b.com")
    assert res.normalized == "a.b.com"
    assert res.is_idn is False


def test_valid_uppercase_and_trailing_dot() -> None:
    res = validate_domain("Example.COM.")
    assert res.normalized == "example.com"
    assert res.is_idn is False


def test_valid_trailing_dot_stripped() -> None:
    res = validate_domain("sub.domain.org.")
    assert res.normalized == "sub.domain.org"
    assert res.is_idn is False


def test_valid_whitespace_trimmed() -> None:
    res = validate_domain("   spaced-domain.io   ")
    assert res.normalized == "spaced-domain.io"
    assert res.is_idn is False


def test_valid_unicode_idn_munchen() -> None:
    res = validate_domain("münchen.de")
    assert res.normalized == "xn--mnchen-3ya.de"
    assert res.is_idn is True
    assert res.original == "münchen.de"


def test_valid_unicode_idn_buecher() -> None:
    res = validate_domain("bücher.ch")
    assert res.normalized == "xn--bcher-kva.ch"
    assert res.is_idn is True


# Rejection path tests (Invalid cases)


def test_reject_empty_string() -> None:
    with pytest.raises(DomainValidationError, match="empty"):
        validate_domain("")


def test_reject_whitespace_only() -> None:
    with pytest.raises(DomainValidationError, match="empty"):
        validate_domain("    ")


def test_reject_scheme_http() -> None:
    with pytest.raises(DomainValidationError, match="scheme"):
        validate_domain("http://example.com")


def test_reject_scheme_https() -> None:
    with pytest.raises(DomainValidationError, match="scheme"):
        validate_domain("https://example.com")


def test_reject_path() -> None:
    with pytest.raises(DomainValidationError, match="path"):
        validate_domain("example.com/test")


def test_reject_query() -> None:
    with pytest.raises(DomainValidationError, match="query"):
        validate_domain("example.com?search=threat")


def test_reject_fragment() -> None:
    with pytest.raises(DomainValidationError, match="fragment"):
        validate_domain("example.com#section")


def test_reject_userinfo() -> None:
    with pytest.raises(DomainValidationError, match="userinfo"):
        validate_domain("admin@example.com")


def test_reject_port() -> None:
    with pytest.raises(DomainValidationError, match="port"):
        validate_domain("example.com:8080")


def test_reject_single_dot_only() -> None:
    with pytest.raises(DomainValidationError, match="empty"):
        validate_domain(".")


def test_reject_double_trailing_dot() -> None:
    with pytest.raises(DomainValidationError, match="empty"):
        validate_domain("example.com..")


def test_reject_no_dot_localhost() -> None:
    with pytest.raises(DomainValidationError, match="at least one dot"):
        validate_domain("localhost")


def test_reject_no_dot_tld_alone() -> None:
    with pytest.raises(DomainValidationError, match="at least one dot"):
        validate_domain("com")


def test_reject_label_starts_with_hyphen() -> None:
    with pytest.raises(DomainValidationError, match="hyphen"):
        validate_domain("-example.com")


def test_reject_label_ends_with_hyphen() -> None:
    with pytest.raises(DomainValidationError, match="hyphen"):
        validate_domain("example-.com")


def test_reject_subdomain_starts_with_hyphen() -> None:
    with pytest.raises(DomainValidationError, match="hyphen"):
        validate_domain("sub.-bad.example.com")


def test_reject_empty_middle_label() -> None:
    with pytest.raises(DomainValidationError, match="empty labels"):
        validate_domain("example..com")


def test_reject_numeric_tld() -> None:
    with pytest.raises(DomainValidationError, match="valid domain format"):
        validate_domain("example.123")


def test_reject_single_letter_tld() -> None:
    with pytest.raises(DomainValidationError, match="valid domain format"):
        validate_domain("example.c")


def test_reject_label_exceeding_63_chars() -> None:
    long_label = "a" * 64
    with pytest.raises(DomainValidationError, match="(valid domain format|Label too long)"):
        validate_domain(f"{long_label}.com")


def test_reject_domain_exceeding_253_chars() -> None:
    long_domain = (
        "a" * 50 + "." + "b" * 50 + "." + "c" * 50 + "." + "d" * 50 + "." + "e" * 50 + ".com"
    )
    assert len(long_domain) > 253
    with pytest.raises(DomainValidationError, match="valid domain format"):
        validate_domain(long_domain)


def test_reject_non_string() -> None:
    with pytest.raises(DomainValidationError, match="must be a string"):
        validate_domain(12345)  # type: ignore[arg-type]
