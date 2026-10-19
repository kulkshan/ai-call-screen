"""A noisy user-report process used only by the synthetic corpus."""
import random
from datetime import datetime, timedelta, timezone

from sim.schema import Report, Reporter


def build_reporters(seed: int = 20261003, count: int = 180) -> list[Reporter]:
    rng = random.Random(seed)
    reporters = []
    for index in range(count):
        mix = rng.random()
        a, b = (8, 2) if mix < .80 else (5, 5) if mix < .95 else (2, 8)
        split = ('train', 'validation', 'test')[index % 3]
        reporters.append(Reporter(f'reporter-{index:03d}', a, b, rng.uniform(.15, 1), split))
    return reporters


def simulate_reports(number_profile: str, label: str, split: str, reporters: list[Reporter], rng: random.Random) -> list[Report]:
    """Reports are imperfect observations, never the scenario label copied verbatim."""
    pool = [reporter for reporter in reporters if reporter.split == split]
    reports = []
    observed_probability = .52 if label == 'scam' else .12
    for reporter in pool:
        if rng.random() > observed_probability * reporter.activity:
            continue
        truthful = rng.random() < reporter.trust
        verdict = int(label == 'scam') if truthful else int(label != 'scam')
        timestamp = datetime(2026, 10, 1, tzinfo=timezone.utc) - timedelta(minutes=rng.randint(1, 50_000))
        reports.append(Report(reporter.reporter_id, number_profile, verdict, timestamp.isoformat(), reporter.trust))
        if len(reports) >= 8:
            break
    return reports
