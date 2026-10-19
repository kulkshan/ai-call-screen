"""Feature vector assembly used identically by evaluation and live calls."""
from signals.schemas import SIGNAL_TYPES


FEATURE_VERSION = 'call-screen-features-v1'
FEATURE_NAMES = [
    *[f'signal_{name}' for name in SIGNAL_TYPES],
    'mean_signal_confidence', 'reputation_risk', 'frequency_anomaly',
    'neighbor_spoof', 'not_contact', 'turn_fraction',
]


def build(turn_signals, metadata, turn_index: int, total_turns: int) -> list[float]:
    values = [turn_signals.confidence(signal) for signal in SIGNAL_TYPES]
    positives = [value for value in values if value > 0]
    return [
        *values,
        sum(positives) / len(positives) if positives else 0.0,
        metadata.reputation_risk,
        metadata.frequency_anomaly,
        metadata.neighbor_spoof,
        0.0 if metadata.is_contact else 1.0,
        min(1.0, turn_index / max(total_turns, 1)),
    ]
