"""Stable payload shape for the dashboard and README."""
from pathlib import Path
import json


REPORT_PATH = Path(__file__).with_name('reports') / 'latest.json'


def write(report: dict) -> Path:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return REPORT_PATH


def load() -> dict | None:
    return json.loads(REPORT_PATH.read_text(encoding='utf-8')) if REPORT_PATH.exists() else None
