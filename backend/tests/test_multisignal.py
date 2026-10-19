import json
import importlib.util
from pathlib import Path
import unittest

from caller_context import simulated_context
from decision_policy import decide
from models import ConversationSignals, TranscriptResult
from risk_combiner import combine, load_policy

generator_spec=importlib.util.spec_from_file_location('multisignal_generator',Path(__file__).resolve().parents[2]/'evaluation'/'generate_multisignal_set.py')
generator=importlib.util.module_from_spec(generator_spec);generator_spec.loader.exec_module(generator)


def transcript(score):
    return TranscriptResult(
        transcript_risk_score=score, confidence=.8, detected_signals=['Credential request'],
        conversation_signals=ConversationSignals(credential_request=True, suspicious_action_request=True),
        explanation='The caller asks for a code.', sufficient_information=True,
        harmful_request=True, missing_information='none', latency_ms=42,
    )


class MultiSignalTests(unittest.TestCase):
    def test_config_has_ordered_thresholds_and_documented_weights(self):
        policy=load_policy(); thresholds=policy['thresholds']
        self.assertLess(thresholds['continue_screening'],thresholds['warn'])
        self.assertLess(thresholds['warn'],thresholds['block'])
        self.assertIn('Initial prototype',policy['notes']['weights'])

    def test_known_contact_reduces_risk(self):
        unknown=simulated_context(caller_reputation_score=.3,recent_call_frequency=1)
        known=simulated_context(known_contact=True,caller_reputation_score=.3,recent_call_frequency=1)
        self.assertLess(combine(transcript(.5),known).final_risk_score,combine(transcript(.5),unknown).final_risk_score)

    def test_decision_policy_has_all_four_actions(self):
        policy=load_policy()
        self.assertEqual(decide(.1,'none',policy)[0],'ALLOW')
        self.assertEqual(decide(.5,'none',policy)[0],'CONTINUE_SCREENING')
        self.assertEqual(decide(.7,'none',policy)[0],'WARN')
        self.assertEqual(decide(.9,'none',policy)[0],'BLOCK')

    def test_controlled_multisignal_scenarios_are_complete(self):
        path=Path(__file__).resolve().parents[2]/'evaluation'/'multisignal_cases.json'
        records=json.loads(path.read_text(encoding='utf-8'))['records']
        self.assertEqual(len(records),5)
        self.assertEqual({record['name'] for record in records},{
            'Normal appointment call','Obvious one-time-code scam','Legitimate bank fraud notice',
            'Call that becomes malicious','Paraphrased payment scam'})
        self.assertTrue(all(record['turns'] and record['caller_context'] for record in records))

    def test_one_thousand_case_set_has_a_balanced_action_key(self):
        rows=generator.build()
        self.assertEqual(len(rows),1000)
        self.assertEqual({action:sum(row['expected_decision']==action for row in rows)
                          for action in ('ALLOW','CONTINUE_SCREENING','WARN','BLOCK')},
                         {'ALLOW':250,'CONTINUE_SCREENING':250,'WARN':250,'BLOCK':250})
