from typing import Any

import httpx

from dnscope.agents.base import stopwatch
from dnscope.schemas.common import AgentStatus
from dnscope.schemas.findings import ReputationFinding
from dnscope.validation import DomainValidationError, validate_domain

VIRUSTOTAL_BASE_URL = "https://www.virustotal.com/api/v3/domains/"


class ReputationAgent:
    def __init__(
        self,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 10.0,
        base_url: str = VIRUSTOTAL_BASE_URL,
    ) -> None:
        """`api_key` is required to actually query VT. `base_url` is injectable
        for tests but MUST default to VIRUSTOTAL_BASE_URL and callers must not
        override it outside tests. If `api_key` is None or empty string, the
        agent will return ReputationFinding(status=SKIPPED, errors=["missing
        VT_API_KEY"]) without making any HTTP call."""
        self._api_key = api_key
        self._injected_client = http_client
        self._timeout_seconds = timeout_seconds
        self._base_url = base_url

    def __repr__(self) -> str:
        # Never leak api_key in repr
        return (
            f"ReputationAgent(base_url={self._base_url!r}, timeout_seconds={self._timeout_seconds})"
        )

    def _extract_stats(
        self, attributes: dict[str, Any] | None
    ) -> tuple[int | None, int | None, int | None]:
        """Extract (malicious, suspicious, total_engines).

        If last_analysis_stats is missing or empty, total_engines is None.
        If present, total_engines is the sum of integer values.
        """
        if not isinstance(attributes, dict):
            return None, None, None

        stats = attributes.get("last_analysis_stats")
        if not isinstance(stats, dict) or not stats:
            return None, None, None

        detections_malicious: int | None = None
        detections_suspicious: int | None = None

        mal = stats.get("malicious")
        if isinstance(mal, int):
            detections_malicious = mal

        susp = stats.get("suspicious")
        if isinstance(susp, int):
            detections_suspicious = susp

        int_values = [v for v in stats.values() if isinstance(v, int)]
        total_engines = sum(int_values)

        return detections_malicious, detections_suspicious, total_engines

    def _extract_categories(self, attributes: dict[str, Any] | None) -> list[str]:
        """Extract deduplicated category values from data.attributes.categories."""
        if not isinstance(attributes, dict):
            return []

        cats = attributes.get("categories")
        if not isinstance(cats, dict):
            return []

        seen: set[str] = set()
        result: list[str] = []
        for val in cats.values():
            if isinstance(val, str) and val and val not in seen:
                seen.add(val)
                result.append(val)
        return result

    def _extract_permalink(self, data: dict[str, Any] | None) -> str | None:
        """Extract permalink from data.links.self."""
        if not isinstance(data, dict):
            return None
        links = data.get("links")
        if isinstance(links, dict):
            self_link = links.get("self")
            if isinstance(self_link, str):
                return self_link
        return None

    async def investigate(self, domain: str) -> ReputationFinding:
        """Query VirusTotal for domain reputation."""
        with stopwatch() as sw:
            # 1. Pre-flight: Validate domain
            try:
                validated = validate_domain(domain)
                target_domain = validated.normalized
            except DomainValidationError as e:
                return ReputationFinding(
                    agent_name="reputation",
                    status=AgentStatus.ERROR,
                    errors=[f"invalid domain: {e}"],
                    duration_ms=sw.elapsed_ms,
                    evidence=[],
                )

            # 2. Pre-flight: Check API key
            if not self._api_key:
                return ReputationFinding(
                    agent_name="reputation",
                    status=AgentStatus.SKIPPED,
                    errors=["missing VT_API_KEY"],
                    duration_ms=sw.elapsed_ms,
                    evidence=[],
                )

            # 3. HTTP Request
            url = f"{self._base_url}{target_domain}"
            headers = {
                "x-apikey": self._api_key,
                "Accept": "application/json",
            }

            owns_client = self._injected_client is None
            client = self._injected_client or httpx.AsyncClient(
                timeout=self._timeout_seconds,
            )

            try:
                try:
                    response = await client.get(url, headers=headers)
                except httpx.TimeoutException:
                    return ReputationFinding(
                        agent_name="reputation",
                        status=AgentStatus.ERROR,
                        errors=[f"VirusTotal timeout after {self._timeout_seconds}s"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )
                except httpx.HTTPError as e:
                    return ReputationFinding(
                        agent_name="reputation",
                        status=AgentStatus.ERROR,
                        errors=[f"VirusTotal HTTP error: {e.__class__.__name__}"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                # Status code mapping
                if response.status_code == 404:
                    return ReputationFinding(
                        agent_name="reputation",
                        status=AgentStatus.PARTIAL,
                        errors=["domain not found in VirusTotal"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                if response.status_code in (401, 403):
                    return ReputationFinding(
                        agent_name="reputation",
                        status=AgentStatus.ERROR,
                        errors=[f"VirusTotal auth failed: {response.status_code}"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                if response.status_code == 429:
                    return ReputationFinding(
                        agent_name="reputation",
                        status=AgentStatus.ERROR,
                        errors=["VirusTotal rate limit (429)"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                if response.status_code != 200:
                    return ReputationFinding(
                        agent_name="reputation",
                        status=AgentStatus.ERROR,
                        errors=[f"VirusTotal HTTP {response.status_code}"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                # Parse JSON
                try:
                    payload = response.json()
                except Exception:
                    return ReputationFinding(
                        agent_name="reputation",
                        status=AgentStatus.ERROR,
                        errors=["VirusTotal returned malformed JSON"],
                        duration_ms=sw.elapsed_ms,
                        evidence=[],
                    )

                data = payload.get("data") if isinstance(payload, dict) else None
                attributes = data.get("attributes") if isinstance(data, dict) else None

                det_mal, det_susp, total_engines = self._extract_stats(attributes)
                categories = self._extract_categories(attributes)
                permalink = self._extract_permalink(data)

                return ReputationFinding(
                    agent_name="reputation",
                    status=AgentStatus.OK,
                    errors=[],
                    evidence=[],
                    duration_ms=sw.elapsed_ms,
                    detections_malicious=det_mal,
                    detections_suspicious=det_susp,
                    total_engines=total_engines,
                    categories=categories,
                    permalink=permalink,
                )
            finally:
                if owns_client:
                    await client.aclose()
