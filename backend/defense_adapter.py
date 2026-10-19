"""Compatibility boundary between the existing FastAPI app and the new shared pipeline."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live.adapter import screen_transcript
from models import ConversationSignals, ScreeningOutcome


def apply(transcript, caller_context, previous_scores: list[float] | None = None, raw_text: str = '') -> ScreeningOutcome:
    result = screen_transcript(transcript, caller_context, previous_scores, raw_text)
    # A clean risk score is not enough to pass an incomplete conversation.
    # This preserves the product behaviour of asking once for a missing purpose.
    tier = result['tier']
    if not transcript.sufficient_information and not transcript.harmful_request:
        tier = 'CONTINUE_SCREENING'
    follow_up = ''
    if tier in ('CONTINUE_SCREENING', 'WARN'):
        follow_up = 'Who are you calling on behalf of, and what do you need the recipient to do?'
    names = {item['type'] for item in result['signal_evidence']}
    features = ConversationSignals(
        impersonation='impersonation' in names,
        urgency='urgency' in names,
        credential_request='code_request' in names,
        payment_or_money_request='payment_request' in names,
        threatening_language='threat' in names,
        suspicious_action_request='suspicious_action' in names,
    )
    probability = result['probability']
    return ScreeningOutcome(
        final_risk_score=result['probability'], risk_score=result['probability'],
        transcript_risk_score=result['probability'], caller_context_risk_score=0.0,
        confidence=abs(probability - .5) * 2, detected_signals=result['signals'],
        features=features, signal_evidence=result['signal_evidence'], caller_context=caller_context,
        contributing_signals=result['signals'], decision_reason=result['reason'],
        explanation=transcript.explanation, decision=tier, follow_up_question=follow_up,
        latency_ms=transcript.latency_ms, classifier='Our classifier · Gemini explanation',
    )
