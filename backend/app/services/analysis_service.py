import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db.models import Finding, SecurityAnalysis
from app.llm.base import LLMProvider, ProviderError
from app.schemas.analysis import AnalysisResponse
from app.security.classification import classify_rule

logger = logging.getLogger(__name__)


def analyze_finding(db: Session, finding: Finding, provider: LLMProvider) -> AnalysisResponse:
    try:
        try:
            provider_result = provider.analyze(
                rule_id=finding.rule_id,
                title=finding.title,
                description=finding.description,
                snippet=finding.code_snippet,
                classification=classify_rule(finding.rule_id),
            )
        except ProviderError:
            raise
        except Exception as error:
            raise ProviderError("Security analysis provider failed.") from error
        result = AnalysisResponse.model_validate(provider_result).model_copy(update={"finding_id": finding.id})
        record = SecurityAnalysis(
            finding_id=finding.id,
            status=result.status,
            finding_summary=result.finding_summary,
            root_cause=result.root_cause,
            security_impact=result.security_impact,
            false_positive_assessment=result.false_positive_assessment,
            remediation=result.remediation,
            fixed_code=result.fixed_code,
            diff=result.diff,
            confidence=result.confidence,
        )
        if finding.analysis is not None:
            db.delete(finding.analysis)
            db.flush()
        db.add(record)
        db.commit()
        db.refresh(record)
        return AnalysisResponse.model_validate(record)
    except (ProviderError, ValidationError, ValueError) as error:
        db.rollback()
        logger.warning("Security analysis provider returned invalid output: %s", type(error).__name__)
        raise ProviderError("Security analysis returned an invalid response.") from error
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to persist security analysis")
        raise ProviderError("Security analysis could not be stored.")
