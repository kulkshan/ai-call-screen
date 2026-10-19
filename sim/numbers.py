"""Generate stable caller-number behaviour profiles from a deterministic seed."""
import math
import random

from sim.schema import NumberProfile


RECIPIENT_PREFIX = '628295'


def _poisson(rng: random.Random, rate: float) -> int:
    # Knuth's sampler keeps this project dependency-free and deterministic.
    limit = math.exp(-rate)
    product = 1.0
    count = 0
    while product > limit:
        count += 1
        product *= rng.random()
    return count - 1


def build_profile(profile_id: str, label: str, index: int, rng: random.Random) -> NumberProfile:
    if label == 'scam':
        age = rng.randint(1, 75)
        hourly_rate = round(rng.uniform(5.0, 15.0), 2)
        calls = _poisson(rng, hourly_rate * rng.uniform(1.1, 2.0))
        burstiness = round(rng.uniform(.65, .98), 2)
        prefix = RECIPIENT_PREFIX if index % 3 == 0 else f'{rng.randint(200, 999)}{rng.randint(200, 999)}'
        contact = False
    else:
        age = rng.randint(365, 6000)
        hourly_rate = round(rng.uniform(.1, 2.4), 2)
        calls = _poisson(rng, hourly_rate * rng.uniform(.45, 1.4))
        burstiness = round(rng.uniform(.02, .35), 2)
        prefix = RECIPIENT_PREFIX if index % 5 == 0 else f'{rng.randint(200, 999)}{rng.randint(200, 999)}'
        contact = index % 4 == 0
    return NumberProfile(profile_id, age, hourly_rate, calls, burstiness, prefix, contact)
