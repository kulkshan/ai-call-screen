"""Run the full, no-network evaluation pipeline."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.harness import run
from eval.regression import record
from eval.report import write
from policy.cost_model import CostModel


if __name__ == '__main__':
    report = run(CostModel())
    path = write(report)
    record(report)
    metrics = report['metrics']
    print(f"Wrote {path}")
    print(f"Precision {metrics['precision']:.3f}; recall {metrics['recall']:.3f}; FPR {metrics['false_positive_rate']:.3f}")
