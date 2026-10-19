"""Coordinates the separate screening layers for one completed caller turn."""
from caller_context import simulated_context
from decision_policy import decide
from models import CallerContext, ScreeningOutcome
from risk_combiner import combine
from transcript_classifier import GeminiTranscriptClassifier, TranscriptClassifier


async def screen(conversation: list[dict], caller: CallerContext | None = None,
                 classifier: TranscriptClassifier | None = None) -> ScreeningOutcome:
    caller = caller or simulated_context()
    transcript = await (classifier or GeminiTranscriptClassifier()).classify(conversation)
    combined = combine(transcript, caller)
    decision, follow_up_question = decide(combined.final_risk_score, transcript.missing_information)
    return ScreeningOutcome(
        final_risk_score=combined.final_risk_score,
        risk_score=combined.final_risk_score,
        transcript_risk_score=combined.transcript_risk_score,
        caller_context_risk_score=combined.caller_context_risk_score,
        confidence=transcript.confidence,
        detected_signals=transcript.detected_signals,
        features=transcript.conversation_signals,
        signal_evidence=transcript.signal_evidence,
        caller_context=caller,
        contributing_signals=combined.contributing_signals,
        decision_reason=combined.decision_reason,
        explanation=transcript.explanation,
        decision=decision,
        follow_up_question=follow_up_question,
        latency_ms=transcript.latency_ms,
        classifier=transcript.provider,
    )
