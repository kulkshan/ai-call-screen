"""Metric definitions for the offline Call Screen report."""
import math


def _rate(numerator: int, denominator: int):
    return numerator / denominator if denominator else None


def wilson_interval(successes: int, total: int, z: float = 1.96):
    if not total:
        return None
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total) / denominator
    return [max(0.0, centre - margin), min(1.0, centre + margin)]


def confusion(calls: list[dict], threshold: float = .5) -> dict:
    """Classifier errors at one explicit probability threshold."""
    tp = sum(call['label'] == 'scam' and call['probability'] >= threshold for call in calls)
    fp = sum(call['label'] == 'legit' and call['probability'] >= threshold for call in calls)
    fn = sum(call['label'] == 'scam' and call['probability'] < threshold for call in calls)
    tn = sum(call['label'] == 'legit' and call['probability'] < threshold for call in calls)
    return {'true_positive': tp, 'false_positive': fp, 'false_negative': fn, 'true_negative': tn}


def call_metrics(calls: list[dict], false_negative_cost: float = 1.0, false_positive_cost: float = 50.0,
                 threshold: float = .5) -> dict:
    matrix = confusion(calls, threshold)
    tp, fp, fn, tn = (matrix[key] for key in ('true_positive', 'false_positive', 'false_negative', 'true_negative'))
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    fpr = _rate(fp, fp + tn)
    fnr = _rate(fn, fn + tp)
    f1 = _rate(2 * tp, 2 * tp + fp + fn)
    return {
        'count': len([call for call in calls if call['label'] in ('scam', 'legit')]),
        'classification_threshold': threshold, 'confusion_matrix': matrix,
        'precision': precision, 'recall': recall, 'f1': f1, 'false_positive_rate': fpr,
        'false_negative_rate': fnr,
        'expected_cost': (fn * false_negative_cost + fp * false_positive_cost) / len(calls) if calls else None,
        'confidence_intervals': {
            'precision': wilson_interval(tp, tp + fp), 'recall': wilson_interval(tp, tp + fn),
            'false_positive_rate': wilson_interval(fp, fp + tn), 'false_negative_rate': wilson_interval(fn, fn + tp),
        },
    }


def policy_metrics(calls: list[dict], false_negative_cost: float = 1.0, false_positive_cost: float = 50.0) -> dict:
    """Measure the final WARN/BLOCK action separately from model quality."""
    binary = [call for call in calls if call['label'] in ('scam', 'legit')]
    converted = [{**call, 'probability': 1.0 if call['tier'] in ('WARN', 'BLOCK') else 0.0}
                 for call in binary]
    return call_metrics(converted, false_negative_cost, false_positive_cost, threshold=.5)


def pr_curve(calls: list[dict]) -> dict:
    positives = sum(call['label'] == 'scam' for call in calls)
    if not calls or not positives:
        return {'points': [], 'average_precision': None}

    ranked = sorted(calls, key=lambda call: call['probability'], reverse=True)
    points = [{'threshold': None, 'precision': 1.0, 'recall': 0.0}]
    true_positives = 0
    false_positives = 0
    index = 0

    # Add a point after every distinct model score. This evaluates every
    # possible ranking cutoff instead of an arbitrary threshold grid.
    while index < len(ranked):
        threshold = ranked[index]['probability']
        while index < len(ranked) and ranked[index]['probability'] == threshold:
            if ranked[index]['label'] == 'scam':
                true_positives += 1
            else:
                false_positives += 1
            index += 1
        points.append({
            'threshold': threshold,
            'precision': true_positives / (true_positives + false_positives),
            'recall': true_positives / positives,
        })

    # Average precision: each recall gain is weighted by precision at that
    # operating point. This is stable for the step-shaped PR curve.
    area = sum(
        (right['recall'] - left['recall']) * right['precision']
        for left, right in zip(points, points[1:])
    )
    return {'points': points, 'average_precision': area}


def calibration(calls: list[dict]) -> dict:
    buckets = [[] for _ in range(10)]
    for call in calls:
        buckets[min(9, int(call['probability'] * 10))].append(call)
    bins = []
    ece = 0.0
    for index, bucket in enumerate(buckets):
        if not bucket:
            bins.append({'bin': index, 'count': 0, 'mean_prediction': None, 'observed_scam_rate': None})
            continue
        prediction = sum(call['probability'] for call in bucket) / len(bucket)
        observed = sum(call['label'] == 'scam' for call in bucket) / len(bucket)
        ece += len(bucket) / len(calls) * abs(prediction - observed)
        bins.append({'bin': index, 'count': len(bucket), 'mean_prediction': prediction, 'observed_scam_rate': observed})
    return {'expected_calibration_error': ece, 'bins': bins}


def signal_metrics(turns: list[dict]) -> dict:
    result = {}
    for name in ('urgency', 'impersonation', 'payment_request', 'code_request', 'personal_info_request', 'threat', 'suspicious_action'):
        tp = sum(name in turn['expected'] and turn['predicted'].get(name, False) for turn in turns)
        fp = sum(name not in turn['expected'] and turn['predicted'].get(name, False) for turn in turns)
        fn = sum(name in turn['expected'] and not turn['predicted'].get(name, False) for turn in turns)
        precision = _rate(tp, tp + fp)
        recall = _rate(tp, tp + fn)
        result[name] = {'precision': precision, 'recall': recall, 'f1': _rate(2 * tp, 2 * tp + fp + fn), 'support': tp + fn}
    return result


def by_subtype(calls: list[dict]) -> list[dict]:
    results = []
    for subtype in sorted({call['subtype'] for call in calls}):
        subset = [call for call in calls if call['subtype'] == subtype]
        row = call_metrics(subset)
        results.append({'subtype': subtype, 'label': subset[0]['label'], 'count': len(subset),
                        'recall': row['recall'] if subset[0]['label'] == 'scam' else None,
                        'false_positive_rate': row['false_positive_rate'] if subset[0]['label'] == 'legit' else None})
    return results
