from datetime import UTC, datetime
from typing import Any

import httpx

from dnscope.agents.base import stopwatch
from dnscope.schemas.common import AgentStatus
from dnscope.schemas.findings import RegistrationFinding
from dnscope.validation import DomainValidationError, validate_domain


class RegistrationAgent:
    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self._injected_client = http_client
        self._timeout_seconds = timeout_seconds

    def _extract_registrar(self, data: dict[str, Any]) -> str | None:
        """Extract registrar name from entities[roles contains 'registrar'].vcardArray FN value."""
        entities = data.get("entities")
        if not isinstance(entities, list):
            return None

        for entity in entities:
            if not isinstance(entity, dict):
                continue
            roles = entity.get("roles")
            if isinstance(roles, list) and "registrar" in roles:
                vcard = entity.get("vcardArray")
                if isinstance(vcard, list) and len(vcard) > 1 and isinstance(vcard[1], list):
                    for prop in vcard[1]:
                        if (
                            isinstance(prop, list)
                            and len(prop) >= 4
                            and str(prop[0]).lower() == "fn"
                        ):
                            return str(prop[3])
        return None

    def _extract_events(
        self, data: dict[str, Any]
    ) -> tuple[str | None, str | None, int | None, list[str]]:
        """Extract created_at, expires_at, and compute age_days.

        Returns (created_at, expires_at, age_days, errors).
        """
        events = data.get("events")
        if not isinstance(events, list) or len(events) == 0:
            return None, None, None, ["RDAP response missing events"]

        created_at_str: str | None = None
        expires_at_str: str | None = None
        created_at_dt: datetime | None = None
        errors: list[str] = []

        for ev in events:
            if not isinstance(ev, dict):
                continue
            action = ev.get("eventAction")
            date_raw = ev.get("eventDate")
            if not isinstance(date_raw, str):
                continue

            if action == "registration":
                created_at_str = date_raw
                try:
                    norm = date_raw.replace("Z", "+00:00")
                    created_at_dt = datetime.fromisoformat(norm)
                except Exception as e:
                    errors.append(f"Failed to parse registration event date: {e}")
            elif action == "expiration":
                expires_at_str = date_raw

        age_days: int | None = None
        if created_at_dt is not None:
            now_utc = datetime.now(UTC)
            if created_at_dt.tzinfo is None:
                created_at_dt = created_at_dt.replace(tzinfo=UTC)
            delta = now_utc - created_at_dt
            age_days = int(delta.days)

        return created_at_str, expires_at_str, age_days, errors

    async def investigate(self, domain: str) -> RegistrationFinding:
        """Query RDAP for registration metadata.

        Flow:
          1. Try https://rdap.org/domain/{domain} (redirector — follows redirects).
          2. If 404 → status=PARTIAL, errors=["domain not found in RDAP"].
          3. If timeout / 5xx → status=ERROR, errors=[...].
          4. On 200: extract registrar name, events (registration / expiration),
             compute age_days from registration event to today (UTC).
        Never raises. `created_at` / `expires_at` are ISO-8601 date strings.
        `age_days` is an int if created_at parses, else None.
        """
        with stopwatch() as sw:
            try:
                validated = validate_domain(domain)
                target_domain = validated.normalized
            except DomainValidationError as e:
                return RegistrationFinding(
                    agent_name="registration",
                    status=AgentStatus.ERROR,
                    errors=[f"invalid domain: {e}"],
                    duration_ms=sw.elapsed_ms,
                    evidence=[],
                )

            headers = {
                "Accept": "application/rdap+json",
                "User-Agent": "dnscope/0.1 (+https://github.com/ali/dnscope)",
            }
            url = f"https://rdap.org/domain/{target_domain}"

            owns_client = self._injected_client is None
            client = self._injected_client or httpx.AsyncClient(
                follow_redirects=True,
                timeout=self._timeout_seconds,
            )

            try:
                try:
                    response = await client.get(url, headers=headers)
                except httpx.TimeoutException as e:
                    return RegistrationFinding(
                        agent_name="registration",
                        status=AgentStatus.ERROR,
                        errors=[f"RDAP request timeout: {e.__class__.__name__}: {e}"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )
                except httpx.HTTPError as e:
                    return RegistrationFinding(
                        agent_name="registration",
                        status=AgentStatus.ERROR,
                        errors=[f"RDAP HTTP error: {e.__class__.__name__}: {e}"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                if response.status_code == 404:
                    return RegistrationFinding(
                        agent_name="registration",
                        status=AgentStatus.PARTIAL,
                        errors=["domain not found in RDAP"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                if response.status_code >= 500:
                    return RegistrationFinding(
                        agent_name="registration",
                        status=AgentStatus.ERROR,
                        errors=[f"RDAP server error: HTTP {response.status_code}"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                if response.status_code != 200:
                    return RegistrationFinding(
                        agent_name="registration",
                        status=AgentStatus.ERROR,
                        errors=[f"RDAP query failed with HTTP {response.status_code}"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                try:
                    data = response.json()
                except Exception as e:
                    return RegistrationFinding(
                        agent_name="registration",
                        status=AgentStatus.ERROR,
                        errors=[f"Failed to parse RDAP JSON: {e}"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                registrar = self._extract_registrar(data)
                created_at, expires_at, age_days, event_errors = self._extract_events(data)

                if event_errors:
                    status = AgentStatus.PARTIAL
                    errors = event_errors
                else:
                    status = AgentStatus.OK
                    errors = []

                return RegistrationFinding(
                    agent_name="registration",
                    status=status,
                    errors=errors,
                    evidence=[],
                    duration_ms=sw.elapsed_ms,
                    created_at=created_at,
                    expires_at=expires_at,
                    registrar=registrar,
                    age_days=age_days,
                )
            finally:
                if owns_client:
                    await client.aclose()
