"""Measure per-turn Gemini signal-extraction latency on 50 generated turns."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]

from dotenv import load_dotenv
from sim.generator import generate
from transcript_classifier import GeminiTranscriptClassifier


OUT = ROOT / 'eval' / 'reports' / 'latency_probe.json'


def percentile(values, quantile):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * quantile
    lower, upper = int(index), min(int(index) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


async def main(run: bool):
    turns = [turn for scenario in generate() if scenario.split == 'test' for turn in scenario.turns if turn.speaker == 'caller'][:50]
    if not run:
        print(json.dumps({'status': 'dry_run', 'turns': len(turns), 'gemini_requests_if_run': len(turns), 'output': str(OUT)}))
        return
    load_dotenv(ROOT / 'backend' / '.env')
    classifier = GeminiTranscriptClassifier()
    latencies = []
    for turn in turns:
        result = await classifier.classify([{'role': 'caller', 'text': turn.text}])
        latencies.append(result.latency_ms)
    report = {'calls': len(latencies), 'p50_ms': percentile(latencies, .5), 'p95_ms': percentile(latencies, .95),
              'component': 'Gemini signal extraction only', 'note': 'Twilio speech recognition and call setup are excluded.'}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Make 50 Gemini requests.')
    args = parser.parse_args()
    asyncio.run(main(args.run))
