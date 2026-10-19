"""Structured signal records shared by batch and live pipelines."""
from dataclasses import asdict, dataclass, field


SIGNAL_TYPES = (
    'urgency', 'impersonation', 'payment_request', 'code_request',
    'personal_info_request', 'threat', 'suspicious_action',
)


@dataclass(frozen=True)
class Signal:
    type: str
    present: bool
    confidence: float
    evidence: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TurnSignals:
    turn_id: int
    signals: list[Signal] = field(default_factory=list)
    raw_response: str = ''
    extractor_version: str = 'synthetic-signal-extractor-v1'

    def confidence(self, signal_type: str) -> float:
        for signal in self.signals:
            if signal.type == signal_type:
                return signal.confidence if signal.present else 0.0
        return 0.0

    def to_dict(self) -> dict:
        return {
            'turn_id': self.turn_id,
            'signals': [signal.to_dict() for signal in self.signals],
            'raw_response': self.raw_response,
            'extractor_version': self.extractor_version,
        }


@dataclass(frozen=True)
class MetadataSignals:
    reputation_risk: float
    frequency_anomaly: float
    neighbor_spoof: float
    is_contact: bool
    source: str = 'simulated-computed'

    def to_dict(self) -> dict:
        return asdict(self)
