from abc import ABC, abstractmethod

from app.schemas.analysis import AnalysisResponse
from app.security.classification import Classification


class ProviderError(Exception):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def analyze(
        self,
        *,
        rule_id: str,
        title: str,
        description: str,
        snippet: str | None,
        classification: Classification,
    ) -> AnalysisResponse:
        """Analyze one finding without receiving credentials or filesystem paths."""
