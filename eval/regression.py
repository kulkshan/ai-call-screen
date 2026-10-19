"""Append-only local tracking of reproducible metric runs."""
import json
from datetime import datetime, timezone
from pathlib import Path


RUNS = Path(__file__).with_name('metric_runs.jsonl')


def record(report: dict, git_sha: str = 'local-uncommitted') -> dict:
    entry = {
        'run_id': report['run_id'], 'git_sha': git_sha,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'fusion_version': report['model']['model_version'],
        'config': report['cost_model'],
        'metrics': report['metrics'],
    }
    RUNS.parent.mkdir(parents=True, exist_ok=True)
    with RUNS.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, separators=(',', ':')) + '\n')
    return entry


def history() -> list[dict]:
    if not RUNS.exists():
        return []
    return [json.loads(line) for line in RUNS.read_text(encoding='utf-8').splitlines() if line.strip()]
