"""Train and calibrate the fusion model without hidden dependencies."""
import random

from fusion.features import FEATURE_VERSION
from fusion.model import Calibrator, LogisticFusionModel, sigmoid


def _pav(scores: list[float], labels: list[int]) -> Calibrator:
    """Pool-adjacent-violators isotonic regression for a validation split."""
    pairs = sorted(zip(scores, labels), key=lambda item: item[0])
    blocks = []
    for score, label in pairs:
        blocks.append([score, score, float(label), 1])
        while len(blocks) >= 2 and blocks[-2][2] / blocks[-2][3] > blocks[-1][2] / blocks[-1][3]:
            right = blocks.pop(); left = blocks.pop()
            blocks.append([left[0], right[1], left[2] + right[2], left[3] + right[3]])
    return Calibrator([block[1] for block in blocks], [block[2] / block[3] for block in blocks])


def train(train_rows: list[tuple[list[float], int]], validation_rows: list[tuple[list[float], int]], *, seed: int = 20261003) -> LogisticFusionModel:
    if not train_rows or not validation_rows:
        raise ValueError('Training and validation rows are required.')
    width = len(train_rows[0][0])
    weights = [0.0] * width
    bias = 0.0
    positives = sum(label for _, label in train_rows)
    negatives = len(train_rows) - positives
    positive_weight = len(train_rows) / (2 * positives) if positives else 1.0
    negative_weight = len(train_rows) / (2 * negatives) if negatives else 1.0
    rng = random.Random(seed)
    for epoch in range(300):
        rows = train_rows[:]
        rng.shuffle(rows)
        rate = .14 / (1 + epoch / 100)
        for features, label in rows:
            predicted = sigmoid(bias + sum(weight * value for weight, value in zip(weights, features)))
            scale = positive_weight if label else negative_weight
            error = (predicted - label) * scale
            for index, value in enumerate(features):
                weights[index] -= rate * (error * value + .0008 * weights[index])
            bias -= rate * error
    validation_scores = [sigmoid(bias + sum(weight * value for weight, value in zip(weights, features))) for features, _ in validation_rows]
    return LogisticFusionModel(weights, bias, _pav(validation_scores, [label for _, label in validation_rows]), FEATURE_VERSION)
