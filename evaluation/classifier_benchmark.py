"""Build the fixed 10,000-call benchmark used to train and test our classifier.

The label is stored beside each transcript for evaluation.  Classifier code is
given only ``conversation[].text``.  The split is fixed before training and the
final test rows are never used to fit weights or calibration.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from evaluation.generate_call_set import FAMILIES, render


ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data' / 'classifier-benchmark-10000.jsonl'
MANIFEST = ROOT / 'data' / 'classifier-benchmark-10000.manifest.json'

SPLITS = (
    ('train', 0, 300),
    ('validation', 300, 400),
    ('test', 400, 500),
)

# A difficult slice of the final test uses wording that does not occur in
# training. Harmful calls avoid the easiest trigger phrases; legitimate calls
# deliberately mention scam language in warnings and safe callback instructions.
HARD_SCAM = {
    'bank_otp': ('A six digit number was just sent to your phone. Confirm those digits so I can close the review.', 'To finish protecting the account, repeat the temporary number in the message you received.'),
    'gift_card_payment': ('Settle the balance using store vouchers and give me the activation details.', 'Purchase prepaid retail cards and dictate the redemption information to clear the case.'),
    'remote_access': ('Open Quick Assist and accept my connection so I can operate the device.', 'Install the screen support utility and approve control while you sign in.'),
    'safe_account_transfer': ('Move the balance into the holding account I provide while the investigation runs.', 'Send the savings to a protected account under my control before the pending debit posts.'),
    'government_threat': ('Your file will be referred for arrest unless the balance is settled through the payment method I give you.', 'Avoid immediate enforcement by verifying the private number delivered to your handset.'),
    'crypto_investment': ('Tell me the recovery words for the wallet so I can restore access.', 'Send a small amount of digital currency to the address I provide to release the recovered funds.'),
    'delivery_payment_phish': ('The parcel is held. Give me the card number and security digits to release it.', 'Complete a small card charge through the address I dictate or the shipment will be returned.'),
    'romance_or_family_emergency': ('Please keep this from the family and wire funds to the account I give you.', 'There is no time to call anyone else. Send the money to my contact immediately.'),
}

HARD_LEGIT = {
    'appointment_reminder': ('This is the clinic confirming tomorrow. We will never ask for a password or verification code.', 'Your appointment remains scheduled. Call the published office number if anyone asks you for payment.'),
    'delivery_notice': ('Your package is ready. There is no fee, card request, or link to open.', 'The parcel is at the desk. Do not give payment details to anyone claiming otherwise.'),
    'school_message': ('The school is warning families about callers demanding urgent gift-card payment.', 'A safety notice from the school: never share a login code with an unexpected caller.'),
    'service_visit': ('The utility visit is confirmed. We do not threaten shutoff or request payment by phone.', 'Your technician is scheduled. Ignore anyone asking to control your screen.'),
    'community_event': ('The community center is hosting a fraud-awareness talk about urgent payment scams.', 'The library session explains why callers asking for gift cards should be reported.'),
    'account_information': ('Your bank detected activity. Hang up and call the number printed on your card; do not share a code.', 'This is a fraud alert. Use the official app yourself and never read us a one-time number.'),
    'medical_result_ready': ('The clinic has an update. Staff will not ask for passwords, codes, or remote access.', 'Your result is ready through the normal portal. No payment information is needed by phone.'),
    'scam_warning': ('Someone claiming to be your bank may demand the verification code. Never provide it.', 'Fraud warning: scammers threaten arrest and demand gift cards. Report the call instead of paying.'),
}

TEST_ENDINGS = (
    'Use an independently verified number if you are unsure.', 'The request applies today.',
    'No other details are available.', 'Please decide before continuing.',
    'This message concerns the current account.', 'That is the full reason for the call.',
    'The caller is waiting for an answer.', 'The request was repeated once.',
    'This is the final instruction.', 'Please handle the matter carefully.',
)


def _hard_test_text(family: dict, index: int) -> str:
    bank = HARD_SCAM if family['label'] == 1 else HARD_LEGIT if family['label'] == 0 else None
    if not bank:
        return render(family, index)
    body = bank[family['name']][index % 2]
    return f"{body} {TEST_ENDINGS[(index - 400) // 2 % len(TEST_ENDINGS)]}"


def build() -> list[dict]:
    rows = []
    for family in FAMILIES:
        for split, start, end in SPLITS:
            for index in range(start, end):
                use_hard_case = split == 'test' and family['label'] is not None and index < 420
                rows.append({
                    'id': f"benchmark-v2-{family['name']}-{index + 1:04d}",
                    'group_id': f"{family['name']}-{index // 5:03d}",
                    'family': family['name'],
                    'call_type': family['kind'],
                    'label': family['label'],
                    'expected_decision': family['decision'],
                    'split': split,
                    'conversation': [{'role': 'caller', 'text': _hard_test_text(family, index) if use_hard_case else render(family, index)}],
                    'source': 'programmatic simulated benchmark v2',
                })
    if len(rows) != 10_000 or len({row['conversation'][0]['text'] for row in rows}) != 10_000:
        raise RuntimeError('The classifier benchmark must contain 10,000 unique transcripts.')
    if Counter(row['split'] for row in rows) != Counter({'train': 6000, 'validation': 2000, 'test': 2000}):
        raise RuntimeError('Unexpected benchmark split.')
    group_splits = {}
    for row in rows:
        group_splits.setdefault(row['group_id'], set()).add(row['split'])
    if any(len(splits) != 1 for splits in group_splits.values()):
        raise RuntimeError('A variation group crossed a data split.')
    return rows


def write(rows: list[dict]) -> tuple[Path, Path]:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(''.join(json.dumps(row, separators=(',', ':')) + '\n' for row in rows), encoding='utf-8')
    payload = {
        'version': 'classifier-benchmark-10000-v2',
        'record_count': len(rows),
        'sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(),
        'splits': dict(Counter(row['split'] for row in rows)),
        'call_types': dict(Counter(row['call_type'] for row in rows)),
        'families': dict(Counter(row['family'] for row in rows)),
        'training_contract': 'Weights use 6,000 train calls only. Calibration uses 2,000 validation calls only. Metrics use 2,000 final test calls only.',
        'group_contract': 'Five-call variation groups stay inside one split.',
        'inference_contract': 'Only raw transcript text is passed to the classifier. Labels and expected decisions are evaluation fields.',
        'provenance': 'Programmatically generated fictional calls. No real callers or production traffic.',
        'limitations': [
            'Synthetic language cannot establish real-world performance.',
            'Labels are assigned by scenario design, not independent human review.',
            'The class mix is balanced for evaluation and does not estimate scam prevalence.',
        ],
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return OUT, MANIFEST


def load() -> list[dict]:
    if not OUT.exists():
        write(build())
    return [json.loads(line) for line in OUT.read_text(encoding='utf-8').splitlines() if line.strip()]


if __name__ == '__main__':
    paths = write(build())
    print(json.dumps({'records': 10000, 'dataset': str(paths[0]), 'manifest': str(paths[1])}))
