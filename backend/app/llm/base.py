from abc import ABC, abstractmethod

from app.schemas.analysis import AnalysisContent
from app.security.classification import Classification


class ProviderError(Exception):
    pass


class LLMProvider(ABC):
    name: str = "mock"
    model: str | None = None

    @abstractmethod
    def analyze(
        self,
        *,
        rule_id: str,
        title: str,
        description: str,
        snippet: str | None,
        classification: Classification,
        severity: str = "UNKNOWN",
        confidence: str = "UNKNOWN",
    ) -> AnalysisContent:
        """Analyze one finding without receiving credentials or filesystem paths."""
