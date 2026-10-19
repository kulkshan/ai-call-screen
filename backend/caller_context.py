"""Simulated caller-side context for the prototype.

The live demo has no caller-reputation source yet, so its values are neutral.
Controlled scenarios can supply explicit context to exercise the risk combiner.
"""
from models import CallerContext


def mask_number(number: str) -> str:
    digits = ''.join(char for char in number if char.isdigit())
    if not digits:
        return 'Unknown caller'
    return f'••• ••• {digits[-4:]}' if len(digits) >= 4 else 'Unknown caller'


def simulated_context(caller_number: str = '', *, known_contact: bool = False,
                      caller_reputation_score: float = .5,
                      prior_spam_reports: int = 0,
                      recent_call_frequency: int = 1) -> CallerContext:
    """Return a transparent neutral default or an explicit controlled-test value."""
    return CallerContext(
        caller_number=caller_number,
        caller_number_masked=mask_number(caller_number),
        known_contact=known_contact,
        caller_reputation_score=caller_reputation_score,
        prior_spam_reports=prior_spam_reports,
        recent_call_frequency=recent_call_frequency,
    )
