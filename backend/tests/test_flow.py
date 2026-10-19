import os
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from pathlib import Path

temp = tempfile.TemporaryDirectory()
os.environ.update(SESSION_DB=str(Path(temp.name)/'sessions.sqlite'), PUBLIC_BASE_URL='https://demo.example', TWILIO_AUTH_TOKEN='test-token', TWILIO_PUBLIC_MODE='1')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import main
from scoring import Assessment, ScreeningFeatures, choose_decision
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

def signature(path,params=None,ws=False):
    url=('wss://demo.example' if ws else 'https://demo.example')+path
    return {'X-Twilio-Signature':RequestValidator('test-token').compute_signature(url,params or {})}

def assessment(score,sufficient=True):
    harmful=score>=.75
    features=ScreeningFeatures(credential_or_otp_request=harmful,financial_impersonation=harmful,
                               urgency_or_pressure=harmful, clear_benign_purpose=score<=.25)
    signal_evidence=([{'type':'code_request','present':True,'confidence':.95,'evidence':'Give me your code'},
                      {'type':'impersonation','present':True,'confidence':.95,'evidence':'This is your bank'},
                      {'type':'urgency','present':True,'confidence':.80,'evidence':'immediately'}] if harmful else [])
    return Assessment(risk_score=score,detected_signals=['test evidence'],features=features,signal_evidence=signal_evidence,explanation='Test assessment',sufficient_information=sufficient,harmful_request=harmful,missing_information='none' if sufficient else 'identity_purpose',follow_up_question='What do you need the recipient to do?',decision=choose_decision(score,sufficient,harmful_request=harmful),latency_ms=123,model='test-model')

class FlowTests(unittest.TestCase):
    def setUp(self):
        main.limits.clear()
        self.client=TestClient(main.app)
    def paired(self,call):
        s=self.client.post('/api/sessions',json={'consent':True}).json()
        params={'Digits':s['code'],'CallSid':call,'From':call}
        r=self.client.post('/twilio/pair',data=params,headers=signature('/twilio/pair',params))
        self.assertEqual(r.status_code,200)
        self.assertIn('ConversationRelay',r.text)
        return s
    def fetch(self,s):
        return self.client.get('/api/sessions/'+s['id'],headers={'Authorization':'Bearer '+s['token']}).json()
    def test_session_access_and_signature(self):
        s=self.client.post('/api/sessions',json={'consent':True}).json()
        self.assertEqual(self.client.get('/api/sessions/'+s['id']).status_code,404)
        self.assertEqual(self.fetch(s)['status'],'WAITING')
        self.assertEqual(self.client.post('/twilio/voice').status_code,403)
        self.assertIn('Gather',self.client.post('/twilio/voice',headers=signature('/twilio/voice')).text)
        self.assertEqual(self.client.post('/analyze',json={'transcript':'test'}).status_code,403)

    def test_controlled_evaluation_cases_are_served(self):
        response=self.client.get('/api/evaluation/cases')
        self.assertEqual(response.status_code,200)
        data=response.json()
        self.assertEqual(data['version'],'synthetic-pilot-v1')
        self.assertEqual(len(data['records']),18)

    def test_relay_uses_deliberate_turn_taking(self):
        r=self.client.post('/twilio/voice',headers=signature('/twilio/voice'))
        # Phone pairing is separate; inspect a completed relay response instead.
        s=self.paired('CA-relay-options')
        params={'Digits':s['code'],'CallSid':'CA-relay-options','From':'CA-relay-options'}
        response=self.client.post('/twilio/pair',data=params,headers=signature('/twilio/pair',params))
        self.assertIn('speechTimeout="3200"',response.text)
        self.assertIn('eotThreshold="0.9"',response.text)
        self.assertIn('interruptible="none"',response.text)
        self.assertIn('interruptSensitivity="low"',response.text)
        self.assertIn('welcomeGreetingInterruptible="none"',response.text)

    def test_partial_transcript_revisions_do_not_duplicate_words(self):
        self.assertEqual(main.merge_transcript('This is your', 'This is your bank'), 'This is your bank')
        self.assertEqual(main.merge_transcript('This is your bank', 'bank calling'), 'This is your bank calling')
        self.assertEqual(main.merge_transcript('This is your bane', 'This is your bank'), 'This is your bank')
    def test_final_prompt_replaces_a_partial_hypothesis(self):
        s=self.paired('CA-final-authority')
        with patch.object(main,'assess',AsyncMock(return_value=assessment(.95))):
            with self.client.websocket_connect('/twilio/conversation-relay',headers=signature('/twilio/conversation-relay',ws=True)) as ws:
                ws.send_json({'type':'setup','callSid':'CA-final-authority'})
                ws.send_json({'type':'prompt','voicePrompt':'This is Chase fraud pre','last':False})
                self.assertEqual(self.fetch(s)['partial'],'This is Chase fraud pre')
                ws.send_json({'type':'prompt','voicePrompt':'This is Chase fraud prevention. Send your verification code.','last':True})
                self.assertEqual(ws.receive_json()['type'],'end')
        state=self.fetch(s)
        caller=[line['text'] for line in state['conversation'] if line['role']=='caller']
        self.assertEqual(caller,['This is Chase fraud prevention. Send your verification code.'])
    def test_block_and_spoken_completion(self):
        s=self.paired('CA-block')
        with patch.object(main,'assess',AsyncMock(return_value=assessment(.95))):
            with self.client.websocket_connect('/twilio/conversation-relay',headers=signature('/twilio/conversation-relay',ws=True)) as ws:
                ws.send_json({'type':'setup','callSid':'CA-block'})
                ws.send_json({'type':'prompt','voicePrompt':'Give me your code','last':True})
                self.assertEqual(ws.receive_json()['type'],'end')
        self.assertEqual(self.fetch(s)['status'],'BLOCK')
        params={'CallSid':'CA-block'}
        r=self.client.post('/twilio/complete',data=params,headers=signature('/twilio/complete',params))
        self.assertIn('will not connect',r.text)
    def test_followup_then_connect(self):
        s=self.paired('CA-follow')
        fake=AsyncMock(side_effect=[assessment(.5,False),assessment(.1)])
        with patch.object(main,'assess',fake):
            with self.client.websocket_connect('/twilio/conversation-relay',headers=signature('/twilio/conversation-relay',ws=True)) as ws:
                ws.send_json({'type':'setup','callSid':'CA-follow'})
                ws.send_json({'type':'prompt','voicePrompt':'Calling about an appointment','last':True})
                self.assertEqual(ws.receive_json()['type'],'text')
                ws.send_json({'type':'prompt','voicePrompt':'Just a reminder for tomorrow','last':True})
                self.assertEqual(ws.receive_json()['type'],'end')
        state=self.fetch(s)
        self.assertEqual(state['status'],'ALLOW')
        self.assertEqual(len(state['assessments']),2)
        self.assertEqual(len(state['conversation']),4)
    def test_pairing_cannot_be_stolen(self):
        s=self.paired('CA-owner')
        params={'Digits':s['code'],'CallSid':'CA-other','From':'other'}
        r=self.client.post('/twilio/pair',data=params,headers=signature('/twilio/pair',params))
        self.assertNotIn('ConversationRelay',r.text)
    def test_error_never_connects(self):
        s=self.paired('CA-error')
        with patch.object(main,'assess',AsyncMock(side_effect=main.HTTPException(503,'Service busy'))):
            with self.client.websocket_connect('/twilio/conversation-relay',headers=signature('/twilio/conversation-relay',ws=True)) as ws:
                ws.send_json({'type':'setup','callSid':'CA-error'})
                ws.send_json({'type':'prompt','voicePrompt':'Hello','last':True})
                self.assertEqual(ws.receive_json()['type'],'end')
        self.assertEqual(self.fetch(s)['status'],'ERROR')

if __name__=='__main__': unittest.main()
