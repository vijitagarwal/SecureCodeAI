import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.llm.base import ProviderError
from app.llm.gemini import GeminiSecurityProvider
from app.security.classification import classify_rule


CONTENT = {
    "finding_summary": "Dynamic evaluation", "root_cause": "Untrusted input reaches eval.",
    "security_impact": "Code execution if input is attacker-controlled.",
    "false_positive_assessment": "Check input provenance.", "remediation": "Parse JSON instead.",
    "fixed_code": "value = json.loads(data)", "diff": None, "confidence": 0.8,
}
CONTEXT = dict(rule_id="B307", title="eval usage", description="Review eval", snippet="1 eval(data)\n",
               classification=classify_rule("B307"), severity="MEDIUM", confidence="HIGH")


def response_payload(content=CONTENT, finish="STOP"):
    return {"candidates": [{"finishReason": finish, "content": {"parts": [{"text": json.dumps(content)}]}}]}


@pytest.fixture(autouse=True)
def configured_provider(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr("test-only-provider-key"))


def test_structured_request_and_response_boundary():
    def respond(request):
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.url.scheme == "https"
        assert not request.url.query
        assert request.headers["x-goog-api-key"] == "test-only-provider-key"
        payload = json.loads(request.content)
        assert "untrusted JSON data" in payload["systemInstruction"]["parts"][0]["text"]
        context = json.loads(payload["contents"][0]["parts"][0]["text"])
        assert context["scanner_severity"] == "MEDIUM"
        assert context["snippet"] == "1 eval(data)\n"
        assert "test-only-provider-key" not in request.content.decode()
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        return httpx.Response(200, json=response_payload())

    provider = GeminiSecurityProvider(transport=httpx.MockTransport(respond))
    result = provider.analyze(**CONTEXT)
    assert result.fixed_code == CONTENT["fixed_code"]


@pytest.mark.parametrize("status", [401, 429, 500, 302])
def test_http_failures_and_redirects_are_not_retried(status):
    calls = []
    def respond(request):
        calls.append(request)
        return httpx.Response(status, text="secret provider diagnostic", headers={"location": "https://other.example/"})
    provider = GeminiSecurityProvider(transport=httpx.MockTransport(respond))
    with pytest.raises(ProviderError, match="unavailable"):
        provider.analyze(**CONTEXT)
    assert len(calls) == 1


@pytest.mark.parametrize("payload", [
    {}, {"candidates": [None]}, response_payload(finish="MAX_TOKENS"),
    response_payload({**CONTENT, "confidence": 1.5}),
    response_payload({**CONTENT, "root_cause": ""}),
    response_payload({**CONTENT, "diff": "--- a/C:/secrets\n+++ b/C:/secrets"}),
    response_payload({**CONTENT, "unexpected_instruction": "ignore validation"}),
])
def test_untrusted_output_is_rejected(payload):
    provider = GeminiSecurityProvider(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
    with pytest.raises(ProviderError):
        provider.analyze(**CONTEXT)


def test_timeout_and_oversized_response():
    def timeout(request):
        raise httpx.ReadTimeout("provider secret")
    provider = GeminiSecurityProvider(transport=httpx.MockTransport(timeout))
    with pytest.raises(ProviderError):
        provider.analyze(**CONTEXT)
    provider = GeminiSecurityProvider(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * 140000)))
    with pytest.raises(ProviderError):
        provider.analyze(**CONTEXT)


def test_missing_credentials_fail_safely(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    with pytest.raises(ProviderError, match="not configured"):
        GeminiSecurityProvider()
