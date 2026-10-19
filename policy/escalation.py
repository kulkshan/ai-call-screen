"""Turn-trajectory guardrail for calls that become dangerous mid-conversation."""


def should_escalate(history: list[float], warn_threshold: float, *, minimum_slope: float = .15) -> bool:
    if len(history) < 3 or history[-1] < warn_threshold:
        return False
    slope = (history[-1] - history[-3]) / 2
    return slope > minimum_slope
