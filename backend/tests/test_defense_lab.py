import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from policy.cost_model import CostModel, derive_thresholds
from policy.evidence import assess as assess_evidence
from policy.tiers import decide
from eval.metrics import pr_curve
from sim.generator import generate
from signals.metadata import from_scenario


class DefenseLabTests(unittest.TestCase):
    def test_generated_corpus_has_expected_shape_and_grouped_splits(self):
        scenarios = generate()
        self.assertEqual(len(scenarios), 1200)
        self.assertEqual(sum(scenario.label == 'scam' for scenario in scenarios), 600)
        self.assertEqual(sum(scenario.label == 'legit' for scenario in scenarios), 600)
        group_splits = {}
        for scenario in scenarios:
            group_splits.setdefault(scenario.group_id, set()).add(scenario.split)
        self.assertTrue(all(len(splits) == 1 for splits in group_splits.values()))
        self.assertTrue(all(scenario.reports is not None for scenario in scenarios))

    def test_metadata_is_computed_from_profile_and_reports(self):
        scenario = generate()[0]
        metadata = from_scenario(scenario.caller_profile, scenario.reports, scenario.recipient_npa_nxx)
        self.assertGreaterEqual(metadata.reputation_risk, 0)
        self.assertLessEqual(metadata.reputation_risk, 1)
        self.assertGreaterEqual(metadata.frequency_anomaly, 0)
        self.assertLessEqual(metadata.frequency_anomaly, 1)

    def test_false_positive_cost_moves_the_derived_warning_boundary(self):
        low = derive_thresholds(CostModel(false_positive_cost=5))
        high = derive_thresholds(CostModel(false_positive_cost=100))
        self.assertLess(low['warn'], high['warn'])

    def test_precision_recall_curve_spans_zero_to_full_recall(self):
        calls = [
            {'label': 'scam', 'probability': .9},
            {'label': 'legit', 'probability': .8},
            {'label': 'scam', 'probability': .7},
            {'label': 'legit', 'probability': .1},
        ]
        result = pr_curve(calls)
        self.assertEqual(result['points'][0]['recall'], 0)
        self.assertEqual(result['points'][-1]['recall'], 1)
        self.assertAlmostEqual(result['average_precision'], 5 / 6)

    def test_vague_call_stays_in_screening_despite_extreme_score(self):
        quality = assess_evidence('I am calling about your account. I need to discuss something with you.')
        result = decide(.999, [.999], CostModel(), evidence_sufficient=quality['sufficient'])
        self.assertFalse(quality['sufficient'])
        self.assertEqual(result['tier'], 'MONITOR')

    def test_concrete_request_can_reach_a_terminal_decision(self):
        quality = assess_evidence('Read me the six digit code we sent you right now.')
        result = decide(.999, [.999], CostModel(), evidence_sufficient=quality['sufficient'])
        self.assertTrue(quality['sufficient'])
        self.assertEqual(result['tier'], 'BLOCK')

    def test_clear_legitimate_purpose_can_be_allowed(self):
        quality = assess_evidence('Your dental appointment is tomorrow at ten.')
        result = decide(.001, [.001], CostModel(), evidence_sufficient=quality['sufficient'])
        self.assertTrue(quality['sufficient'])
        self.assertEqual(result['tier'], 'ALLOW')


if __name__ == '__main__':
    unittest.main()
