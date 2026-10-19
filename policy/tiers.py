"""Apply expected-cost tiers and trajectory escalation."""
from policy.cost_model import CostModel, derive_thresholds
from policy.escalation import should_escalate


def decide(probability: float, history: list[float] | None = None, cost_model: CostModel | None = None,
           *, evidence_sufficient: bool = True) -> dict:
    cost_model = cost_model or CostModel()
    tier, expected_costs = cost_model.choose(probability)
    thresholds = derive_thresholds(cost_model)
    escalated = False
    if not evidence_sufficient:
        return {
            'tier': 'MONITOR',
            'expected_costs': expected_costs,
            'thresholds': thresholds,
            'escalated': False,
            'evidence_override': True,
        }
    warning_boundary = thresholds['warn'] if thresholds['warn'] is not None else 1.0
    if tier in ('ALLOW', 'MONITOR') and should_escalate(history or [], warning_boundary):
        tier = 'WARN'
        escalated = True
    return {
        'tier': tier,
        'expected_costs': expected_costs,
        'thresholds': thresholds,
        'escalated': escalated,
        'evidence_override': False,
    }
