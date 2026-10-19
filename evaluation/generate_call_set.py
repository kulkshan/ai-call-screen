"""Create the reproducible simulated Call Screen evaluation corpus.

This generator makes no network requests and never calls Gemini or Twilio.
The corpus is intentionally stratified for classification evaluation; it is
not a sample of real calling prevalence and must not be used to claim product
performance or an experiment result.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data' / 'call-screen-simulated-v1.jsonl'
MANIFEST = ROOT / 'data' / 'call-screen-simulated-v1.manifest.json'
SEED = 20260929
PER_FAMILY = 500

OPENERS = (
    'Hello.', 'Hi.', 'Good morning.', 'Good afternoon.', 'Good evening.',
    'I am calling today.', 'This is a quick call.', 'I am following up.',
    'I wanted to let you know.', 'I am reaching out now.', 'I have a brief update.',
    'I am calling with an update.', 'I am getting in touch.', 'This is a short reminder.',
    'I am calling about a recent matter.', 'I wanted to check in.', 'I have some information.',
    'I am calling to follow up.', 'I need to speak with you.', 'This is a courtesy call.',
    'I am calling from the service desk.', 'I am calling from the office.',
    'I am calling with a notice.', 'I am calling with a reminder.', 'I am calling about this now.',
)

ENDINGS = {
    'harmful': (
        'This needs to happen now.', 'Do not delay.', 'Please act immediately.', 'Time is limited.',
        'Handle this before the deadline.', 'This is urgent.', 'Do not wait to respond.',
        'Please complete this today.', 'The matter cannot wait.', 'Take care of this right away.',
        'Do this before the account changes.', 'Please keep this confidential.', 'Act before the notice expires.',
        'This must be resolved now.', 'Please respond without delay.', 'Do not ignore this request.',
        'The issue is time sensitive.', 'Complete the request immediately.', 'Respond before it is escalated.',
        'This is your final reminder.',
    ),
    'normal': (
        'Thank you.', 'Have a good day.', 'There is no urgency.', 'Please use the usual number for questions.',
        'No response is required now.', 'We are happy to help.', 'Details are available through the usual channel.',
        'Call the regular office if needed.', 'Take care.', 'This is only a reminder.',
        'Please contact us through the normal office line.', 'The usual team can answer questions.',
        'This message is for your information.', 'We appreciate your time.', 'There is nothing else needed today.',
        'The regular portal has more details.', 'The office can help during normal hours.',
        'Please keep this as a reminder.', 'No sensitive information is needed.', 'Thank you for your time.',
    ),
    'unclear': (
        'Please let me know.', 'I would like to discuss it.', 'Can we talk?', 'Please return the call.',
        'I need more information.', 'There is more to explain.', 'I hope to hear from you.',
        'Please get back to me.', 'I have a question.', 'I need to follow up.',
        'We should speak soon.', 'Let me know when you can talk.', 'Please call when available.',
        'I am waiting to hear back.', 'I would appreciate a response.', 'There is an update to discuss.',
        'I need to clarify something.', 'Could we connect?', 'Please contact me.', 'I have a matter to discuss.',
    ),
}


def options(*values):
    return list(values)


FAMILIES = [
    # Harmful calls: 8 families x 500 = 4,000.
    dict(name='bank_otp', label=1, decision='BLOCK', kind='harmful',
         patterns=options('{claim}. {ask}.', '{ask} — {claim}.', '{claim}; {ask}.'),
         claim=options('This is {bank} security', 'I am calling from {bank} fraud prevention', '{bank} flagged a payment'),
         ask=options('Read me the one-time code we sent', 'Tell me the verification code now', 'Confirm the login passcode'),
         bank=options('your bank', 'the account team', 'the payment center', 'the card department')),
    dict(name='gift_card_payment', label=1, decision='BLOCK', kind='harmful',
         patterns=options('{claim}. {ask}.', '{ask}; {claim}.'),
         claim=options('Your account has an urgent balance', 'You must resolve this tax issue today', 'A legal problem needs payment'),
         ask=options('Buy gift cards and read me the numbers', 'Send the redemption codes immediately', 'Pay with gift cards to avoid a penalty')),
    dict(name='remote_access', label=1, decision='BLOCK', kind='harmful',
         patterns=options('{claim}. {ask}.', '{ask} so {claim_lower}.'),
         claim=options('Your computer has a security problem', 'There is suspicious activity on your account', 'Your device needs immediate support'),
         claim_lower=options('we can fix the account', 'I can remove the problem', 'the payment can be protected'),
         ask=options('Install remote access software and give me control', 'Open the support app so I can control your screen', 'Let me connect to your device remotely')),
    dict(name='safe_account_transfer', label=1, decision='BLOCK', kind='harmful',
         patterns=options('{claim}. {ask}.', '{ask}; {claim_lower}.'),
         claim=options('Your money is at risk', 'Your bank account has been compromised', 'A suspicious transfer was detected'),
         claim_lower=options('your funds are safe', 'we can secure the balance', 'the account is protected'),
         ask=options('Move the balance to my safe account', 'Transfer your savings to this secure account', 'Send the funds to the account I provide')),
    dict(name='government_threat', label=1, decision='BLOCK', kind='harmful',
         patterns=options('{claim}. {ask}.', '{ask} because {claim_lower}.'),
         claim=options('This is a government collections office', 'Your tax record requires action', 'A legal enforcement notice is pending'),
         claim_lower=options('an arrest could follow', 'a penalty is due', 'your file will be escalated'),
         ask=options('Pay the fine today using gift cards', 'Verify your identity code now', 'Send a payment immediately')),
    dict(name='crypto_investment', label=1, decision='BLOCK', kind='harmful',
         patterns=options('{claim}. {ask}.', '{ask}; {claim_lower}.'),
         claim=options('I have an urgent investment opportunity', 'Your crypto wallet needs verification', 'You have a guaranteed recovery payment'),
         claim_lower=options('the offer expires today', 'the wallet can be secured', 'the funds can be released'),
         ask=options('Share your recovery phrase', 'Send cryptocurrency to verify the wallet', 'Read out the code from your authenticator')),
    dict(name='delivery_payment_phish', label=1, decision='BLOCK', kind='harmful',
         patterns=options('{claim}. {ask}.', '{ask} to {claim_lower}.'),
         claim=options('Your parcel cannot be delivered', 'A delivery fee is overdue', 'Your package is being held'),
         claim_lower=options('release the parcel', 'avoid a return', 'complete delivery'),
         ask=options('Pay the small fee with your card now', 'Confirm your card details', 'Read me the code from your bank')),
    dict(name='romance_or_family_emergency', label=1, decision='BLOCK', kind='harmful',
         patterns=options('{claim}. {ask}.', '{ask}; {claim_lower}.'),
         claim=options('I am in an emergency and cannot talk long', 'Your family member needs urgent help', 'I need money immediately'),
         claim_lower=options('there is no time to verify this', 'the situation is urgent', 'help can arrive quickly'),
         ask=options('Send money to this account', 'Buy gift cards and send the codes', 'Transfer funds before anyone else finds out')),
    # Normal calls: 8 families x 500 = 4,000.
    dict(name='appointment_reminder', label=0, decision='CONNECT', kind='normal',
         patterns=options('{claim}. {detail}.', '{detail}. {claim}.'),
         claim=options('This is {place} with a reminder', '{place} is confirming your appointment', 'A reminder from {place}'),
         place=options('your dental office', 'the clinic', 'the optometrist', 'the physiotherapy office'),
         detail=options('Your appointment is tomorrow at {time}', 'Please call our usual number to reschedule', 'No payment is needed on this call'),
         time=options('9 a.m.', '10 a.m.', '2 p.m.', '3:30 p.m.')),
    dict(name='delivery_notice', label=0, decision='CONNECT', kind='normal',
         patterns=options('{claim}. {detail}.', '{detail}. {claim}.'),
         claim=options('Your delivery is at the front desk', 'This is a delivery notice', 'Your parcel is ready for collection'),
         detail=options('You can pick it up when convenient', 'There is no fee due', 'Use the regular pickup desk')),
    dict(name='school_message', label=0, decision='CONNECT', kind='normal',
         patterns=options('{claim}. {detail}.', '{detail}. {claim}.'),
         claim=options('This is {school}', 'A message from {school}', '{school} is calling'),
         school=options('the school office', 'your child’s school', 'the after-school program', 'the library program'),
         detail=options('The event starts at {time}', 'Please check the usual parent portal for details', 'No action is needed today'),
         time=options('4 p.m.', '5 p.m.', '6 p.m.', '7 p.m.')),
    dict(name='service_visit', label=0, decision='CONNECT', kind='normal',
         patterns=options('{claim}. {detail}.', '{detail}. {claim}.'),
         claim=options('This is {provider} about your scheduled visit', '{provider} is confirming a service window', 'A reminder from {provider}'),
         provider=options('the utility company', 'the home repair team', 'the internet installer', 'the building manager'),
         detail=options('The technician arrives between {time} and {time2}', 'Please use the usual support line if you need to change it', 'There is no payment request'),
         time=options('8 a.m.', '9 a.m.', '1 p.m.', '2 p.m.'), time2=options('10 a.m.', '11 a.m.', '3 p.m.', '4 p.m.')),
    dict(name='community_event', label=0, decision='CONNECT', kind='normal',
         patterns=options('{claim}. {detail}.', '{detail}. {claim}.'),
         claim=options('This is {group} with an event reminder', 'A reminder from {group}', '{group} is calling about an event'),
         group=options('the neighborhood association', 'the community center', 'the volunteer group', 'the local library'),
         detail=options('The event is on {day}', 'Details are in the regular newsletter', 'You do not need to share any information'),
         day=options('Monday', 'Tuesday', 'Wednesday', 'Thursday')),
    dict(name='account_information', label=0, decision='CONNECT', kind='normal',
         patterns=options('{claim}. {detail}.', '{detail}. {claim}.'),
         claim=options('This is {business} with account information', 'A routine notice from {business}', '{business} is returning your call'),
         business=options('your insurance office', 'the pharmacy', 'the membership desk', 'the property manager'),
         detail=options('Please use the number on your statement for questions', 'No password or code is requested', 'Your usual account portal has the update')),
    dict(name='medical_result_ready', label=0, decision='CONNECT', kind='normal',
         patterns=options('{claim}. {detail}.', '{detail}. {claim}.'),
         claim=options('This is {place} letting you know an update is ready', 'A message from {place}', '{place} is returning your call'),
         place=options('the clinic', 'the dental office', 'the diagnostic center', 'the pharmacy'),
         detail=options('Please use the usual office number to speak with staff', 'No sensitive details are needed on this call', 'The office is open until {time}'),
         time=options('4 p.m.', '5 p.m.', '6 p.m.', '7 p.m.')),
    dict(name='scam_warning', label=0, decision='CONNECT', kind='normal',
         patterns=options('{claim}. {detail}.', '{detail}. {claim}.'),
         claim=options('This is a security reminder', 'A public safety message', 'A fraud-awareness notice'),
         detail=options('Never read a verification code to someone who calls you', 'Do not buy gift cards for an unexpected caller', 'Do not give remote access to an unknown person')),
    # Unclear calls: 4 families x 500 = 2,000.
    dict(name='vague_account', label=None, decision='CONTINUE_SCREENING', kind='unclear',
         patterns=options('{claim}.', '{claim}; {detail}.'),
         claim=options('I am calling about your account', 'There is an issue with your account', 'I need to discuss an account matter'),
         detail=options('I need to verify a few details', 'Can you help with this', 'Please call me back')),
    dict(name='vague_service', label=None, decision='CONTINUE_SCREENING', kind='unclear',
         patterns=options('{claim}.', '{claim}; {detail}.'),
         claim=options('I am calling about a service request', 'There is a problem to sort out', 'I need to speak with you'),
         detail=options('It is important', 'Please return the call', 'I need more information')),
    dict(name='generic_callback', label=None, decision='CONTINUE_SCREENING', kind='unclear',
         patterns=options('{claim}.', '{claim}; {detail}.'),
         claim=options('Please call me back', 'I am following up', 'I need to reach you today'),
         detail=options('This concerns a recent request', 'It is about a message we received', 'I have a question')),
    dict(name='identity_only', label=None, decision='CONTINUE_SCREENING', kind='unclear',
         patterns=options('{claim}.', '{claim}; {detail}.'),
         claim=options('This is the account team', 'I am calling from support', 'This is customer service'),
         detail=options('I need to discuss something with you', 'Please answer a quick question', 'I have an update')),
]


def render(family: dict, index: int) -> str:
    keys = [key for key, value in family.items() if isinstance(value, list)]
    values = [family[key] for key in keys]
    combos = list(itertools.product(*values))
    combo = combos[index % len(combos)]
    context = dict(zip(keys, combo))
    # Render nested values such as "This is {bank} security" first.
    for _ in range(3):
        context = {key: value.format(**context) if isinstance(value, str) else value for key, value in context.items()}
    pattern = family['patterns'][index % len(family['patterns'])]
    body = pattern.format(**context)
    # Every record has a natural call opening and ending. The 25 x 20
    # combinations guarantee 500 distinct transcripts per scenario family
    # without adding IDs or other artificial labels to caller text.
    opening = OPENERS[index % len(OPENERS)]
    ending = ENDINGS[family['kind']][index // len(OPENERS)]
    return f'{opening} {body} {ending}'


def split_rows(rows: list[dict], rng: random.Random) -> list[dict]:
    rng.shuffle(rows)
    for index, row in enumerate(rows):
        row['split'] = 'development' if index < 350 else 'validation' if index < 425 else 'held_out'
    return rows


def build() -> list[dict]:
    rng = random.Random(SEED)
    rows = []
    for family in FAMILIES:
        family_rows = []
        for index in range(PER_FAMILY):
            text = render(family, index)
            family_rows.append({
                'id': f"sim-v1-{family['name']}-{index + 1:04d}",
                'family': family['name'],
                'call_type': family['kind'],
                'label': family['label'],
                'expected_decision': family['decision'],
                'conversation': [{'role': 'caller', 'text': text}],
                'source': 'programmatic simulated scenario matrix v1',
            })
        rows.extend(split_rows(family_rows, rng))
    rng.shuffle(rows)
    if len(rows) != 10_000 or len({row['id'] for row in rows}) != 10_000:
        raise RuntimeError('Expected 10,000 uniquely identified records.')
    texts = {row['conversation'][0]['text'] for row in rows}
    if len(texts) != 10_000:
        raise RuntimeError('Expected 10,000 distinct transcripts.')
    return rows


def write(rows: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', encoding='utf-8', newline='\n') as file:
        for row in rows:
            file.write(json.dumps(row, separators=(',', ':')) + '\n')
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    manifest = {
        'version': 'call-screen-simulated-v1',
        'seed': SEED,
        'record_count': len(rows),
        'sha256': digest,
        'format': 'JSON Lines; one caller turn per record',
        'provenance': 'Programmatic simulated scenarios with scenario-assigned labels. No real callers, Twilio calls, or Gemini outputs.',
        'sampling': 'Stratified evaluation corpus: 4,000 harmful, 4,000 normal, and 2,000 unclear calls. It is not population prevalence.',
        'splits': dict(Counter(row['split'] for row in rows)),
        'call_types': dict(Counter(row['call_type'] for row in rows)),
        'families': dict(Counter(row['family'] for row in rows)),
        'limitations': [
            'Labels are scenario-assigned, not independently adjudicated.',
            'Synthetic wording cannot measure speech-to-text errors, adversarial adaptation, or population prevalence.',
            'Precision from this stratified corpus is evaluation precision, not an estimate of production precision.',
            'This corpus cannot establish causal experiment results.',
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    generated = build()
    write(generated)
    print(json.dumps({'records': len(generated), 'output': str(OUT), 'manifest': str(MANIFEST)}))
