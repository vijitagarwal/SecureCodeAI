import pytest

from app.llm.base import ProviderError
from app.llm.factory import get_security_analysis_provider
from app.llm.mock import MockSecurityProvider


def test_mock_provider_selection_returns_existing_mock_provider():
    provider = get_security_analysis_provider("mock")

    assert isinstance(provider, MockSecurityProvider)


def test_unknown_provider_selection_is_rejected_safely():
    with pytest.raises(ProviderError, match="Unsupported security analysis provider"):
        get_security_analysis_provider("unknown")
