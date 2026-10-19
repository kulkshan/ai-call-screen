"""Cloud Run session store. Activated only with SESSION_STORE=firestore."""
import hashlib
import secrets
import time
from datetime import datetime, timezone, timedelta

from google.cloud import firestore
from google.cloud.firestore_v1 import transactional

TTL = 1800
_client = None


def client():
    global _client
    if _client is None:
        _client = firestore.Client()
    return _client


def sessions(): return client().collection('call_screen_sessions')
def codes(): return client().collection('call_screen_codes')
def calls(): return client().collection('call_screen_calls')


def _public(data, token=None):
    if not data or data.get('expires_at', 0) < time.time(): return None
    if token is not None and not secrets.compare_digest(data.get('secret', ''), hashlib.sha256(token.encode()).hexdigest()): return None
    data = dict(data); data.pop('secret', None); return data


def create(policy='follow_up'):
    secret=secrets.token_urlsafe(32); sid=secrets.token_urlsafe(18)
    for _ in range(20):
        code=str(secrets.randbelow(900000)+100000); now=time.time(); expires=now+TTL
        data={'id':sid,'code':code,'secret':hashlib.sha256(secret.encode()).hexdigest(),'expires_at':expires,
              'expire_at':datetime.now(timezone.utc)+timedelta(seconds=TTL),'status':'WAITING','policy':policy,
              'conversation':[],'assessments':[],'risk_history':[],'caller_number':'',
              'caller_context':None,'partial':'','error':None,'call_sid':None}
        transaction=client().transaction(); code_ref=codes().document(code); session_ref=sessions().document(sid)
        @transactional
        def create_once(tx):
            if tx.get(code_ref).exists: return False
            tx.set(code_ref,{'sid':sid,'expire_at':data['expire_at']}); tx.set(session_ref,data); return True
        if create_once(transaction):
            public=_public(data); public['token']=secret; return public
    raise ValueError('Unable to create a session.')


def get(sid, token=None):
    ref=sessions().document(sid); snapshot=ref.get(); data=_public(snapshot.to_dict() if snapshot.exists else None,token)
    if data is None and snapshot.exists: ref.delete()
    return data


def update(sid, **fields):
    fields=dict(fields); fields.pop('id',None); fields.pop('code',None); fields.pop('expires_at',None)
    sessions().document(sid).update(fields)


def _claim_from_sid(sid, call_sid, caller_number=''):
    if not sid or not call_sid: return None
    transaction=client().transaction(); ref=sessions().document(sid); call_ref=calls().document(hashlib.sha256(call_sid.encode()).hexdigest())
    @transactional
    def claim_once(tx):
        snap=tx.get(ref)
        if not snap.exists: return None
        data=snap.to_dict()
        if data.get('expires_at',0)<time.time() or data.get('call_sid') not in (None,call_sid): return None
        mapped=tx.get(call_ref)
        if mapped.exists and mapped.to_dict().get('sid')!=sid: return None
        if data.get('call_sid') is None:
            data['call_sid']=call_sid; data['status']='CONNECTING'; data['caller_number']=caller_number
            tx.update(ref,{'call_sid':call_sid,'status':'CONNECTING','caller_number':caller_number}); tx.set(call_ref,{'sid':sid,'expire_at':data['expire_at']})
        return _public(data)
    return claim_once(transaction)


def claim(code, call_sid, caller_number=''):
    snap=codes().document(code).get()
    return _claim_from_sid(snap.to_dict().get('sid') if snap.exists else None,call_sid,caller_number)


def by_call(call_sid):
    snap=calls().document(hashlib.sha256(call_sid.encode()).hexdigest()).get()
    return get(snap.to_dict().get('sid')) if snap.exists else None


def claim_browser(identity, call_sid):
    query=sessions().where('browser_identity','==',identity).limit(1).stream()
    snap=next(query,None)
    return _claim_from_sid(snap.id if snap else None,call_sid)
