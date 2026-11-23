import asyncio
import inspect
from typing import Any

import dns.asyncresolver
import dns.exception
import dns.resolver

from dnscope.agents.base import stopwatch
from dnscope.schemas.common import AgentStatus
from dnscope.schemas.findings import DNSFinding
from dnscope.validation import DomainValidationError, validate_domain

RECORD_TYPES = ("A", "AAAA", "MX", "NS", "TXT")


class DNSAgent:
    def __init__(
        self,
        resolver: Any | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._resolver = resolver
        self._timeout_seconds = timeout_seconds

    def _get_resolver(self) -> Any:
        if self._resolver is not None:
            return self._resolver
        res = dns.asyncresolver.Resolver()
        res.lifetime = self._timeout_seconds
        res.timeout = self._timeout_seconds
        return res

    async def _resolve_type(
        self, resolver: Any, domain: str, rdtype: str
    ) -> tuple[str, list[str] | Exception]:
        try:
            call = resolver.resolve(domain, rdtype)
            if inspect.isawaitable(call):
                answer = await call
            else:
                answer = call

            records: list[str] = []
            if answer is not None:
                for r in answer:
                    if hasattr(r, "address"):
                        records.append(str(r.address).rstrip("."))
                    elif hasattr(r, "strings"):
                        txt_val = b"".join(r.strings).decode("utf-8", errors="replace")
                        records.append(txt_val)
                    elif hasattr(r, "to_text"):
                        records.append(r.to_text().rstrip("."))
                    else:
                        records.append(str(r).rstrip("."))
            return rdtype, records
        except Exception as e:
            return rdtype, e

    async def investigate(self, domain: str) -> DNSFinding:
        """Run A, AAAA, MX, NS, TXT lookups. Compose a DNSFinding.

        Never raises. All DNS exceptions (NXDOMAIN, NoAnswer, Timeout, Lifetime)
        are collected into `errors` and reflected in `status`:
          - OK: all five lookups succeeded (may still be empty lists for legit
            cases like no AAAA)
          - PARTIAL: at least one lookup succeeded and at least one failed
          - ERROR: all lookups failed, or the resolver itself failed
        `has_spf`: True if any TXT record starts with "v=spf1 " (case-insensitive),
        False if TXT lookups succeeded and none matched, None if TXT lookup failed.
        """
        with stopwatch() as sw:
            try:
                validated = validate_domain(domain)
                target_domain = validated.normalized
            except DomainValidationError as e:
                return DNSFinding(
                    agent_name="dns",
                    status=AgentStatus.ERROR,
                    errors=[f"Invalid domain: {e}"],
                    duration_ms=sw.elapsed_ms,
                    evidence=[],
                )

            try:
                resolver = self._get_resolver()
            except Exception as e:
                return DNSFinding(
                    agent_name="dns",
                    status=AgentStatus.ERROR,
                    errors=[f"Resolver initialization failed: {e.__class__.__name__}: {e}"],
                    duration_ms=sw.elapsed_ms,
                    evidence=[],
                )

            tasks = [self._resolve_type(resolver, target_domain, rdtype) for rdtype in RECORD_TYPES]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

            a_records: list[str] = []
            aaaa_records: list[str] = []
            mx_records: list[str] = []
            ns_records: list[str] = []
            txt_records: list[str] = []
            errors: list[str] = []

            succeeded_count = 0
            failed_count = 0
            txt_succeeded = False

            for item in raw_results:
                if isinstance(item, BaseException):
                    failed_count += 1
                    errors.append(f"Lookup task error: {item.__class__.__name__}: {item}")
                    continue

                rdtype, result = item
                if isinstance(result, Exception):
                    failed_count += 1
                    errors.append(f"{rdtype} lookup failed: {result.__class__.__name__}: {result}")
                else:
                    succeeded_count += 1
                    if rdtype == "A":
                        a_records = result
                    elif rdtype == "AAAA":
                        aaaa_records = result
                    elif rdtype == "MX":
                        mx_records = result
                    elif rdtype == "NS":
                        ns_records = result
                    elif rdtype == "TXT":
                        txt_records = result
                        txt_succeeded = True

            if succeeded_count == 5:
                status = AgentStatus.OK
            elif succeeded_count > 0:
                status = AgentStatus.PARTIAL
            else:
                status = AgentStatus.ERROR

            if txt_succeeded:
                has_spf = any(
                    rec.strip('"').strip("'").lower().startswith("v=spf1 ") for rec in txt_records
                )
            else:
                has_spf = None

            return DNSFinding(
                agent_name="dns",
                status=status,
                errors=errors,
                evidence=[],
                duration_ms=sw.elapsed_ms,
                a_records=a_records,
                aaaa_records=aaaa_records,
                mx_records=mx_records,
                txt_records=txt_records,
                ns_records=ns_records,
                has_spf=has_spf,
            )
