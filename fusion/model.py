"""Small dependency-free logistic model plus isotonic calibration artifact."""
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


ARTIFACT = Path(__file__).with_name('artifacts') / 'call_screen_v1.json'


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(-35.0, min(35.0, value))))


@dataclass
class Calibrator:
    x: list[float]
    y: list[float]

    def predict(self, probability: float) -> float:
        if not self.x:
            return probability
        for index, boundary in enumerate(self.x):
            if probability <= boundary:
                return self.y[index]
        return self.y[-1]


@dataclass
class LogisticFusionModel:
    weights: list[float]
    bias: float
    calibrator: Calibrator
    feature_version: str
    model_version: str = 'call-screen-fusion-v1'

    def raw_probability(self, features: list[float]) -> float:
        return sigmoid(self.bias + sum(weight * value for weight, value in zip(self.weights, features)))

    def probability(self, features: list[float]) -> float:
        return self.calibrator.predict(self.raw_probability(features))

    def to_dict(self) -> dict:
        return {
            'weights': self.weights, 'bias': self.bias,
            'calibrator': asdict(self.calibrator),
            'feature_version': self.feature_version, 'model_version': self.model_version,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['weights'], data['bias'], Calibrator(**data['calibrator']),
                   data['feature_version'], data.get('model_version', 'call-screen-fusion-v1'))


def save(model: LogisticFusionModel, path: Path = ARTIFACT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.to_dict(), indent=2) + '\n', encoding='utf-8')
    return path


def load(path: Path = ARTIFACT) -> LogisticFusionModel:
    return LogisticFusionModel.from_dict(json.loads(path.read_text(encoding='utf-8')))
