"""Create the compact report bundled with the public static portfolio build."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'eval' / 'reports' / 'latest.json'
TARGET = ROOT / 'web' / 'app' / 'data' / 'public-report.json'
GUIDED_IDS = {
    'benchmark-v2-remote_access-0401',
    'benchmark-v2-delivery_notice-0401',
    'benchmark-v2-vague_account-0416',
}


def build() -> dict:
    report = json.loads(SOURCE.read_text(encoding='utf-8'))
    calls = report['calls']
    selected = {call['scenario_id']: call for call in calls if call['scenario_id'] in GUIDED_IDS}
    examples = (
        next((call for call in calls if call['label'] == 'scam' and call['probability'] < .5), None),
        next((call for call in calls if call['label'] == 'legit' and call['probability'] >= .5), None),
        next((call for call in calls if call.get('baseline_probability', 0) >= .5 and call['probability'] < .5), None),
    )
    for call in examples:
        if call:
            selected[call['scenario_id']] = call
    return {**report, 'calls': list(selected.values()), 'public_report': True}


if __name__ == '__main__':
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(build(), separators=(',', ':')) + '\n', encoding='utf-8')
    print(TARGET)
