"""Train and calibrate our transcript classifier on the fixed benchmark."""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from classifier.text_model import ARTIFACT, Encoder, TranscriptModel, save
from evaluation.classifier_benchmark import MANIFEST, build, write


def binary(rows, split):
    return [row for row in rows if row['split'] == split and row['label'] is not None]


def train_head(embeddings, labels, seed=20261011):
    import torch
    torch.manual_seed(seed)
    x = torch.tensor(embeddings, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.float32)
    layer = torch.nn.Linear(x.shape[1], 1)
    optimizer = torch.optim.AdamW(layer.parameters(), lr=.025, weight_decay=.02)
    for _ in range(450):
        optimizer.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(layer(x).squeeze(1), y)
        loss.backward()
        optimizer.step()
    return layer


def fit_temperature(logits, labels):
    import torch
    values = torch.tensor(logits, dtype=torch.float32)
    targets = torch.tensor(labels, dtype=torch.float32)
    log_temperature = torch.nn.Parameter(torch.zeros(()))
    optimizer = torch.optim.LBFGS([log_temperature], lr=.1, max_iter=80)

    def closure():
        optimizer.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(values / log_temperature.exp(), targets)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(log_temperature.exp().detach().clamp(.05, 10))


def main():
    rows = build()
    dataset, _ = write(rows)
    train_rows = binary(rows, 'train')
    validation_rows = binary(rows, 'validation')
    encoder = Encoder()
    train_embeddings = encoder.encode([row['conversation'][0]['text'] for row in train_rows])
    validation_embeddings = encoder.encode([row['conversation'][0]['text'] for row in validation_rows])
    head = train_head(train_embeddings, [row['label'] for row in train_rows])

    import torch
    with torch.inference_mode():
        validation_logits = head(torch.tensor(validation_embeddings, dtype=torch.float32)).squeeze(1).tolist()
    temperature = fit_temperature(validation_logits, [row['label'] for row in validation_rows])
    artifact = TranscriptModel(
        weights=head.weight.detach().squeeze(0).tolist(),
        bias=float(head.bias.detach()),
        temperature=temperature,
        benchmark_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),
    )
    path = save(artifact, ARTIFACT)
    print(json.dumps({
        'artifact': str(path), 'benchmark': str(dataset),
        'train_binary': len(train_rows), 'validation_binary': len(validation_rows),
        'temperature': temperature,
    }))


if __name__ == '__main__':
    main()
