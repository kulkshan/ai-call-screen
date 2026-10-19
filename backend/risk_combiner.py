"""Deterministic risk calculation configured by config/risk_policy.json."""
import json
from pathlib import Path

from models import CallerContext, CombinedRisk, TranscriptResult

CONFIG_PATH = Path(__file__).with_name('config') / 'risk_policy.json'


def load_policy() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def combine(transcript: TranscriptResult, caller: CallerContext, policy: dict | None = None) -> CombinedRisk:
    policy = policy or load_policy()
    weights = policy['weights']
    normal = policy['normalization']
    report_risk = clamp(caller.prior_spam_reports / normal['prior_spam_reports_cap'])
    frequency_risk = clamp(caller.recent_call_frequency / normal['recent_call_frequency_cap'])
    caller_context_risk = clamp(
        weights['caller_reputation'] * caller.caller_reputation_score
        + weights['prior_spam_reports'] * report_risk
        + weights['call_frequency'] * frequency_risk
        + (weights['known_contact_adjustment'] if caller.known_contact else 0)
    )
    final = clamp(weights['transcript_risk'] * transcript.transcript_risk_score + caller_context_risk)
    signals = list(transcript.detected_signals)
    if caller.prior_spam_reports:
        signals.append(f'{caller.prior_spam_reports} prior spam report(s) in simulated caller context')
    if caller.recent_call_frequency >= normal['recent_call_frequency_cap']:
        signals.append('High recent call frequency in simulated caller context')
    if caller.known_contact:
        signals.append('Known contact in simulated caller context')
    reason = 'Transcript evidence is the primary contributor.'
    if caller_context_risk > .1:
        reason += ' Simulated caller context increased the score.'
    elif caller.known_contact:
        reason += ' Simulated known-contact context reduced the score.'
    return CombinedRisk(
        final_risk_score=final,
        transcript_risk_score=transcript.transcript_risk_score,
        caller_context_risk_score=caller_context_risk,
        contributing_signals=signals[:8],
        decision_reason=reason,
    )
