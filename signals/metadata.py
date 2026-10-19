"""Computed metadata features. No caller risk is set as a hidden constant."""
import math

from signals.schemas import MetadataSignals


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def wilson_lower(k: float, n: float, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    proportion = k / n
    denom = 1 + z * z / n
    centre = proportion + z * z / (2 * n)
    adjustment = z * math.sqrt((proportion * (1 - proportion) + z * z / (4 * n)) / n)
    return _clip((centre - adjustment) / denom)


def from_scenario(profile, reports, recipient_prefix: str) -> MetadataSignals:
    # Beta(1, 9) is a conservative prior: absent reports should not imply no risk.
    weighted_scam = sum(report.reporter_trust * report.verdict for report in reports)
    total_weight = sum(report.reporter_trust for report in reports)
    reputation = wilson_lower(weighted_scam + 1, total_weight + 10)
    expected = max(profile.hourly_rate, .05)
    z_score = (profile.calls_last_hour - expected) / math.sqrt(expected)
    anomaly = _clip(z_score / 6)
    spoof = 1.0 if profile.npa_nxx == recipient_prefix and profile.number_age_days < 30 else 0.0
    return MetadataSignals(reputation, anomaly, spoof, profile.is_contact)


def neutral_live_metadata() -> MetadataSignals:
    """Live calls have no reputation feed in this prototype; report that honestly."""
    return MetadataSignals(reputation_risk=0.0, frequency_anomaly=0.0, neighbor_spoof=0.0,
                           is_contact=False, source='unavailable-for-live-demo')
