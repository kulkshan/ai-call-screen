import asyncio
from collections import defaultdict, deque
import json
import os
from pathlib import Path
import time
from xml.etree.ElementTree import Element, SubElement, tostring

from dotenv import load_dotenv
load_dotenv(Path(__file__).with_name('.env'))
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from twilio.request_validator import RequestValidator
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
import hashlib
from caller_context import simulated_context
from defense_adapter import apply as apply_defense_pipeline
from models import CallerContext, ScreeningOutcome
from scoring import assess
from transcript_classifier import LegacyAssessmentClassifier
import store

app=FastAPI(title='Call Screen — live demo',version='2.0')
origins=os.getenv('FRONTEND_ORIGINS','http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type'])
limits=defaultdict(deque)
GREETING='This is an AI screening demo. Use fictional details. Who is calling, and what is the reason for your call?'


async def screen_live(conversation, caller_context, previous_scores=None):
    """Live entry point: our classifier scores; Gemini supplies explanation."""
    transcript = await LegacyAssessmentClassifier(assess).classify(conversation)
    raw_text=' '.join(item['text'] for item in conversation if item.get('role')=='caller')
    return apply_defense_pipeline(transcript, caller_context, previous_scores, raw_text)


def public_session(data):
    """The browser gets a masked caller identifier; raw caller number stays server-side."""
    safe=json.loads(json.dumps(data))
    safe.pop('caller_number',None)
    if isinstance(safe.get('caller_context'),dict):
        safe['caller_context'].pop('caller_number',None)
    return safe


def throttle(key, maximum, seconds):
    now=time.monotonic()
    queue=limits[key]
    while queue and queue[0] < now-seconds: queue.popleft()
    if len(queue)>=maximum: raise HTTPException(429,'Too many attempts. Please wait before trying again.')
    queue.append(now)
    if len(limits)>5000:
        for k in list(limits):
            if not limits[k] or limits[k][-1]<now-3600: limits.pop(k,None)


def base():
    value=os.getenv('PUBLIC_BASE_URL','').rstrip('/')
    if not value.startswith('https://'): raise HTTPException(503,'Public call URL is not configured.')
    return value


async def twilio(request):
    token=os.getenv('TWILIO_AUTH_TOKEN','')
    if not token: raise HTTPException(503,'Twilio is not configured.')
    form=await request.form()
    url=base()+request.url.path
    if request.url.query: url+='?'+request.url.query
    if not RequestValidator(token).validate(url,form,request.headers.get('x-twilio-signature','')):
        raise HTTPException(403,'Invalid Twilio signature.')
    return form


def xml(root): return Response(tostring(root),media_type='application/xml')
def finish(message):
    root=Element('Response'); SubElement(root,'Say').text=message; SubElement(root,'Hangup'); return xml(root)


def conversation_relay(connect):
    """Favor complete, clean caller turns over the fastest possible response."""
    return SubElement(
        connect, 'ConversationRelay',
        url=base().replace('https://', 'wss://', 1) + '/twilio/conversation-relay',
        welcomeGreeting=GREETING,
        welcomeGreetingInterruptible='none',
        transcriptionProvider='Deepgram', speechModel='flux',
        transcriptionLanguage='en-US', deepgramSmartFormat='true',
        # Flux uses these values for turn detection.  A higher threshold and a
        # longer silence ceiling prevent a natural mid-sentence pause from being
        # treated as the end of a caller turn.
        partialPrompts='true', eotThreshold='0.9', speechTimeout='3200',
        # The short, fixed agent messages should finish before listening resumes.
        # That makes the demo predictable and avoids callers clipping the prompt.
        interruptible='none', interruptSensitivity='low',
        reportInputDuringAgentSpeech='none', ignoreBackchannel='true',
    )


def merge_transcript(previous, incoming):
    """Reconcile a partial STT hypothesis with its next revision."""
    incoming = incoming.strip()
    if not previous or not incoming:
        return incoming or previous
    if incoming.startswith(previous):
        return incoming
    if previous.endswith(incoming):
        return previous
    # STT providers sometimes replace the final word of a partial hypothesis.
    # If most of the prior text is shared from the start, the newer hypothesis
    # is authoritative; appending it would show duplicated or invented words.
    shared=0
    for prior, current in zip(previous.lower(),incoming.lower()):
        if prior!=current: break
        shared+=1
    if shared>=max(4, int(min(len(previous),len(incoming))*0.6)):
        return incoming
    maximum = min(len(previous), len(incoming))
    for size in range(maximum, 0, -1):
        if previous[-size:].lower() == incoming[:size].lower():
            return previous + incoming[size:]
    return previous + ' ' + incoming


@app.get('/health')
async def health(): return {'status':'ok','version':'2.0'}


@app.get('/api/config')
async def config():
    return {'phone_number':os.getenv('TWILIO_PHONE_NUMBER',''),'session_ttl_seconds':store.TTL,
            'model':os.getenv('GEMINI_MODEL','gemini-3.8-flash'),
            'storage':'firestore' if os.getenv('SESSION_STORE','sqlite').lower()=='firestore' else 'single-host demo',
            'browser_calling':browser_ready(),
            'classifier':'Our transcript classifier',
            'caller_context':'simulated'}


class NewSession(BaseModel):
    consent: bool


@app.post('/api/sessions')
async def new_session(body:NewSession,request:Request):
    if not body.consent: raise HTTPException(400,'Consent is required to show and analyze the test transcript.')
    throttle('create:'+request.client.host,5,600)
    try: return store.create()
    except ValueError as exc: raise HTTPException(429,str(exc)) from None


@app.get('/api/sessions/{sid}')
async def session(sid:str,request:Request):
    header=request.headers.get('authorization','')
    token=header.removeprefix('Bearer ') if header.startswith('Bearer ') else ''
    data=store.get(sid,token)
    if not data: raise HTTPException(404,'Session not found or expired. Start a new test.')
    return Response(json.dumps(public_session(data)),media_type='application/json',headers={'Cache-Control':'no-store'})


class Transcript(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    transcript:str=Field(min_length=1,max_length=12000)


@app.post('/analyze',response_model=ScreeningOutcome)
async def analyze(body:Transcript):
    if os.getenv('TWILIO_PUBLIC_MODE')=='1': raise HTTPException(403,'Text testing is available only locally.')
    return await screen_live([{'role':'caller','text':body.transcript}], simulated_context())


@app.post('/twilio/voice')
async def voice(request:Request):
    await twilio(request)
    root=Element('Response')
    gather=SubElement(root,'Gather',input='dtmf',numDigits='6',timeout='15',action=base()+'/twilio/pair',method='POST')
    SubElement(gather,'Say').text='Welcome to the call screening demo. Enter the six digit session code shown on the website.'
    SubElement(root,'Say').text='No code received. Please start a session on the website and call again.'
    SubElement(root,'Hangup')
    return xml(root)


@app.post('/twilio/pair')
async def pair(request:Request):
    form=await twilio(request)
    # Bound pairing guesses by caller and call. Never log phone numbers.
    throttle('pair:'+str(form.get('From','')),5,600)
    caller_number=str(form.get('From',''))
    data=store.claim(str(form.get('Digits','')),str(form.get('CallSid','')),caller_number)
    if not data: return finish('That session code is invalid or already used. Please start a new session and call again.')
    context=simulated_context(caller_number)
    store.update(data['id'],caller_context=context.model_dump())
    root=Element('Response')
    connect=SubElement(root,'Connect',action=base()+'/twilio/complete',method='POST')
    conversation_relay(connect)
    return xml(root)


@app.post('/twilio/complete')
async def complete(request:Request):
    form=await twilio(request)
    data=store.by_call(str(form.get('CallSid','')))
    if not data: return finish('The screening session has ended.')
    status=data['status']
    if status=='BLOCK': message='This request appears unsafe. I will not connect this call. Goodbye.'
    elif status=='WARN': message='This call may be unsafe. Please use a verified number to contact the organization. Goodbye.'
    elif status in ('ALLOW','CONNECT'): message='Screening passed. In a real deployment this call would now connect. This demo does not transfer calls. Goodbye.'
    elif status=='UNRESOLVED': message='I could not verify the purpose of this call. The demo will end without connecting.'
    elif status=='ERROR': message='The analysis service is unavailable. The call has not been approved. Please try again later.'
    else:
        store.update(data['id'],status='ENDED',error='The call ended before a final assessment.')
        message='The screening session has ended.'
    return finish(message)


@app.websocket('/twilio/conversation-relay')
async def relay(ws:WebSocket):
    token=os.getenv('TWILIO_AUTH_TOKEN','')
    url=base().replace('https://','wss://',1)+'/twilio/conversation-relay'
    if not token or not RequestValidator(token).validate(url,{},ws.headers.get('x-twilio-signature','')):
        await ws.close(code=1008); return
    await ws.accept()
    sid=None; history=[]; assessments=[]; risk_history=[]; caller_context=None; parts=[]; turns=0
    try:
        async with asyncio.timeout(180):
            while True:
                event=await asyncio.wait_for(ws.receive_json(),60)
                if not isinstance(event,dict): raise ValueError('Malformed event')
                kind=event.get('type')
                if kind=='setup':
                    if sid: raise ValueError('Repeated setup')
                    data=store.by_call(str(event.get('callSid','')))
                    if not data or data['status']!='CONNECTING':
                        await ws.close(code=1008); return
                    sid=data['id']; history=[{'role':'agent','text':GREETING}]
                    caller_context=CallerContext.model_validate(data.get('caller_context') or simulated_context(data.get('caller_number','')).model_dump())
                    risk_history=list(data.get('risk_history',[]))
                    store.update(sid,status='RESPONDING',conversation=history,caller_context=caller_context.model_dump(),risk_history=risk_history)
                elif kind=='prompt':
                    if not sid or not isinstance(event.get('voicePrompt'),str) or type(event.get('last')) is not bool:
                        raise ValueError('Invalid prompt')
                    text=event['voicePrompt'].strip()
                    # Partial prompts are useful for the live UI, but they are
                    # provisional STT hypotheses. Never append them into the
                    # saved turn: the final Twilio prompt is authoritative.
                    parts=[text]
                    if len(text)+sum(len(x['text']) for x in history)>12000: raise ValueError('Conversation too long')
                    confidence=event.get('confidence')
                    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
                        confidence=None
                    store.update(sid,status='LISTENING',partial=text,
                                 stt_confidence=confidence)
                    if not event['last']: continue
                    parts=[]
                    if not text: continue
                    turns+=1; history.append({'role':'caller','text':text})
                    analysis_started_at=time.time()
                    store.update(sid,status='ANALYZING',conversation=history,partial='',analysis_started_at=analysis_started_at)
                    assessment=await screen_live(history, caller_context,
                        [item['final_risk_score'] for item in risk_history])
                    assessments.append(assessment.model_dump())
                    risk_history.append({
                        'turn':turns,
                        'transcript_risk_score':assessment.transcript_risk_score,
                        'final_risk_score':assessment.final_risk_score,
                        'decision':assessment.decision,
                    })
                    analysis_completed_at=time.time()
                    analysis_duration_ms=round((analysis_completed_at-analysis_started_at)*1000)
                    if assessment.decision in ('CONTINUE_SCREENING','WARN') and turns<3:
                        question=assessment.follow_up_question or 'Who do you represent, and what do you need the recipient to do?'
                        if assessment.decision=='WARN':
                            question='I need to verify this request. Do not share codes, passwords, or account details. ' + question
                        history.append({'role':'agent','text':question})
                        store.update(sid,status='RESPONDING',assessments=assessments,conversation=history,
                                     risk_history=risk_history,analysis_completed_at=analysis_completed_at,analysis_duration_ms=analysis_duration_ms)
                        # Do not let a quiet acknowledgment clip the safety question.
                        await ws.send_json({'type':'text','token':question,'last':True,'interruptible':False,'preemptible':False})
                    else:
                        status='UNRESOLVED' if assessment.decision=='CONTINUE_SCREENING' else assessment.decision
                        store.update(sid,status=status,assessments=assessments,conversation=history,
                                     risk_history=risk_history,analysis_completed_at=analysis_completed_at,analysis_duration_ms=analysis_duration_ms)
                        await ws.send_json({'type':'end','handoffData':json.dumps({'decision':assessment.decision,'status':status})})
                        return
                elif kind=='error': raise ValueError('ConversationRelay reported an error')
    except WebSocketDisconnect:
        if sid:
            data=store.get(sid)
            if data and data['status'] in ('LISTENING','ANALYZING','CONNECTING'):
                store.update(sid,status='ENDED',error='Caller disconnected before a final decision.')
    except (HTTPException,TimeoutError,ValueError) as exc:
        if sid: store.update(sid,status='ERROR',partial='',error=exc.detail if isinstance(exc,HTTPException) else 'Screening ended without a verified decision.')
        try: await ws.send_json({'type':'end','handoffData':json.dumps({'status':'error'})})
        except (WebSocketDisconnect,RuntimeError): pass


@app.get('/api/evaluation')
async def evaluation():
    path=Path(__file__).parent.parent/'evaluation'/'results.json'
    if not path.exists(): return {'status':'not_run','records':[]}
    return JSONResponse(json.loads(path.read_text(encoding='utf-8')),headers={'Cache-Control':'no-store'})


@app.get('/api/evaluation/cases')
async def evaluation_cases():
    """The labelled control set used by the offline evaluation runner.

    This source data is public to the demo and contains no customer calls or
    credentials. The browser uses it to tie a guided case to its row in the
    test set; scoring remains an explicit local runner action.
    """
    path=Path(__file__).parent.parent/'evaluation'/'cases.json'
    if not path.exists(): raise HTTPException(404,'Evaluation cases are unavailable.')
    return JSONResponse(json.loads(path.read_text(encoding='utf-8')),headers={'Cache-Control':'no-store'})


@app.get('/api/multisignal/cases')
async def multisignal_cases():
    """Small controlled cases for exercising caller context plus transcript risk."""
    path=Path(__file__).parent.parent/'evaluation'/'multisignal_cases.json'
    if not path.exists(): raise HTTPException(404,'Multi-signal test cases are unavailable.')
    return JSONResponse(json.loads(path.read_text(encoding='utf-8')),headers={'Cache-Control':'no-store'})


@app.get('/api/lab/report')
async def lab_report():
    """Latest no-network evaluation run used by the measurement dashboard."""
    path=Path(__file__).parent.parent/'eval'/'reports'/'latest.json'
    if not path.exists():
        raise HTTPException(404,'Run scripts/run_eval.py before opening the lab dashboard.')
    return JSONResponse(json.loads(path.read_text(encoding='utf-8')),headers={'Cache-Control':'no-store'})


@app.get('/api/lab/threshold-preview')
async def threshold_preview(false_positive_cost: float = 50.0):
    """Recalculate policy outcomes from the fixed test set for the UI slider."""
    if not 1 <= false_positive_cost <= 200:
        raise HTTPException(422,'False-positive cost must be between 1 and 200.')
    path=Path(__file__).parent.parent/'eval'/'reports'/'latest.json'
    if not path.exists():
        raise HTTPException(404,'Run scripts/run_eval.py before opening the lab dashboard.')
    from eval.metrics import policy_metrics
    from policy.cost_model import CostModel
    from policy.tiers import decide as decide_tier
    cost_model=CostModel(false_positive_cost=false_positive_cost)
    report=json.loads(path.read_text(encoding='utf-8'))
    calls=[]
    for call in report['calls']:
        state=decide_tier(call['probability'], [], cost_model)
        calls.append({**call,'tier':state['tier']})
    return {'cost_model':cost_model.to_dict(),'thresholds':decide_tier(.5,[],cost_model)['thresholds'],
            'metrics':policy_metrics(calls,cost_model.false_negative_cost,cost_model.false_positive_cost)}


@app.get('/api/lab/history')
async def lab_history():
    from eval.regression import history
    return {'runs':history()}


@app.get('/api/local/calls')
async def local_calls(request:Request):
    """Operational inspection for the local demo only; never expose on hosting."""
    if os.getenv('LOCAL_DEBUG')!='1' or request.client.host not in ('127.0.0.1','::1'):
        raise HTTPException(404,'Not found.')
    return {'calls':store.recent_calls()}


def browser_ready():
    return all(os.getenv(k,'').strip() for k in ('TWILIO_ACCOUNT_SID','TWILIO_API_KEY_SID','TWILIO_API_KEY_SECRET','TWILIO_TWIML_APP_SID','TWILIO_AUTH_TOKEN','PUBLIC_BASE_URL'))


@app.post('/api/sessions/{sid}/voice-token')
async def voice_token(sid:str,request:Request):
    token=request.headers.get('authorization','').removeprefix('Bearer ')
    data=store.get(sid,token)
    if not data: raise HTTPException(404,'Session not found or expired.')
    if data['status']!='WAITING': raise HTTPException(409,'Start a new session for another call.')
    if not browser_ready(): raise HTTPException(503,'Browser calling is not configured yet.')
    throttle('voice-token:'+sid,3,600)
    identity='screen_'+hashlib.sha256(sid.encode()).hexdigest()[:32]
    # Identity is signed into the token; never trust a client-supplied session parameter.
    store.update(sid,browser_identity=identity)
    access=AccessToken(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_API_KEY_SID'],
        os.environ['TWILIO_API_KEY_SECRET'],identity=identity,ttl=300)
    access.add_grant(VoiceGrant(outgoing_application_sid=os.environ['TWILIO_TWIML_APP_SID'],incoming_allow=False))
    jwt=access.to_jwt()
    return Response(json.dumps({'token':jwt.decode() if isinstance(jwt,bytes) else jwt}),media_type='application/json',headers={'Cache-Control':'no-store'})


@app.post('/twilio/browser-voice')
async def browser_voice(request:Request):
    form=await twilio(request)
    if form.get('AccountSid')!=os.getenv('TWILIO_ACCOUNT_SID'):
        raise HTTPException(403,'Invalid account.')
    caller=str(form.get('From',''))
    browser_identity=caller.removeprefix('client:') if caller.startswith('client:') else ''
    data=store.claim_browser(browser_identity,str(form.get('CallSid','')))
    if not data: return finish('This browser session is expired or already used. Please start a new test.')
    context=simulated_context('')
    store.update(data['id'],caller_context=context.model_dump())
    root=Element('Response')
    connect=SubElement(root,'Connect',action=base()+'/twilio/complete',method='POST')
    conversation_relay(connect)
    return xml(root)
