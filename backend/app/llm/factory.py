from app.core.config import settings
from app.llm.base import LLMProvider, ProviderError
from app.llm.mock import MockSecurityProvider


def get_security_analysis_provider(provider_name: str | None = None) -> LLMProvider:
    selected_provider = (provider_name or settings.ai_provider).strip().lower()
    if selected_provider == "mock":
        return MockSecurityProvider()
    raise ProviderError(f"Unsupported security analysis provider: {selected_provider}")
