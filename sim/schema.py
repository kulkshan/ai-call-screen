"""Data contracts for synthetic, labelled call scenarios."""
from dataclasses import asdict, dataclass, field
from typing import Literal


CallLabel = Literal['scam', 'legit']
Difficulty = Literal['standard', 'adversarial', 'tricky_legit']
TurnLabel = Literal['benign', 'suspicious', 'malicious']


@dataclass(frozen=True)
class Turn:
    speaker: Literal['caller', 'recipient']
    text: str
    turn_label: TurnLabel
    signals: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        data = asdict(self)
        data['signals'] = list(self.signals)
        return data


@dataclass(frozen=True)
class NumberProfile:
    profile_id: str
    number_age_days: int
    hourly_rate: float
    calls_last_hour: int
    burstiness: float
    npa_nxx: str
    is_contact: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Reporter:
    reporter_id: str
    reliability_a: float
    reliability_b: float
    activity: float
    split: str

    @property
    def trust(self) -> float:
        return self.reliability_a / (self.reliability_a + self.reliability_b)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Report:
    reporter_id: str
    number_profile: str
    verdict: int
    reported_at: str
    reporter_trust: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Scenario:
    scenario_id: str
    group_id: str
    archetype: CallLabel
    subtype: str
    difficulty: Difficulty
    label: CallLabel
    malicious_from_turn: int | None
    adversarial_variant_of: str | None
    caller_profile: NumberProfile
    recipient_npa_nxx: str
    turns: list[Turn] = field(default_factory=list)
    split: str = ''
    reports: list[Report] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'scenario_id': self.scenario_id,
            'group_id': self.group_id,
            'archetype': self.archetype,
            'subtype': self.subtype,
            'difficulty': self.difficulty,
            'label': self.label,
            'malicious_from_turn': self.malicious_from_turn,
            'adversarial_variant_of': self.adversarial_variant_of,
            'caller_profile': self.caller_profile.to_dict(),
            'recipient_npa_nxx': self.recipient_npa_nxx,
            'turns': [turn.to_dict() for turn in self.turns],
            'split': self.split,
            'reports': [report.to_dict() for report in self.reports],
        }
