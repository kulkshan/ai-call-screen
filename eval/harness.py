"""Score the final benchmark test set with our transcript-only classifier."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re

from classifier.text_model import ARTIFACT, LEGACY_ARTIFACT, OurClassifier, extract_signals
from eval.metrics import by_subtype, calibration, call_metrics, policy_metrics, pr_curve
from evaluation.classifier_benchmark import MANIFEST, load as load_benchmark
from policy.cost_model import CostModel
from policy.evidence import assess as assess_evidence
from policy.tiers import decide
from signals.schemas import SIGNAL_TYPES


def _sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r'(?<=[.!?])\s+', text) if part.strip()]
    return parts or [text]


def _signal_payload(text: str, turn: int) -> dict:
    positive = {item['type']: item for item in extract_signals(text)}
    return {
        'turn_id': turn,
        'signals': [positive.get(name, {'type': name, 'present': False, 'confidence': 0.0, 'evidence': ''})
                    for name in SIGNAL_TYPES],
        'raw_response': '',
        'extractor_version': 'transparent-text-features-v1',
    }


def run(cost_model: CostModel | None = None) -> dict:
    cost_model = cost_model or CostModel()
    rows = load_benchmark()
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    artifact = json.loads(ARTIFACT.read_text(encoding='utf-8'))
    if artifact.get('benchmark_sha256') != manifest['sha256']:
        raise RuntimeError('Classifier artifact and benchmark do not match. Retrain before evaluation.')

    test_rows = [row for row in rows if row['split'] == 'test']
    classifier = OurClassifier()
    cumulative_inputs = []
    turn_keys = []
    for row in test_rows:
        cumulative = []
        for index, sentence in enumerate(_sentences(row['conversation'][0]['text']), start=1):
            cumulative.append(sentence)
            cumulative_inputs.append(' '.join(cumulative))
            turn_keys.append((row['id'], index, sentence, ' '.join(cumulative)))
    embeddings = classifier.encoder.encode(cumulative_inputs)
    probabilities = classifier.probabilities_from_embeddings(embeddings)
    baseline_probabilities = None
    if LEGACY_ARTIFACT.exists():
        baseline = OurClassifier(LEGACY_ARTIFACT, encoder=classifier.encoder)
        baseline_probabilities = baseline.probabilities_from_embeddings(embeddings)
    scored_turns = {}
    histories = {}
    for (scenario_id, index, sentence, cumulative_text), probability in zip(turn_keys, probabilities):
        history = histories.setdefault(scenario_id, [])
        history.append(probability)
        score_only_action = decide(probability, history, cost_model)
        evidence_quality = assess_evidence(cumulative_text)
        action = decide(
            probability, history, cost_model,
            evidence_sufficient=evidence_quality['sufficient'],
        )
        scored_turns.setdefault(scenario_id, []).append({
            'turn_index': index,
            'text': sentence,
            'probability': probability,
            'tier': action['tier'],
            'signals': _signal_payload(sentence, index),
            'evidence_quality': evidence_quality,
            'tier_before_evidence_gate': score_only_action['tier'],
            'decision': action,
        })

    baseline_final = {}
    if baseline_probabilities is not None:
        for (scenario_id, _index, _sentence, _cumulative_text), probability in zip(turn_keys, baseline_probabilities):
            baseline_final[scenario_id] = probability

    calls = []
    for row in test_rows:
        turns = scored_turns[row['id']]
        final = turns[-1]
        calls.append({
            'scenario_id': row['id'],
            'subtype': row['family'],
            'difficulty': 'controlled',
            'label': 'scam' if row['label'] == 1 else 'legit' if row['label'] == 0 else 'unclear',
            'expected_decision': 'ALLOW' if row['expected_decision'] == 'CONNECT' else row['expected_decision'],
            'probability': final['probability'],
            'baseline_probability': baseline_final.get(row['id']),
            'tier': final['tier'],
            'tier_before_evidence_gate': final['tier_before_evidence_gate'],
            'evidence_quality': final['evidence_quality'],
            'malicious_from_turn': None,
            'turns': turns,
            'metadata': {
                'reputation_risk': 0.0, 'frequency_anomaly': 0.0,
                'neighbor_spoof': 0.0, 'is_contact': False,
                'source': 'not used by transcript benchmark',
            },
        })

    binary_calls = [call for call in calls if call['label'] in ('scam', 'legit')]
    metrics = call_metrics(binary_calls, cost_model.false_negative_cost, cost_model.false_positive_cost)
    baseline_calls = [
        {**call, 'probability': baseline_final[call['scenario_id']]}
        for call in binary_calls if call['scenario_id'] in baseline_final
    ]
    baseline_metrics = call_metrics(
        baseline_calls, cost_model.false_negative_cost, cost_model.false_positive_cost
    ) if baseline_calls else None
    mistakes = [call for call in binary_calls if (call['probability'] >= .5) != (call['label'] == 'scam')]
    unclear_calls = [call for call in calls if call['label'] == 'unclear']
    unclear_before = sum(call['tier_before_evidence_gate'] == 'MONITOR' for call in unclear_calls)
    unclear_after = sum(call['tier'] == 'MONITOR' for call in unclear_calls)
    return {
        'run_id': 'our-classifier-final-test-v2',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'evaluation_status': 'independent_inference',
        'corpus': {
            'scenarios': len(rows), 'test_scenarios': len(calls),
            'binary_test_scenarios': len(binary_calls),
            'split': manifest['training_contract'],
            'provenance': manifest['provenance'],
            'sha256': manifest['sha256'],
        },
        'limitations': manifest['limitations'],
        'cost_model': cost_model.to_dict(),
        'derived_thresholds': decide(.5, [], cost_model)['thresholds'],
        'model': {
            'display_name': 'Our classifier',
            'model_version': artifact['model_version'],
            'base_encoder': artifact['model_name'],
            'input_contract': artifact['input_contract'],
            'artifact': str(ARTIFACT),
        },
        'metrics': metrics,
        'baseline_comparison': {
            'basis': 'Both classifiers scored the same 1,600 clearly labelled final test calls.',
            'before': baseline_metrics,
            'after': metrics,
        } if baseline_metrics else None,
        'policy_metrics': policy_metrics(binary_calls, cost_model.false_negative_cost, cost_model.false_positive_cost),
        'unclear_call_evaluation': {
            'count': len(unclear_calls),
            'before_evidence_gate': unclear_before,
            'after_evidence_gate': unclear_after,
            'before_rate': unclear_before / len(unclear_calls) if unclear_calls else None,
            'after_rate': unclear_after / len(unclear_calls) if unclear_calls else None,
        },
        'pr_curve': pr_curve(binary_calls),
        'calibration': calibration(binary_calls),
        'per_archetype': by_subtype(binary_calls),
        'failure_gallery': mistakes[:20],
        'calls': calls,
    }
