"""Local reviewer corrections; no live customer data is included by default."""
import json
from datetime import datetime, timezone
from pathlib import Path


PATH = Path(__file__).with_name('adjudications.jsonl')


def add(call_id: str, predicted_tier: str, reviewer_label: str, corrected_label: str, reviewer: str, notes: str = '') -> dict:
    record = {'call_id': call_id, 'predicted_tier': predicted_tier, 'reviewer_label': reviewer_label,
              'corrected_label': corrected_label, 'timestamp': datetime.now(timezone.utc).isoformat(),
              'reviewer': reviewer, 'notes': notes}
    with PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, separators=(',', ':')) + '\n')
    return record


def all_records() -> list[dict]:
    return [json.loads(line) for line in PATH.read_text(encoding='utf-8').splitlines() if line.strip()] if PATH.exists() else []
