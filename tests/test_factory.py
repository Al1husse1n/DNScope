import logging

import pytest

from dnscope.config import Settings
from dnscope.factory import build_supervisor
from dnscope.supervisor.explainer import NullExplainer
from dnscope.supervisor.gemini_explainer import GeminiExplainer


# 1. NullExplainer when gemini_api_key is None
def test_factory_null_explainer_when_no_key() -> None:
    settings = Settings(gemini_api_key=None)
    supervisor = build_supervisor(settings)
    assert isinstance(supervisor._explainer, NullExplainer)


# 2. GeminiExplainer when gemini_api_key is provided
def test_factory_gemini_explainer_when_key_set() -> None:
    settings = Settings(gemini_api_key="fake-secret-key-12345")
    supervisor = build_supervisor(settings)
    assert isinstance(supervisor._explainer, GeminiExplainer)


# 3. Factory does not log the api_key
def test_factory_never_logs_api_key(caplog: pytest.LogCaptureFixture) -> None:
    secret = "super-secret-gemini-key-99999"
    settings = Settings(gemini_api_key=secret)
    with caplog.at_level(logging.INFO, logger="dnscope.factory"):
        build_supervisor(settings)

    for record in caplog.records:
        assert secret not in record.message
        assert secret not in str(record.__dict__)
