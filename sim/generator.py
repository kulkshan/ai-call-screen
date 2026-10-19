"""Create the reproducible 1,200-scenario corpus used by the harness."""
import random

from sim.adversary import paraphrase
from sim.numbers import RECIPIENT_PREFIX, build_profile
from sim.reporters import build_reporters, simulate_reports
from sim.schema import Scenario, Turn


SCAMS = {
    'bank_impersonation': ('I am calling from the fraud department at your bank.', 'Read me the one-time code we sent so I can secure your account.', ('impersonation', 'code_request')),
    'tech_support': ('I am from device support and noticed a security problem.', 'Install our support tool and let me control your screen to fix it.', ('impersonation', 'suspicious_action')),
    'lottery_prize': ('You have been selected for a prize that is waiting for release.', 'Pay the processing fee today so the prize does not expire.', ('payment_request', 'urgency')),
    'tax_authority': ('This is the tax office about a serious account issue.', 'Pay now or enforcement action will begin.', ('impersonation', 'payment_request', 'threat')),
    'delivery_fee': ('Your parcel cannot be delivered until a small charge is resolved.', 'Use the payment link now to release the delivery.', ('payment_request', 'urgency')),
    'utility_shutoff': ('This is the utility service about an unpaid balance.', 'Make a payment before service is turned off today.', ('impersonation', 'payment_request', 'threat')),
}

LEGIT = {
    'pharmacy_reminder': 'This is the pharmacy calling to say your prescription is ready for collection.',
    'school_alert': 'This is the school office with an attendance reminder. Please use the family portal for details.',
    'bank_fraud_callback': 'This is a fraud notice from your bank. Please use the number on the back of your card to review an alert. We will not ask for a code.',
    'delivery_notification': 'This is a delivery notification. Your parcel will be left at the usual location this afternoon.',
    'appointment_reminder': 'This is the clinic confirming your appointment tomorrow. Please use the usual number if you need to reschedule.',
    'two_factor_call': 'This is an automated login confirmation. Do not share a code with anyone; use the app if you did not request it.',
}


def _split_groups(groups: list[str], rng: random.Random) -> dict[str, str]:
    rng.shuffle(groups)
    train_end = round(len(groups) * .60)
    validation_end = train_end + round(len(groups) * .20)
    return {group: 'train' if index < train_end else 'validation' if index < validation_end else 'test'
            for index, group in enumerate(groups)}


def _scam_turns(intro: str, request: str, signals: tuple[str, ...], adversarial: bool) -> list[Turn]:
    opening = paraphrase(intro) if adversarial else intro
    action = paraphrase(request) if adversarial else request
    return [
        Turn('caller', opening, 'suspicious', ('impersonation',) if 'impersonation' in signals else ()),
        Turn('recipient', 'What is this regarding?', 'benign', ()),
        Turn('caller', 'I need to resolve this before the available window closes.' if adversarial else 'This needs prompt attention.', 'suspicious', ('urgency',) if ('urgency' in signals or adversarial) else ()),
        Turn('recipient', 'What do you need me to do?', 'benign', ()),
        Turn('caller', action, 'malicious', signals),
    ]


def _legit_turns(text: str, tricky: bool) -> list[Turn]:
    if tricky:
        text = text.replace('Please use', 'There is an urgent matter, but please use')
    return [Turn('caller', text, 'benign', ())]


def generate(seed: int = 20261003) -> list[Scenario]:
    rng = random.Random(seed)
    reporters = build_reporters(seed)
    scenarios: list[Scenario] = []
    groups: list[str] = []
    # 450 parent scam calls + 150 adversarial variants = 600 scam calls.
    for subtype, (intro, request, signals) in SCAMS.items():
        for index in range(75):
            group = f'scam-{subtype}-{index:03d}'
            groups.append(group)
            profile = build_profile(f'number-{group}', 'scam', index, rng)
            scenarios.append(Scenario(f'{group}-standard', group, 'scam', subtype, 'standard', 'scam', 5, None, profile, RECIPIENT_PREFIX, _scam_turns(intro, request, signals, False)))
            if index < 25:
                variant_profile = build_profile(f'number-{group}-variant', 'scam', index + 500, rng)
                scenarios.append(Scenario(f'{group}-adversarial', group, 'scam', subtype, 'adversarial', 'scam', 5, f'{group}-standard', variant_profile, RECIPIENT_PREFIX, _scam_turns(intro, request, signals, True)))
    # 450 standard legitimate + 150 difficult legitimate calls = 600 legitimate calls.
    for subtype, text in LEGIT.items():
        for index in range(100):
            group = f'legit-{subtype}-{index:03d}'
            groups.append(group)
            tricky = index >= 75
            difficulty = 'tricky_legit' if tricky else 'standard'
            profile = build_profile(f'number-{group}', 'legit', index, rng)
            scenarios.append(Scenario(f'{group}-{difficulty}', group, 'legit', subtype, difficulty, 'legit', None, None, profile, RECIPIENT_PREFIX, _legit_turns(text, tricky)))
    splits = _split_groups(groups, rng)
    for scenario in scenarios:
        scenario.split = splits[scenario.group_id]
        scenario.reports = simulate_reports(scenario.caller_profile.profile_id, scenario.label, scenario.split, reporters, rng)
    assert len(scenarios) == 1200
    return scenarios
