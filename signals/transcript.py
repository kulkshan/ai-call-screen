"""Signal-only extractors. The fusion model, never this layer, assigns a tier."""
import json
import random

from signals.schemas import SIGNAL_TYPES, Signal, TurnSignals


_ALIASES = {
    'credential_request': 'code_request',
    'payment_or_money_request': 'payment_request',
    'threatening_language': 'threat',
    'suspicious_action_request': 'suspicious_action',
}


def _expected(turn) -> set[str]:
    return {_ALIASES.get(name, name) for name in turn.signals}


def simulated_extract(turn, turn_id: int, difficulty: str, seed: int) -> TurnSignals:
    """A seeded noisy LLM surrogate for reproducible offline evaluation.

    It receives only the generated expected signal labels plus a deterministic
    error process. That gives the judge an independently measurable error rate
    without claiming that it is a live Gemini result.
    """
    rng = random.Random(f'{seed}:{turn_id}:{turn.text}')
    expected = _expected(turn)
    sensitivity = .94 if difficulty == 'standard' else .79 if difficulty == 'adversarial' else .91
    false_positive = .015 if difficulty == 'standard' else .035 if difficulty == 'adversarial' else .05
    signals = []
    quote = turn.text[:160]
    for signal_type in SIGNAL_TYPES:
        should_find = signal_type in expected
        present = rng.random() < (sensitivity if should_find else false_positive)
        if present:
            confidence = round(rng.uniform(.63, .96) if should_find else rng.uniform(.40, .66), 3)
            evidence = quote
        else:
            confidence = 0.0
            evidence = ''
        signals.append(Signal(signal_type, present, confidence, evidence))
    payload = {'turn_id': turn_id, 'signals': [signal.to_dict() for signal in signals]}
    return TurnSignals(turn_id, signals, json.dumps(payload, separators=(',', ':')), 'synthetic-signal-extractor-v1')


def from_legacy_features(features, confidence: float, turn_id: int, evidence: str = '', signal_evidence=None) -> TurnSignals:
    """Translate the existing Gemini output into Layer 1 until its prompt emits
    per-signal evidence records directly. It still does not make a decision."""
    if signal_evidence:
        extracted = [Signal(item.type if hasattr(item, 'type') else item['type'], True,
                            item.confidence if hasattr(item, 'confidence') else item['confidence'],
                            item.evidence if hasattr(item, 'evidence') else item['evidence'])
                     for item in signal_evidence if (item.present if hasattr(item, 'present') else item.get('present'))]
        names = {signal.type for signal in extracted}
        extracted.extend(Signal(name, False, 0.0, '') for name in SIGNAL_TYPES if name not in names)
        return TurnSignals(turn_id, extracted, '', 'gemini-signal-extractor-v1')
    mapping = {
        'urgency': getattr(features, 'urgency_or_pressure', False),
        'impersonation': getattr(features, 'financial_impersonation', False),
        'payment_request': getattr(features, 'money_transfer_request', False),
        'code_request': getattr(features, 'credential_or_otp_request', False),
        'personal_info_request': False,
        'threat': getattr(features, 'threatening_language', False),
        'suspicious_action': getattr(features, 'remote_access_request', False) or getattr(features, 'money_transfer_request', False),
    }
    signals = [Signal(name, bool(present), round(confidence if present else 0.0, 3), evidence if present else '')
               for name, present in mapping.items()]
    return TurnSignals(turn_id, signals, '', 'gemini-legacy-signal-adapter-v1')
