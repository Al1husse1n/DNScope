import logging

from dnscope.config import Settings
from dnscope.supervisor.agent import SupervisorAgent
from dnscope.supervisor.explainer import Explainer, NullExplainer
from dnscope.supervisor.gemini_explainer import GeminiExplainer

logger = logging.getLogger("dnscope.factory")


def build_supervisor(settings: Settings) -> SupervisorAgent:
    """If settings.gemini_api_key is set and non-empty, use GeminiExplainer.

    Otherwise use NullExplainer. Log which explainer was selected at INFO level
    (but NEVER log the key).
    """
    explainer: Explainer
    if settings.gemini_api_key and settings.gemini_api_key.strip():
        logger.info(
            "Selected explainer: GeminiExplainer (model=%s)",
            settings.gemini_model,
        )
        explainer = GeminiExplainer(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
    else:
        logger.info("Selected explainer: NullExplainer (GEMINI_API_KEY not configured)")
        explainer = NullExplainer()

    return SupervisorAgent(explainer=explainer)
