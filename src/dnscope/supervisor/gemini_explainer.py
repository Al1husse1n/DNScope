import json
from typing import Any

from google import genai

from dnscope.config import Settings
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.scoring import ScoreResult
from dnscope.supervisor.prompts import (
    build_response_schema,
    build_system_instruction,
    build_user_message,
)


class GeminiExplainer:
    """Explainer implementation backed by Google Gemini (google-genai SDK).

    Uses the new google-genai SDK (`from google import genai`), NOT the
    deprecated google-generativeai package.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: Any = None,
    ) -> None:
        """If api_key is None, read from Settings().gemini_api_key.

        If model is None, read from Settings().gemini_model.
        If client is None, construct genai.Client(api_key=api_key).
        If api_key is still None/empty after resolution, set
        self._available = False and short-circuit explain() to return
        'Narrative unavailable: GEMINI_API_KEY not set'. Do NOT raise.
        """
        settings = Settings()
        resolved_key = api_key if api_key is not None else settings.gemini_api_key
        self._model = model if model is not None else settings.gemini_model
        self._api_key = resolved_key

        if not resolved_key:
            self._available = False
            self._client = client
        else:
            self._available = True
            self._client = (
                client
                if client is not None
                else genai.Client(
                    api_key=resolved_key,
                    http_options={"api_version": "v1beta"},
                )
            )

    def __repr__(self) -> str:
        return f"GeminiExplainer(model={self._model!r}, available={self._available!r})"

    async def explain(
        self,
        domain: str,
        dns: DNSFinding | None,
        registration: RegistrationFinding | None,
        reputation: ReputationFinding | None,
        score_result: ScoreResult,
    ) -> str:
        """Call Gemini with structured output. Return narrative string.

        Never raises. Any exception -> 'Narrative unavailable: <type>: <msg>'.
        Any malformed response (no candidates, no text, no 'narrative' key,
        non-JSON content) -> 'Narrative unavailable: malformed response'.

        Steps:
          1. If not self._available -> return the fallback string, no API call.
          2. Build system instruction, user message, response schema via
             dnscope.supervisor.prompts.
          3. Call the async API:
             response = await self._client.aio.models.generate_content(
                 model=self._model,
                 contents=user_message,
                 config={
                     'system_instruction': system_instruction,
                     'response_mime_type': 'application/json',
                     'response_schema': response_schema,
                     'temperature': 0.2,
                 },
             )
          4. Parse response.text as JSON -> extract 'narrative'.
          5. If any step fails, return fallback string; never raise.

        Length guard: if narrative > 2000 chars, truncate to 2000 + '...'.
        """
        if not self._available or self._client is None:
            return "Narrative unavailable: GEMINI_API_KEY not set"

        system_instruction = build_system_instruction()
        user_message = build_user_message(domain, dns, registration, reputation, score_result)
        response_schema = build_response_schema()

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user_message,
                config={
                    "system_instruction": system_instruction,
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                    "temperature": 0.2,
                },
            )
        except Exception as exc:
            err_msg = str(exc)
            if self._api_key and self._api_key in err_msg:
                err_msg = err_msg.replace(self._api_key, "***")
            return f"Narrative unavailable: {type(exc).__name__}: {err_msg}"

        try:
            if hasattr(response, "candidates") and not response.candidates:
                return "Narrative unavailable: malformed response"

            text = getattr(response, "text", None)
            if not text or not isinstance(text, str):
                return "Narrative unavailable: malformed response"

            data = json.loads(text)
            if not isinstance(data, dict):
                return "Narrative unavailable: malformed response"

            narrative = data.get("narrative")
            if not isinstance(narrative, str) or not narrative.strip():
                return "Narrative unavailable: malformed response"

        except Exception:
            return "Narrative unavailable: malformed response"

        if len(narrative) > 2000:
            narrative = narrative[:2000] + "..."

        return narrative
