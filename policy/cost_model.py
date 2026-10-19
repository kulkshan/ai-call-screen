"""Expected-cost policy. Changing the false-positive cost changes the cutoffs."""
from dataclasses import asdict, dataclass


TIERS = ('ALLOW', 'MONITOR', 'WARN', 'BLOCK')


@dataclass(frozen=True)
class CostModel:
    false_negative_cost: float = 1.0
    false_positive_cost: float = 50.0
    monitoring_cost: float = 0.02

    def costs(self) -> dict[str, dict[str, float]]:
        return {
            'ALLOW': {'scam': self.false_negative_cost, 'legit': 0.0},
            # Continuing to screen has a small user-experience cost. Without it,
            # MONITOR would dominate ALLOW at every non-zero probability.
            'MONITOR': {'scam': self.false_negative_cost / 2, 'legit': self.monitoring_cost},
            'WARN': {'scam': self.false_negative_cost / 3, 'legit': self.false_positive_cost / 5},
            'BLOCK': {'scam': 0.0, 'legit': self.false_positive_cost},
        }

    def expected_costs(self, scam_probability: float) -> dict[str, float]:
        return {tier: scam_probability * costs['scam'] + (1 - scam_probability) * costs['legit']
                for tier, costs in self.costs().items()}

    def choose(self, scam_probability: float) -> tuple[str, dict[str, float]]:
        costs = self.expected_costs(scam_probability)
        return min(TIERS, key=lambda tier: (costs[tier], TIERS.index(tier))), costs

    def to_dict(self) -> dict:
        return asdict(self)


def derive_thresholds(model: CostModel, step: float = .0005) -> dict[str, float | None]:
    """Find action switch points from the costs; no product threshold is hand-picked."""
    changes = {'monitor': None, 'warn': None, 'block': None}
    previous = 'ALLOW'
    steps = int(1 / step) + 1
    for index in range(steps):
        probability = min(1.0, index * step)
        tier, _ = model.choose(probability)
        if tier != previous:
            if tier == 'MONITOR' and changes['monitor'] is None:
                changes['monitor'] = probability
            elif tier == 'WARN' and changes['warn'] is None:
                changes['warn'] = probability
            elif tier == 'BLOCK' and changes['block'] is None:
                changes['block'] = probability
            previous = tier
    return changes
