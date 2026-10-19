"""Measure Gemini's signal extraction against 100 generated, turn-level labels.

Default mode makes no network requests. `--run` performs 300 Gemini calls
(three passes across 100 turns) and writes a separate audit report.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]

from dotenv import load_dotenv
from eval.metrics import signal_metrics
from sim.generator import generate
from transcript_classifier import GeminiTranscriptClassifier


OUT = ROOT / 'eval' / 'reports' / 'gemini_signal_audit.json'
NAMES = ('urgency', 'impersonation', 'payment_request', 'code_request', 'personal_info_request', 'threat', 'suspicious_action')


def sample():
    rows = []
    for scenario in generate():
        if scenario.split != 'test':
            continue
        for turn in scenario.turns:
            if turn.speaker == 'caller':
                rows.append((scenario, turn))
    return rows[:100]


def fleiss_kappa(runs: list[list[dict]]) -> float | None:
    # Each item is one (turn, signal) pair rated present/absent by three runs.
    items = []
    for index in range(len(runs[0])):
        for name in NAMES:
            present = [int(run[index]['predicted'].get(name, False)) for run in runs]
            items.append(present)
    if not items:
        return None
    raters = len(runs)
    p_present = sum(sum(item) for item in items) / (len(items) * raters)
    p_expected = p_present * p_present + (1 - p_present) ** 2
    p_observed = sum((sum(item) ** 2 + (raters - sum(item)) ** 2 - raters) / (raters * (raters - 1)) for item in items) / len(items)
    return (p_observed - p_expected) / (1 - p_expected) if p_expected < 1 else None


async def score_once(rows):
    classifier = GeminiTranscriptClassifier()
    scored = []
    for index, (scenario, turn) in enumerate(rows, start=1):
        result = await classifier.classify([{'role': 'caller', 'text': turn.text}])
        predicted = {item.type: item.present for item in result.signal_evidence}
        if not predicted:
            predicted = {
                'urgency': result.conversation_signals.urgency,
                'impersonation': result.conversation_signals.impersonation,
                'payment_request': result.conversation_signals.payment_or_money_request,
                'code_request': result.conversation_signals.credential_request,
                'personal_info_request': False,
                'threat': result.conversation_signals.threatening_language,
                'suspicious_action': result.conversation_signals.suspicious_action_request,
            }
        scored.append({'scenario_id': scenario.scenario_id, 'turn_id': index, 'expected': list(turn.signals),
                       'predicted': predicted, 'evidence': [item.model_dump() for item in result.signal_evidence],
                       'latency_ms': result.latency_ms})
    return scored


async def main(run: bool):
    rows = sample()
    if not run:
        print(json.dumps({'status': 'dry_run', 'turns': len(rows), 'gemini_requests_if_run': len(rows) * 3, 'output': str(OUT)}))
        return
    load_dotenv(ROOT / 'backend' / '.env')
    runs = [await score_once(rows) for _ in range(3)]
    primary = runs[0]
    report = {'turns': len(rows), 'runs': 3, 'metrics': signal_metrics(primary),
              'fleiss_kappa': fleiss_kappa(runs), 'latency_ms': [row['latency_ms'] for row in primary],
              'failure_gallery': [row for row in primary if any(name in row['expected'] and not row['predicted'].get(name, False) for name in row['expected'])][:20],
              'note': 'Gemini signal audit on generated labels; it is separate from call-level policy metrics.'}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'complete', 'output': str(OUT), 'fleiss_kappa': report['fleiss_kappa']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Make 300 Gemini requests.')
    args = parser.parse_args()
    asyncio.run(main(args.run))
