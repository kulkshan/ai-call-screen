import hashlib
import json
import base64
import os
import unittest
from unittest.mock import patch, AsyncMock
from test_flow import main, signature, assessment
from fastapi.testclient import TestClient

SETTINGS=dict(TWILIO_ACCOUNT_SID='AC'+'1'*32,TWILIO_API_KEY_SID='SK'+'2'*32,TWILIO_API_KEY_SECRET='test-key-secret-for-unit-tests-only-123456',TWILIO_TWIML_APP_SID='AP'+'3'*32)

class BrowserTests(unittest.TestCase):
 def setUp(self):
  main.limits.clear();self.client=TestClient(main.app)
  self.env=patch.dict(os.environ,SETTINGS);self.env.start();self.addCleanup(self.env.stop)
  self.s=self.client.post('/api/sessions',json={'consent':True}).json()
  self.path='/api/sessions/'+self.s['id']+'/voice-token'
  self.auth={'Authorization':'Bearer '+self.s['token']}
 def token(self):return self.client.post(self.path,headers=self.auth)
 def call(self,identity,call='CA-browser'):
  params={'From':'client:'+identity,'CallSid':call,'AccountSid':SETTINGS['TWILIO_ACCOUNT_SID'],'SessionId':'untrusted'}
  return self.client.post('/twilio/browser-voice',data=params,headers=signature('/twilio/browser-voice',params))
 def test_token_is_private_short_lived_outgoing_only(self):
  self.assertEqual(self.client.post(self.path).status_code,404)
  r=self.token();self.assertEqual(r.status_code,200);self.assertEqual(r.headers['cache-control'],'no-store')
  payload=r.json()['token'].split('.')[1];p=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
  self.assertEqual(p['exp']-p['nbf'],300)
  self.assertNotIn('incoming',p['grants']['voice'])
  self.assertEqual(p['grants']['voice']['outgoing']['application_sid'],SETTINGS['TWILIO_TWIML_APP_SID'])
 def test_browser_pairing_and_screening(self):
  self.token();identity=main.store.get(self.s['id'])['browser_identity']
  self.assertNotIn('ConversationRelay',self.call('other').text)
  r=self.call(identity);self.assertIn('ConversationRelay',r.text);self.assertNotIn('Gather',r.text)
  self.assertNotIn('ConversationRelay',self.call(identity,'CA-thief').text)
  self.assertEqual(self.token().status_code,409)
  with patch.object(main,'assess',AsyncMock(return_value=assessment(.95))):
   with self.client.websocket_connect('/twilio/conversation-relay',headers=signature('/twilio/conversation-relay',ws=True)) as ws:
    ws.send_json({'type':'setup','callSid':'CA-browser'})
    ws.send_json({'type':'prompt','voicePrompt':'Give me your OTP','last':True})
    self.assertEqual(ws.receive_json()['type'],'end')
  self.assertEqual(main.store.get(self.s['id'])['status'],'BLOCK')
 def test_requires_configuration_and_signature(self):
  self.assertEqual(self.client.post('/twilio/browser-voice').status_code,403)
  with patch.dict(os.environ,{'TWILIO_API_KEY_SECRET':''}):
   self.assertFalse(self.client.get('/api/config').json()['browser_calling'])
   self.assertEqual(self.token().status_code,503)
 def test_other_session_cannot_request_token(self):
  other=self.client.post('/api/sessions',json={'consent':True}).json()
  self.assertEqual(self.client.post(self.path,headers={'Authorization':'Bearer '+other['token']}).status_code,404)
