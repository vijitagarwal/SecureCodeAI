import difflib
import logging
import re

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Finding, SecurityAnalysis
from app.llm.base import LLMProvider, ProviderError
from app.schemas.analysis import AnalysisContent, AnalysisResponse
from app.security.classification import classify_rule

logger = logging.getLogger(__name__)


def analyze_finding(db: Session, finding: Finding, provider: LLMProvider) -> AnalysisResponse:
    finding_id = finding.id
    try:
        existing = db.scalar(select(SecurityAnalysis).where(SecurityAnalysis.finding_id == finding_id))
        if existing is not None:
            return AnalysisResponse.model_validate(existing)
        # Do not hold a database transaction or row lock across provider I/O.
        # Concurrent requests may both calculate guidance; the unique finding_id
        # constraint makes the first committed result authoritative.
        context = {
            "rule_id": finding.rule_id,
            "title": finding.title,
            "description": finding.description,
            "snippet": finding.code_snippet,
            "classification": classify_rule(finding.rule_id),
            "severity": finding.severity.value,
            "confidence": finding.confidence.value,
        }
        db.rollback()
        try:
            output = provider.analyze(**context)
        except ProviderError:
            raise
        except Exception as error:
            raise ProviderError("Security analysis provider failed.") from error
        # Revalidate a dict, including model instances constructed without validation.
        content = AnalysisContent.model_validate(output.model_dump() if isinstance(output, AnalysisContent) else output)
        if content.fixed_code and finding.code_snippet:
            original = re.sub(r"(?m)^\d+ ", "", finding.code_snippet)
            diff = "".join(difflib.unified_diff(
                (original.rstrip("\n") + "\n").splitlines(keepends=True),
                (content.fixed_code.rstrip("\n") + "\n").splitlines(keepends=True),
                fromfile="a/snippet.py", tofile="b/snippet.py",
            ))
            content = AnalysisContent.model_validate({**content.model_dump(), "diff": diff or None})
        record = SecurityAnalysis(
            finding_id=finding_id, status="completed", provider=provider.name, model=provider.model,
            **content.model_dump(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return AnalysisResponse.model_validate(record)
    except IntegrityError as error:
        db.rollback()
        existing = db.scalar(select(SecurityAnalysis).where(SecurityAnalysis.finding_id == finding_id))
        if existing is not None:
            return AnalysisResponse.model_validate(existing)
        raise ProviderError("Security analysis could not be stored.") from error
    except (ProviderError, ValidationError, ValueError) as error:
        db.rollback()
        logger.warning("Security analysis failed validation or provider request")
        raise ProviderError("Security analysis returned an invalid response.") from error
    except SQLAlchemyError as error:
        db.rollback()
        logger.error("Security analysis persistence failed")
        raise ProviderError("Security analysis could not be stored.") from error
