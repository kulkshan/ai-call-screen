"""Apply explicit corrections and emit a new report. This never silently rewrites labels."""
from feedback.adjudications import all_records


def corrections_by_call() -> dict[str, str]:
    return {record['call_id']: record['corrected_label'] for record in all_records()}
