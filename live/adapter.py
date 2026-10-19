"""Run the same transcript classifier used by the locked offline test."""
from classifier.text_model import OurClassifier, extract_signals
from policy.cost_model import CostModel
from policy.evidence import assess as assess_evidence
from policy.tiers import decide
from signals.metadata import neutral_live_metadata


ACTION_MAP = {'ALLOW': 'ALLOW', 'MONITOR': 'CONTINUE_SCREENING', 'WARN': 'WARN', 'BLOCK': 'BLOCK'}
_CLASSIFIER = None


def _classifier():
    global _CLASSIFIER
    if _CLASSIFIER is None:
        _CLASSIFIER = OurClassifier()
    return _CLASSIFIER


def screen_transcript(transcript_result, caller_context, previous_scores: list[float] | None = None,
                      raw_text: str = '') -> dict:
    """Run Layers 1–3 for a real call.

    Gemini can still write a short explanation, but it no longer supplies the
    risk score.  The score comes from our locally trained transcript model.
    """
    metadata = neutral_live_metadata()
    probability = _classifier().probability(raw_text)
    evidence_quality = assess_evidence(raw_text)
    decision = decide(
        probability,
        [*(previous_scores or []), probability],
        CostModel(),
        evidence_sufficient=evidence_quality['sufficient'],
    )
    evidence = extract_signals(raw_text)
    signals = [item['type'].replace('_', ' ') for item in evidence]
    unavailable_note = 'Caller reputation is not available in this live prototype.'
    return {
        'probability': probability,
        'tier': ACTION_MAP[decision['tier']],
        'signals': signals,
        'metadata': metadata,
        'signal_evidence': evidence,
        'evidence_quality': evidence_quality,
        'decision': decision,
        'reason': f"{unavailable_note} Our classifier scored the raw transcript; the configured cost policy selected the action.",
    }
