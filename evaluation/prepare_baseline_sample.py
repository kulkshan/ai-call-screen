"""Prepare a fixed 1,000-call baseline sample without calling external services."""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'data' / 'call-screen-simulated-v1.jsonl'
OUTPUT = ROOT / 'data' / 'baseline-development-1000.jsonl'
MANIFEST = ROOT / 'data' / 'baseline-development-1000.manifest.json'
SEED = 20260930
QUOTAS = {'harmful': 400, 'normal': 400, 'unclear': 200}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def select(rows: list[dict], seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    selected = []
    for call_type, quota in QUOTAS.items():
        candidates = sorted(
            (row for row in rows if row['split'] == 'development' and row['call_type'] == call_type),
            key=lambda row: row['id'],
        )
        if len(candidates) < quota:
            raise ValueError(f'Need {quota} development {call_type} calls; found {len(candidates)}.')
        selected.extend(rng.sample(candidates, quota))
    rng.shuffle(selected)
    return selected


def write(rows: list[dict], source: Path = SOURCE, output: Path = OUTPUT, manifest: Path = MANIFEST) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8', newline='\n') as file:
        for row in rows:
            file.write(json.dumps(row, separators=(',', ':')) + '\n')
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    output_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    payload = {
        'version': 'baseline-development-1000-v1',
        'record_count': len(rows),
        'seed': SEED,
        'source_dataset': source.name,
        'source_sha256': source_hash,
        'sha256': output_hash,
        'selection': 'Fixed stratified sample from the development split.',
        'quotas': QUOTAS,
        'counts': dict(Counter(row['call_type'] for row in rows)),
        'provenance': 'Subset of the programmatic simulated Call Screen corpus. No Gemini or Twilio calls were made.',
    }
    manifest.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    if not SOURCE.exists():
        raise SystemExit('Generate the 10,000-call corpus first: python evaluation/generate_call_set.py')
    sample = select(read_jsonl(SOURCE))
    write(sample)
    print(json.dumps({'records': len(sample), 'output': str(OUTPUT), 'manifest': str(MANIFEST)}))
