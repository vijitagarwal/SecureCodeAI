import pytest
from pydantic import ValidationError

from app.schemas.analysis import AnalysisResponse
from app.security.diff_validation import contains_unsafe_diff_path


@pytest.mark.parametrize(
    "diff_text",
    [
        "diff --git a/../outside.py b/../outside.py\n--- a/../outside.py\n+++ b/../outside.py",
        "diff --git a/C:/Windows/system32/drivers/etc/hosts b/C:/Windows/system32/drivers/etc/hosts",
        "diff --git a/ok.py b/../outside.py\n--- a/ok.py\n+++ b/../outside.py",
        "diff --git a/\\\\server\\share\\outside.py b/\\\\server\\share\\outside.py",
        "--- /etc/passwd\n+++ /etc/passwd",
        "--- ..\\outside.py\n+++ ..\\outside.py",
        "--- a/C:/outside.py\n+++ b/C:/outside.py",
        'diff --git "a/../outside.py" "b/../outside.py"',
        "diff --git a/file.py",
        "not a diff",
        "diff --git a/ok.py b/ok.py\n--- a/ok.py\x00\n+++ b/ok.py",
    ],
)
def test_analysis_rejects_unsafe_diff_paths(diff_text):
    assert contains_unsafe_diff_path(diff_text)
    with pytest.raises(ValidationError):
        AnalysisResponse(
            id=1,
            finding_id=1,
            status="completed",
            finding_summary="summary",
            root_cause="cause",
            security_impact="impact",
            false_positive_assessment="review",
            remediation="fix",
            diff=diff_text,
            confidence=0.5,
            created_at="2026-01-01T00:00:00Z",
        )


def test_analysis_accepts_safe_relative_diff_paths():
    diff_text = "diff --git a/example.py b/example.py\n--- a/example.py\n+++ b/example.py"
    assert not contains_unsafe_diff_path(diff_text)
    analysis = AnalysisResponse(
        id=1,
        finding_id=1,
        status="completed",
        finding_summary="summary",
        root_cause="cause",
        security_impact="impact",
        false_positive_assessment="review",
        remediation="fix",
        diff=diff_text,
        confidence=0.5,
        created_at="2026-01-01T00:00:00Z",
    )
    assert analysis.diff == diff_text
