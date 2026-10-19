"""Create the fixed 1,000-case simulated test set for the multi-signal demo.

This creates test inputs and expected actions only. It does not call Gemini,
Twilio, or any external service.
"""
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data' / 'multisignal-call-screen-v1.jsonl'
MANIFEST = ROOT / 'data' / 'multisignal-call-screen-v1.manifest.json'
PER_ACTION = 250
SOURCE = ROOT / 'data' / 'call-screen-simulated-v1.jsonl'

CASES = {
    'ALLOW': {
        'label': 0,
        'texts': [
            'This is {place} confirming your appointment on {day} at {time}. Use the usual office number if you need to reschedule.',
            'A reminder from {place}: your scheduled visit is {day} at {time}. No information is needed on this call.',
            'This is {place} returning your call about a routine appointment. Please use the number you already have for questions.',
        ],
        'contexts': [
            {'known_contact': True, 'caller_reputation_score': .05, 'prior_spam_reports': 0, 'recent_call_frequency': 1},
            {'known_contact': False, 'caller_reputation_score': .2, 'prior_spam_reports': 0, 'recent_call_frequency': 2},
        ],
    },
    'CONTINUE_SCREENING': {
        'label': None,
        'texts': [
            'I am calling about your account and need to discuss an update.',
            'There is a service matter to sort out. Please return this call.',
            'This is customer support. I have an update but need to speak with you first.',
        ],
        'contexts': [
            {'known_contact': False, 'caller_reputation_score': .45, 'prior_spam_reports': 0, 'recent_call_frequency': 2},
            {'known_contact': False, 'caller_reputation_score': .55, 'prior_spam_reports': 1, 'recent_call_frequency': 3},
        ],
    },
    'WARN': {
        'label': None,
        'texts': [
            'I am from account support. There is unusual activity and we need to verify a few details before the account changes.',
            'Your account may have a problem. Please stay on the line so we can sort it out before the notice expires.',
            'This is a security follow-up. We need to discuss an urgent account concern with you today.',
        ],
        'contexts': [
            {'known_contact': False, 'caller_reputation_score': .8, 'prior_spam_reports': 3, 'recent_call_frequency': 6},
            {'known_contact': False, 'caller_reputation_score': .9, 'prior_spam_reports': 2, 'recent_call_frequency': 7},
        ],
    },
    'BLOCK': {
        'label': 1,
        'texts': [
            'This is your bank security team. Read me the one-time code we sent so I can secure the account.',
            'Install the support application and give me control of your screen so I can fix the account issue.',
            'Move the balance to the safe account I provide before the payment is taken.',
            'Buy prepaid gift cards and tell me the numbers today to avoid the penalty.',
        ],
        'contexts': [
            {'known_contact': False, 'caller_reputation_score': .2, 'prior_spam_reports': 0, 'recent_call_frequency': 1},
            {'known_contact': False, 'caller_reputation_score': .85, 'prior_spam_reports': 4, 'recent_call_frequency': 8},
        ],
    },
}

PLACES = ('the dental office', 'the clinic', 'the optometrist', 'the therapy office')
DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')
TIMES = ('9 a.m.', '10 a.m.', '1 p.m.', '2:30 p.m.', '4 p.m.')


def text_for(action: str, index: int) -> str:
    template = CASES[action]['texts'][index % len(CASES[action]['texts'])]
    return template.format(place=PLACES[index % len(PLACES)], day=DAYS[index % len(DAYS)], time=TIMES[index % len(TIMES)])


def build() -> list[dict]:
    """Draw a fixed 1,000-row evaluation sample from the existing unique texts.

    The source corpus is used only as a text pool. This script evaluates 1,000
    rows, not the earlier 10,000-row corpus.
    """
    if not SOURCE.exists():
        raise RuntimeError(f'Missing source text pool: {SOURCE}')
    source = [json.loads(line) for line in SOURCE.read_text(encoding='utf-8').splitlines() if line.strip()]
    rng = random.Random(20260930)
    normal = [row for row in source if row['call_type'] == 'normal']
    unclear = [row for row in source if row['call_type'] == 'unclear']
    harmful = [row for row in source if row['call_type'] == 'harmful']
    for group in (normal, unclear, harmful):
        rng.shuffle(group)
    selections = {
        'ALLOW': normal[:PER_ACTION],
        'CONTINUE_SCREENING': unclear[:PER_ACTION],
        'WARN': unclear[PER_ACTION:PER_ACTION * 2],
        'BLOCK': harmful[:PER_ACTION],
    }
    contexts = {
        'ALLOW': ({'known_contact': True, 'caller_reputation_score': .05, 'prior_spam_reports': 0, 'recent_call_frequency': 1},
                  {'known_contact': False, 'caller_reputation_score': .2, 'prior_spam_reports': 0, 'recent_call_frequency': 2}),
        'CONTINUE_SCREENING': ({'known_contact': False, 'caller_reputation_score': .45, 'prior_spam_reports': 0, 'recent_call_frequency': 2},
                               {'known_contact': False, 'caller_reputation_score': .55, 'prior_spam_reports': 1, 'recent_call_frequency': 3}),
        'WARN': ({'known_contact': False, 'caller_reputation_score': .8, 'prior_spam_reports': 3, 'recent_call_frequency': 6},
                 {'known_contact': False, 'caller_reputation_score': .9, 'prior_spam_reports': 2, 'recent_call_frequency': 7}),
        'BLOCK': ({'known_contact': False, 'caller_reputation_score': .2, 'prior_spam_reports': 0, 'recent_call_frequency': 1},
                  {'known_contact': False, 'caller_reputation_score': .85, 'prior_spam_reports': 4, 'recent_call_frequency': 8}),
    }
    rows = []
    for action, selected in selections.items():
        for index, source_row in enumerate(selected):
            context = contexts[action][index % len(contexts[action])]
            rows.append({
                'id': f'multisignal-v1-{action.lower()}-{index + 1:04d}',
                'split': 'evaluation',
                'conversation': source_row['conversation'],
                'caller_context': context,
                'expected_decision': action,
                'label': 1 if action == 'BLOCK' else 0 if action == 'ALLOW' else None,
                'source': f"simulated multi-signal sample from {source_row['id']}",
            })
    if len(rows) != 1000:
        raise RuntimeError('Expected exactly 1,000 rows.')
    if len({row['conversation'][0]['text'] for row in rows}) != 1000:
        raise RuntimeError('Expected 1,000 unique transcripts.')
    return rows


def write(rows: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(''.join(json.dumps(row, separators=(',', ':')) + '\n' for row in rows), encoding='utf-8')
    manifest = {
        'version': 'multisignal-call-screen-v1',
        'record_count': len(rows),
        'sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(),
        'counts_by_expected_action': dict(Counter(row['expected_decision'] for row in rows)),
        'provenance': 'Programmatic simulated test cases. No real callers, phone numbers, Twilio events, or Gemini outputs.',
        'limitations': [
            'Caller context is simulated and is not a real reputation service.',
            'Expected actions are author-assigned for a controlled product test.',
            'This set cannot estimate real-world scam prevalence or production performance.',
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    write(build())
    print(json.dumps({'records': 1000, 'output': str(OUT), 'manifest': str(MANIFEST)}))
