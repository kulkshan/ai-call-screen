"""Action policy. Thresholds live in config/risk_policy.json, not code."""
from models import Decision
from risk_combiner import load_policy


QUESTIONS = {
    'identity_purpose': 'Who are you calling on behalf of, and what is the purpose of your call?',
    'requested_action': 'What would you like the recipient to do? Please do not share any private details.',
    'clarify_request': 'Please clarify the purpose of your request without sharing codes, passwords, or account details.',
    'none': 'Who are you calling on behalf of, and what do you need the recipient to do?',
}


def decide(final_risk_score: float, missing_information: str, policy: dict | None = None) -> tuple[Decision, str]:
    thresholds = (policy or load_policy())['thresholds']
    if final_risk_score >= thresholds['block']:
        return 'BLOCK', ''
    if final_risk_score >= thresholds['warn']:
        return 'WARN', QUESTIONS.get(missing_information, QUESTIONS['none'])
    if final_risk_score >= thresholds['continue_screening']:
        return 'CONTINUE_SCREENING', QUESTIONS.get(missing_information, QUESTIONS['none'])
    return 'ALLOW', ''
