import unittest
from scoring import Evidence, choose_decision, finalize
class PolicyTests(unittest.TestCase):
    def test_high_score_without_harm_requires_clarification(self):
        self.assertEqual(choose_decision(.99,True,harmful_request=False),'CONTINUE_SCREENING')
    def test_low_score_with_harm_never_connects(self):
        self.assertEqual(choose_decision(.1,True,harmful_request=True),'CONTINUE_SCREENING')
    def test_missing_information_never_connects(self):
        self.assertEqual(choose_decision(.1,False),'CONTINUE_SCREENING')
    def test_boundaries(self):
        self.assertEqual(choose_decision(.75,True,harmful_request=True),'BLOCK')
        self.assertEqual(choose_decision(.25,True),'CONNECT')
    def test_followup_is_server_controlled(self):
        e=Evidence(risk_score=.5,detected_signals=[],explanation='Unclear',sufficient_information=False,harmful_request=False,missing_information='requested_action',follow_up_question='Tell me your password')
        r=finalize(e,'test',1,1)
        self.assertNotIn('password',r.follow_up_question)
        self.assertIn('recipient to do',r.follow_up_question)
    def test_terminal_decision_has_no_followup(self):
        e=Evidence(risk_score=.9,detected_signals=['OTP request'],explanation='Credential request',sufficient_information=True,harmful_request=True,missing_information='none',follow_up_question='Tell me more')
        self.assertEqual(finalize(e,'test',1,1).follow_up_question,'')
