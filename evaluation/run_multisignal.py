"""Run the fixed 1,000-case multi-signal evaluation.

Default mode is a dry run. `--run` makes Gemini requests and writes a
resumable result under evaluation/runs.
"""
import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from dotenv import load_dotenv
load_dotenv(ROOT / 'backend' / '.env')
from caller_context import simulated_context
from screening_service import screen

SOURCE = ROOT / 'evaluation' / 'data' / 'multisignal-call-screen-v1.jsonl'
OUT = ROOT / 'evaluation' / 'runs' / 'multisignal-call-screen-v1.json'


def load_rows():
    return [json.loads(line) for line in SOURCE.read_text(encoding='utf-8').splitlines() if line.strip()]


def percentile(values, q):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * q
    low, high = int(index), min(int(index) + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def summaries(records):
    action_counts = {expected: {observed: 0 for observed in ('ALLOW', 'CONTINUE_SCREENING', 'WARN', 'BLOCK')}
                     for expected in ('ALLOW', 'CONTINUE_SCREENING', 'WARN', 'BLOCK')}
    for row in records:
        action_counts[row['expected_decision']][row['outcome']['decision']] += 1
    labelled = [row for row in records if row['label'] is not None]
    caught = sum(row['label'] == 1 and row['outcome']['decision'] in ('WARN', 'BLOCK') for row in labelled)
    blocked = [row for row in labelled if row['outcome']['decision'] == 'BLOCK']
    true_blocks = sum(row['label'] == 1 for row in blocked)
    false_blocks = sum(row['label'] == 0 and row['outcome']['decision'] == 'BLOCK' for row in labelled)
    harmful = sum(row['label'] == 1 for row in labelled)
    normal = sum(row['label'] == 0 for row in labelled)
    return {
        'completed': len(records),
        'exact_action_accuracy': sum(row['expected_decision'] == row['outcome']['decision'] for row in records) / len(records) if records else None,
        'harmful_calls_caught': caught / harmful if harmful else None,
        'block_precision': true_blocks / len(blocked) if blocked else None,
        'false_block_rate': false_blocks / normal if normal else None,
        'action_confusion': action_counts,
        'p50_latency_ms': percentile([row['outcome']['latency_ms'] for row in records], .5),
        'p95_latency_ms': percentile([row['outcome']['latency_ms'] for row in records], .95),
    }


def save(result, status):
    result['status'] = status
    result['updated_at'] = datetime.now(timezone.utc).isoformat()
    result['summaries'] = summaries(result['records'])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, indent=2), encoding='utf-8')
    temporary.replace(OUT)


async def score(row):
    context = simulated_context(**row['caller_context'])
    outcome = await screen(row['conversation'], context)
    return {**row, 'outcome': outcome.model_dump()}


async def run(args):
    rows = load_rows()
    if not args.run:
        print(json.dumps({'status': 'dry_run', 'selected': len(rows), 'result_file': str(OUT)}))
        return
    result = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {
        'version': 'multisignal-evaluation-v1', 'source': SOURCE.name, 'records': [], 'errors': []}
    done = {row['id'] for row in result['records']}
    pending = [row for row in rows if row['id'] not in done]
    # Every checkpoint should include a mix of actions, not 250 identical rows.
    random.Random(20260930).shuffle(pending)
    if args.limit:
        pending = pending[:args.limit]
    for start in range(0, len(pending), args.workers):
        batch = pending[start:start + args.workers]
        scored = await asyncio.gather(*(score(row) for row in batch), return_exceptions=True)
        failure = next((item for item in scored if isinstance(item, Exception)), None)
        if failure:
            result['errors'].append({
                'at': datetime.now(timezone.utc).isoformat(),
                'type': type(failure).__name__,
                'status_code': getattr(failure, 'status_code', None),
                'detail': str(getattr(failure, 'detail', ''))[:160],
            })
            save(result, 'provider_error')
            print(f'Stopped after provider error; saved {len(result["records"])} results.', flush=True)
            return
        result['records'].extend(scored)
        save(result, 'partial' if len(result['records']) < len(rows) else 'complete')
        print(f'{len(result["records"])} / {len(rows)} saved', flush=True)
        if args.interval:
            await asyncio.sleep(args.interval)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Make Gemini requests.')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--interval', type=float, default=.25)
    parser.add_argument('--limit', type=int, default=0, help='Score at most this many pending rows; 0 means all.')
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 8 or args.interval < 0 or args.limit < 0:
        parser.error('workers must be 1–8, interval must be non-negative, and limit must be non-negative')
    asyncio.run(run(args))
