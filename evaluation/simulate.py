"""Create a deterministic, clearly labelled simulated evaluation pilot.

This script makes no network requests and does not call Gemini or Twilio.
It exists solely to demonstrate the evaluation UI before controlled live calls exist.
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'evaluation' / 'cases.json'
OUTPUT = ROOT / 'evaluation' / 'results.json'

spec = importlib.util.spec_from_file_location('evaluation_runner', ROOT / 'evaluation' / 'run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

# Two intentionally simulated errors make the case-review experience concrete:
# one missed scam and one false block. These values are not model outputs.
OUTCOMES = {
    'otp-1': (.98, 'BLOCK', 590, ['Bank impersonation', 'One-time-code request']),
    'otp-2': (.96, 'BLOCK', 640, ['One-time-password request', 'Fraud-prevention impersonation']),
    'gift_card-1': (.99, 'BLOCK', 610, ['Gift-card payment request', 'Government impersonation']),
    'gift_card-2': (.97, 'BLOCK', 670, ['Gift-card redemption request', 'Threat and urgency']),
    'appointment-1': (.07, 'CONNECT', 520, ['Routine appointment context', 'No sensitive request']),
    'appointment-2': (.11, 'CONNECT', 560, ['Routine appointment context', 'No payment or credential request']),
    'unclear-1': (.46, 'CONTINUE_SCREENING', 690, ['Caller identity is vague', 'Purpose needs clarification']),
    'unclear-2': (.51, 'CONTINUE_SCREENING', 710, ['Account claim is vague', 'Purpose needs clarification']),
    'remote_access-1': (.94, 'BLOCK', 790, ['Remote-access request', 'Financial account pretext']),
    'remote_access-2': (.54, 'CONTINUE_SCREENING', 860, ['Remote-access request', 'Needs targeted follow-up']),
    'safe_account-1': (.96, 'BLOCK', 740, ['Safe-account transfer request', 'Urgency']),
    'safe_account-2': (.93, 'BLOCK', 820, ['Safe-account transfer request', 'Financial loss threat']),
    'warning-1': (.18, 'CONNECT', 490, ['Scam-warning context', 'No harmful request']),
    'warning-2': (.81, 'BLOCK', 760, ['Gift-card language', 'Warning context was missed']),
    'delivery-1': (.08, 'CONNECT', 510, ['Specific delivery context', 'No sensitive request']),
    'delivery-2': (.10, 'CONNECT', 540, ['Routine pickup context', 'No fee or credential request']),
    'ambiguous-1': (.47, 'CONTINUE_SCREENING', 630, ['Purpose is unclear', 'Follow-up required']),
    'ambiguous-2': (.43, 'CONTINUE_SCREENING', 650, ['Purpose is unclear', 'Follow-up required']),
}

EXPLANATIONS = {
    'remote_access-2': 'Simulated miss: the caller asks for remote access, but the system asks a question instead of stopping the call.',
    'warning-2': 'Simulated false block: the caller warns about a gift-card scam, but the system stops the call anyway.',
}

def main():
    dataset = json.loads(SOURCE.read_text(encoding='utf-8'))
    records = []
    for case in dataset['records']:
        score, decision, latency_ms, signals = OUTCOMES[case['id']]
        assessment = {
            'risk_score': score,
            'decision': decision,
            'detected_signals': signals,
            'explanation': EXPLANATIONS.get(case['id'], 'Simulated result for this demo.'),
            'latency_ms': latency_ms,
        }
        records.append({**case, 'assessment': assessment})
    summaries = {
        'all': runner.metrics(records),
        'development': runner.metrics([record for record in records if record['split'] == 'development']),
        'held_out': runner.metrics([record for record in records if record['split'] == 'held_out']),
    }
    result = {
        'status': 'simulated',
        'simulated': True,
        'dataset_version': dataset['version'],
        'provenance': 'Simulated example calls and outcomes for this demo. No live calls, Twilio, or Gemini were used.',
        'total': len(records),
        'records': records,
        'summaries': summaries,
        'errors': [],
    }
    OUTPUT.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f'Wrote {OUTPUT} with {len(records)} simulated records.')

if __name__ == '__main__':
    main()
