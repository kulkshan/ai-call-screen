"""Single-host demo store. Do not use SQLite on multi-instance Cloud Run."""
import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time

DB = os.getenv('SESSION_DB', str(Path(__file__).parent / 'data' / 'sessions.sqlite'))
TTL = 1800


@contextmanager
def connection():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    db=sqlite3.connect(DB, timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, code TEXT UNIQUE, secret TEXT, expires REAL, call_sid TEXT UNIQUE, data TEXT)')
    db.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
    db.commit()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create(policy='follow_up'):
    sid=secrets.token_urlsafe(18)
    secret=secrets.token_urlsafe(32)
    with connection() as db:
        if db.execute('SELECT count(*) FROM sessions').fetchone()[0] >= 100:
            raise ValueError('Demo is at capacity. Try later.')
        for _ in range(20):
            code=str(secrets.randbelow(900000)+100000)
            expires=time.time()+TTL
            data={'id':sid,'code':code,'expires_at':expires,'status':'WAITING','policy':policy,
                  'conversation':[],'assessments':[],'risk_history':[],'caller_number':'',
                  'caller_context':None,'partial':'','error':None}
            try:
                db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?)',
                    (sid,code,hashlib.sha256(secret.encode()).hexdigest(),expires,None,json.dumps(data)))
                return {**data,'token':secret}
            except sqlite3.IntegrityError:
                continue
    raise ValueError('Unable to create a session.')


def get(sid, token=None):
    with connection() as db:
        row=db.execute('SELECT secret,data FROM sessions WHERE id=?',(sid,)).fetchone()
        if not row or (token is not None and not secrets.compare_digest(row[0], hashlib.sha256(token.encode()).hexdigest())):
            return None
        return json.loads(row[1])


def update(sid, **fields):
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT data FROM sessions WHERE id=?',(sid,)).fetchone()
        if row:
            data=json.loads(row[0]); data.update(fields)
            db.execute('UPDATE sessions SET data=? WHERE id=?',(json.dumps(data),sid))


def claim(code, call_sid, caller_number=''):
    if not call_sid:
        return None
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT id,call_sid,data FROM sessions WHERE code=?',(code,)).fetchone()
        if not row or row[1] not in (None,call_sid):
            return None
        data=json.loads(row[2])
        if row[1] is None:
            data['status']='CONNECTING'
            data['caller_number']=caller_number
            db.execute('UPDATE sessions SET call_sid=?,data=? WHERE id=?',(call_sid,json.dumps(data),row[0]))
        return data


def by_call(call_sid):
    with connection() as db:
        row=db.execute('SELECT data FROM sessions WHERE call_sid=?',(call_sid,)).fetchone()
        return json.loads(row[0]) if row else None


def claim_browser(identity, call_sid):
    if not identity or not call_sid: return None
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        for sid, bound, raw in db.execute('SELECT id,call_sid,data FROM sessions').fetchall():
            data=json.loads(raw)
            if data.get('browser_identity')!=identity: continue
            if bound==call_sid: return data
            if bound is not None or data['status']!='WAITING': return None
            data['status']='CONNECTING'
            db.execute('UPDATE sessions SET call_sid=?,data=? WHERE id=?',(call_sid,json.dumps(data),sid))
            return data
    return None


def recent_calls(limit=25):
    """Return redacted recent sessions for the local operational view."""
    limit=max(1,min(int(limit),100))
    with connection() as db:
        rows=db.execute('SELECT expires,data FROM sessions ORDER BY expires DESC LIMIT ?', (limit,)).fetchall()
    calls=[]
    for expires, raw in rows:
        data=json.loads(raw)
        calls.append({
            'id':data['id'][:8],
            'started_at':round(float(expires)-TTL),
            'status':data['status'],
            'conversation':data.get('conversation',[]),
            'assessments':data.get('assessments',[]),
            'error':data.get('error'),
        })
    return calls


if os.getenv('SESSION_STORE', 'sqlite').lower() == 'firestore':
    # Keep local SQLite for tests and development; Cloud Run imports these instead.
    from firestore_store import create, get, update, claim, by_call, claim_browser, TTL  # noqa: F401
