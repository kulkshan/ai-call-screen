"""A compact trained classifier on frozen DistilBERT transcript embeddings.

The saved artifact contains only the fitted classification head and calibration
temperature.  Expected labels and scenario signals never enter inference.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Iterable


ROOT = Path(__file__).resolve().parent
LEGACY_ARTIFACT = ROOT / 'artifacts' / 'our_classifier_v1.json'
ARTIFACT = ROOT / 'artifacts' / 'our_classifier_v2.json'
MODEL_NAME = 'distilbert-base-uncased'
MODEL_VERSION = 'our-transcript-classifier-v2'


def _sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(-35.0, min(35.0, value))))


@dataclass
class TranscriptModel:
    weights: list[float]
    bias: float
    temperature: float
    model_name: str = MODEL_NAME
    model_version: str = MODEL_VERSION
    benchmark_sha256: str = ''

    def to_dict(self) -> dict:
        return {
            'weights': self.weights,
            'bias': self.bias,
            'temperature': self.temperature,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'benchmark_sha256': self.benchmark_sha256,
            'input_contract': 'raw transcript text only',
        }

    @classmethod
    def from_dict(cls, payload: dict) -> 'TranscriptModel':
        return cls(
            weights=payload['weights'], bias=payload['bias'],
            temperature=payload.get('temperature', 1.0),
            model_name=payload.get('model_name', MODEL_NAME),
            model_version=payload.get('model_version', MODEL_VERSION),
            benchmark_sha256=payload.get('benchmark_sha256', ''),
        )


def save(model: TranscriptModel, path: Path = ARTIFACT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.to_dict(), indent=2) + '\n', encoding='utf-8')
    return path


def load(path: Path = ARTIFACT) -> TranscriptModel:
    if not path.exists():
        raise FileNotFoundError('Our classifier has not been trained. Run scripts/train_classifier.py.')
    return TranscriptModel.from_dict(json.loads(path.read_text(encoding='utf-8')))


class Encoder:
    """Lazy DistilBERT encoder shared across predictions in one process."""
    def __init__(self, model_name: str = MODEL_NAME):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        cache = ROOT / '.model-cache'
        cache.mkdir(parents=True, exist_ok=True)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache, local_files_only=True)
        self.model = AutoModel.from_pretrained(model_name, cache_dir=cache, local_files_only=True)
        self.model.eval()

    def encode(self, texts: list[str], batch_size: int = 24) -> list[list[float]]:
        torch = self.torch
        output = []
        with torch.inference_mode():
            for start in range(0, len(texts), batch_size):
                batch = texts[start:start + batch_size]
                tokens = self.tokenizer(batch, padding=True, truncation=True, max_length=128, return_tensors='pt')
                hidden = self.model(**tokens).last_hidden_state
                mask = tokens['attention_mask'].unsqueeze(-1)
                pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
                output.extend(pooled.cpu().tolist())
        return output


class OurClassifier:
    def __init__(self, artifact: Path = ARTIFACT, encoder: Encoder | None = None):
        self.head = load(artifact)
        self.encoder = encoder or Encoder(self.head.model_name)

    def probabilities(self, texts: list[str]) -> list[float]:
        embeddings = self.encoder.encode(texts)
        return self.probabilities_from_embeddings(embeddings)

    def probabilities_from_embeddings(self, embeddings: list[list[float]]) -> list[float]:
        temperature = max(self.head.temperature, .05)
        return [
            _sigmoid((self.head.bias + sum(weight * value for weight, value in zip(self.head.weights, vector))) / temperature)
            for vector in embeddings
        ]

    def probability(self, text: str) -> float:
        return self.probabilities([text])[0]


SIGNAL_PATTERNS = {
    'urgency': (r'\burgent\b', r'\bimmediately\b', r'\bact (?:now|today)\b', r'\btime (?:is )?limited\b', r'\bdo not delay\b', r'\bbefore .*expire'),
    'impersonation': (r'\b(?:your )?bank\b', r'\bfraud (?:department|prevention)\b', r'\bgovernment\b', r'\btax (?:office|record)\b', r'\baccount team\b'),
    'payment_request': (r'\bpay\b', r'\bpayment\b', r'\btransfer\b', r'\bsend (?:money|funds|cryptocurrency)\b', r'\bgift cards?\b', r'\bmove the balance\b'),
    'code_request': (r'\bread (?:me|out).{0,25}\bcode\b', r'\btell me.{0,25}\bcode\b', r'\bshare.{0,25}\bcode\b', r'\bverification code\b', r'\bone-time code\b', r'\bpasscode\b'),
    'personal_info_request': (r'\bcard details\b', r'\bpassword\b', r'\brecovery phrase\b', r'\bverify your identity\b'),
    'threat': (r'\barrest\b', r'\bpenalty\b', r'\benforcement\b', r'\bservice .*turned off\b', r'\blegal problem\b'),
    'suspicious_action': (r'\bremote access\b', r'\bcontrol your screen\b', r'\bcontrol of your screen\b', r'\binstall .*support\b', r'\bsafe account\b'),
}

NEGATIONS = ('never ', 'do not ', "don't ", 'will not ', 'no ')


def extract_signals(text: str) -> list[dict]:
    """Return transparent transcript features for display, never for scoring."""
    lowered = text.lower()
    found = []
    for signal, patterns in SIGNAL_PATTERNS.items():
        evidence = ''
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if not match:
                continue
            prefix = lowered[max(0, match.start() - 12):match.start()]
            if any(prefix.endswith(negation) for negation in NEGATIONS):
                continue
            evidence = text[max(0, match.start() - 28):min(len(text), match.end() + 45)].strip()
            break
        if evidence:
            found.append({'type': signal, 'present': True, 'confidence': 1.0, 'evidence': evidence})
    return found
