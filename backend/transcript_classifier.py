"""Transcript-classifier boundary.

Gemini is the initial implementation. Replacing it with a locally trained
classifier later only requires another implementation of `classify`.
"""
from typing import Awaitable, Callable, Protocol

from models import ConversationSignals, TranscriptResult
from scoring import analyze_transcript


class TranscriptClassifier(Protocol):
    async def classify(self, conversation: list[dict]) -> TranscriptResult: ...


def signals_from_evidence(features) -> ConversationSignals:
    return ConversationSignals(
        impersonation=features.financial_impersonation,
        urgency=features.urgency_or_pressure,
        credential_request=features.credential_or_otp_request,
        payment_or_money_request=features.money_transfer_request,
        threatening_language=features.threatening_language,
        suspicious_action_request=any((
            features.credential_or_otp_request,
            features.remote_access_request,
            features.money_transfer_request,
        )),
    )


class GeminiTranscriptClassifier:
    async def classify(self, conversation: list[dict]) -> TranscriptResult:
        evidence, model, latency_ms, _attempts, _usage = await analyze_transcript(conversation)
        return TranscriptResult(
            transcript_risk_score=evidence.risk_score,
            confidence=evidence.confidence,
            detected_signals=evidence.detected_signals,
            conversation_signals=signals_from_evidence(evidence.features),
            signal_evidence=evidence.signal_evidence,
            explanation=evidence.explanation,
            sufficient_information=evidence.sufficient_information,
            harmful_request=evidence.harmful_request,
            missing_information=evidence.missing_information,
            latency_ms=latency_ms,
            provider=f'Gemini transcript classifier ({model})',
        )


def result_from_assessment(assessment) -> TranscriptResult:
    """Adapt the existing evaluator result while the legacy endpoint remains."""
    return TranscriptResult(
        transcript_risk_score=assessment.risk_score,
        confidence=assessment.confidence,
        detected_signals=assessment.detected_signals,
        conversation_signals=signals_from_evidence(assessment.features),
        signal_evidence=getattr(assessment, 'signal_evidence', []),
        explanation=assessment.explanation,
        sufficient_information=assessment.sufficient_information,
        harmful_request=assessment.harmful_request,
        missing_information=assessment.missing_information,
        latency_ms=assessment.latency_ms,
        provider=f'Gemini transcript classifier ({assessment.model})',
    )


class LegacyAssessmentClassifier:
    """Compatibility adapter for the existing Gemini evaluator and test seam."""
    def __init__(self, assess: Callable[[list[dict]], Awaitable[object]]):
        self.assess = assess

    async def classify(self, conversation: list[dict]) -> TranscriptResult:
        return result_from_assessment(await self.assess(conversation))
