'use client';

import { useEffect, useRef, useState } from 'react';
import BrowserCall from './BrowserCall';
import staticReport from './data/public-report.json';
import LabNav from './lab/LabNav';
import liveStyles from './live.module.css';
import styles from './page.module.css';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8002';
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || '';
const STATIC_DEMO = process.env.NEXT_PUBLIC_STATIC_DEMO === '1';
const terminal = ['ALLOW', 'CONNECT', 'WARN', 'BLOCK', 'UNRESOLVED', 'ERROR', 'ENDED'];
const guidedCases = [
  ['benchmark-v2-remote_access-0401', 'Remote access request', 'Caller asks to control your device', '!'],
  ['benchmark-v2-delivery_notice-0401', 'Delivery notice', 'A routine package update', '✓'],
  ['benchmark-v2-vague_account-0416', 'Unclear request', 'Caller gives too little detail', '?'],
];
const statusLabel = { WAITING: 'Ready', CONNECTING: 'Connecting', RESPONDING: 'Agent is speaking', LISTENING: 'Listening', ANALYZING: 'Assessing', ALLOW: 'Screening passed', CONNECT: 'Screening passed', WARN: 'Safety warning', BLOCK: 'Call blocked', UNRESOLVED: 'Needs review', ERROR: 'Screening unavailable', ENDED: 'Call ended' };
const greeting = 'Hi — who is calling, and what is this about?';

function Progress({ stage }) {
  const steps = [['demo', '1', 'Try Call Screen'], ['evidence', '2', 'Check the test set'], ['recommendation', '3', 'See the next test']];
  const current = steps.findIndex(([id]) => id === stage);
  return <nav className={styles.progress} aria-label="Demo progress">{steps.map(([id, number, label], index) => <div className={styles.progressItem} key={id}><div className={styles.progressNumber + ' ' + (index <= current ? styles.progressActive : '')}>{number}</div><span>{label}</span>{index < steps.length - 1 && <div className={styles.progressLine + ' ' + (index < current ? styles.progressLineActive : '')} />}</div>)}</nav>;
}

function assessmentRows(assessment) {
  if (assessment?.features && typeof assessment.features === 'object') return Object.entries(assessment.features);
  return (assessment?.detected_signals || []).map(signal => [signal, true]);
}

function guidedRecord(call) {
  if (!call) return null;
  const transcript = call.turns.map(turn => turn.text).join(' ');
  return {
    id: call.scenario_id,
    expected_decision: call.expected_decision,
    conversation: [{ role: 'caller', text: transcript }],
    assessment: {
      decision: call.tier === 'MONITOR' ? 'CONTINUE_SCREENING' : call.tier,
      features: {
        'scam probability': `${(call.probability * 100).toFixed(1)}%`,
        'decision evidence': call.evidence_quality?.sufficient ? call.evidence_quality.kind : 'not enough yet',
        ...(call.evidence_quality?.cue ? { 'evidence phrase': `“${call.evidence_quality.cue}”` } : {}),
      },
      final_risk_score: call.probability,
      transcript_risk_score: call.probability,
      confidence: Math.abs(call.probability - 0.5) * 2,
      explanation: `Our classifier scored this final-test transcript at ${(call.probability * 100).toFixed(1)}% risk.`,
      latency_ms: 0,
    },
  };
}

function RiskSnapshot({ assessment, history = [] }) {
  const percentage = value => typeof value === 'number' ? Math.round(value * 100) + '%' : '—';
  return <section className={styles.riskSnapshot} aria-label="Live risk summary">
    <div className={styles.riskTopline}><span className={styles.kicker}>LIVE RISK</span><strong>{percentage(assessment.final_risk_score)}</strong></div>
    <div className={styles.riskGrid}><div><span>Transcript</span><strong>{percentage(assessment.transcript_risk_score)}</strong></div><div><span>Caller context</span><strong>{percentage(assessment.caller_context_risk_score)}</strong><small>Simulated</small></div><div><span>Confidence</span><strong>{percentage(assessment.confidence)}</strong></div><div><span>Caller</span><strong>{assessment.caller_context?.caller_number_masked || 'Unknown caller'}</strong><small>Masked</small></div></div>
    <div className={styles.riskHistory}><span>Risk across the call</span><div>{history.map((point, index) => <i key={index} style={{ height: Math.max(8, Math.round(point.final_risk_score * 42)) + 'px' }} title={`Turn ${point.turn}: ${percentage(point.final_risk_score)}`} />)}</div></div>
  </section>;
}

function Decision({ assessment, caseRecord, simulated, live, history, onNext }) {
  if (!assessment) return <div className={styles.decisionPlaceholder}><div className={styles.placeholderMark}>◌</div><p>The decision appears after the call finishes.</p></div>;
  const decision = assessment.decision;
  const style = decision === 'BLOCK' ? styles.block : decision === 'ALLOW' || decision === 'CONNECT' ? styles.connect : decision === 'WARN' ? styles.warn : styles.continue;
  const action = decision === 'CONTINUE_SCREENING' ? 'CONTINUE SCREENING' : decision;
  const systemText = caseRecord
    ? 'This is one of 2,000 final test calls kept separate from training and tuning.'
    : live
    ? `Our classifier assessed the completed caller turn in ${assessment.latency_ms} ms, then combined it with simulated caller context.`
    : simulated
      ? 'This is a simulated control result that demonstrates the evaluation workflow. It is not a Gemini performance claim.'
      : 'This stored transcript was scored by the same classifier and decision policy used for a live call.';
  return <div className={styles.decisionContent}>
    <div className={styles.decisionBanner + ' ' + style}><span className={styles.decisionIcon}>{decision === 'BLOCK' ? '⊘' : decision === 'ALLOW' || decision === 'CONNECT' ? '✓' : decision === 'WARN' ? '!' : '?'}</span><div><strong>{action}</strong><span>{decision === 'BLOCK' ? 'The call is not connected.' : decision === 'ALLOW' || decision === 'CONNECT' ? 'The call can continue.' : decision === 'WARN' ? 'The agent gives a safety warning and asks one more question.' : 'The agent asks one focused question.'}</span></div></div>
    {live && <RiskSnapshot assessment={assessment} history={history} />}
    {caseRecord && <div className={styles.caseLink}><span>CHECK AGAINST THE LABEL</span><strong>Expected {caseRecord.expected_decision.replaceAll('_', ' ')}</strong><small>Call Screen chose {action}</small></div>}
    <div className={styles.evidenceTitle}>What drove the score</div>
    <ul className={styles.featureList}>{assessmentRows(assessment).map(([name, value]) => <li key={name}><code>{name}</code><strong>{String(value)}</strong></li>)}</ul>
    <p className={styles.systemBehavior}>{systemText}</p>
    {assessment.explanation && <p className={styles.decisionExplanation}>{assessment.explanation}</p>}
    <button className={styles.nextButton} onClick={onNext}>See all 2,000 test results <span>→</span></button>
  </div>;
}

function Telemetry({ session, latest, enabled, onToggle }) {
  const assessments = session?.assessments || [];
  const tokenCount = assessments.reduce((total, item) => total + (item.total_tokens || 0), 0);
  const cost = assessments.reduce((total, item) => total + (item.cost_estimate_usd || 0), 0);
  const hasCost = assessments.some(item => typeof item.cost_estimate_usd === 'number');
  return <section className={styles.telemetry} aria-label="Live call telemetry"><div className={styles.telemetryTop}><div><span className={styles.kicker}>LIVE CALL TELEMETRY</span><small>Available only for browser calls.</small></div><button className={enabled ? styles.telemetryToggleOn : styles.telemetryToggle} onClick={onToggle} aria-pressed={enabled}>{enabled ? 'On' : 'Off'}</button></div>{enabled && <><div className={styles.telemetryGrid}><div><span>Transcript analysis</span><strong>{latest?.latency_ms ? latest.latency_ms + ' ms' : '—'}</strong></div><div><span>Transcript tokens</span><strong>{tokenCount || '—'}</strong></div><div><span>STT confidence</span><strong>{typeof session?.stt_confidence === 'number' ? Math.round(session.stt_confidence * 100) + '%' : 'Not reported'}</strong></div><div><span>Cost estimate</span><strong>{hasCost ? '$' + cost.toFixed(4) : 'Rate not set'}</strong></div></div><p className={styles.telemetryNote}>Values appear only when a provider supplies them. No value is invented for the demo.</p></>}</section>;
}

function Matrix({ summary, selected }) {
  const c = summary.confusion;
  const score = (top, bottom) => bottom ? Math.round((top / bottom) * 100) + '%' : '—';
  return <><div className={styles.matrix}><div className={styles.matrixBlank}></div><div className={styles.matrixAxis}>Blocked</div><div className={styles.matrixAxis}>Not blocked</div><div className={styles.matrixAxis}>Actually harmful</div><div><small>TRUE POSITIVE</small><strong>{c.tp}</strong><span>Protected</span></div><div><small>FALSE NEGATIVE</small><strong>{c.fn}</strong><span>Missed</span></div><div className={styles.matrixAxis}>Actually helpful</div><div><small>FALSE POSITIVE</small><strong>{c.fp}</strong><span>Blocked</span></div><div><small>TRUE NEGATIVE</small><strong>{c.tn}</strong><span>Allowed</span></div></div><div className={styles.metrics}><div><small>Precision</small><strong>{score(c.tp, c.tp + c.fp)}</strong></div><div><small>Recall</small><strong>{score(c.tp, c.tp + c.fn)}</strong></div><div><small>p95 decision time</small><strong>{summary.p95_ms ? Math.round(summary.p95_ms) + ' ms' : '—'}</strong></div></div>{selected && <p className={styles.selectedCaseNote}><strong>{selected.id}</strong> is the guided call you just ran. Expected: {selected.expected_decision.replaceAll('_', ' ')}. Observed: {selected.assessment?.decision?.replaceAll('_', ' ') || 'not yet recorded'}.</p>}</>;
}

export default function Home() {
  const [stage, setStage] = useState('demo'); const [mode, setMode] = useState('guided'); const [selectedId, setSelectedId] = useState(guidedCases[0][0]); const [reveal, setReveal] = useState(0); const [playing, setPlaying] = useState(false); const [config, setConfig] = useState(null); const [session, setSession] = useState(null); const [credentials, setCredentials] = useState(null); const [consent, setConsent] = useState(false); const [error, setError] = useState(''); const [evaluation, setEvaluation] = useState(null); const [cases, setCases] = useState(null); const [labReport, setLabReport] = useState(staticReport); const [evaluationError, setEvaluationError] = useState(''); const [telemetryOn, setTelemetryOn] = useState(false); const topRef = useRef(null);
  const results = evaluation?.records || []; const selected = guidedRecord(labReport?.calls?.find(call => call.scenario_id === selectedId)); const guidedMeta = guidedCases.find(([id]) => id === selectedId) || guidedCases[0]; const latest = session?.assessments?.at(-1); const active = session && !terminal.includes(session.status); const heldOut = evaluation?.summaries?.held_out; const simulated = evaluation?.simulated === true || evaluation?.status === 'simulated'; const missed = results.find(row => row.label === 1 && row.assessment?.decision !== 'BLOCK'); const falseBlock = results.find(row => row.label === 0 && row.assessment?.decision === 'BLOCK');
  useEffect(() => { if (STATIC_DEMO) return; fetch(API + '/api/config').then(response => response.ok ? response.json() : Promise.reject()).then(setConfig).catch(() => setError('The live-call backend is unavailable.')); }, []);
  useEffect(() => { if (!STATIC_DEMO && new URLSearchParams(window.location.search).get('mode') === 'live') setMode('live'); }, []);
  useEffect(() => { if (STATIC_DEMO) return; Promise.all([fetch(API + '/api/evaluation', { cache: 'no-store' }), fetch(API + '/api/evaluation/cases', { cache: 'no-store' })]).then(async ([resultResponse, caseResponse]) => { if (!resultResponse.ok || !caseResponse.ok) throw Error(); setEvaluation(await resultResponse.json()); setCases(await caseResponse.json()); }).catch(() => setEvaluationError('The controlled test set could not be loaded.')); }, []);
  useEffect(() => { if (STATIC_DEMO) return; fetch(API + '/api/lab/report', { cache: 'no-store' }).then(response => response.ok ? response.json() : Promise.reject()).then(setLabReport).catch(() => {}); }, []);
  useEffect(() => { if (!credentials) return; let stopped = false; let timer; const controller = new AbortController(); async function poll() { try { const response = await fetch(API + '/api/sessions/' + credentials.id, { headers: { Authorization: 'Bearer ' + credentials.token }, cache: 'no-store', signal: controller.signal }); if (!response.ok) throw Error(); const data = await response.json(); if (!stopped) { setSession(data); setError(''); } } catch { if (!stopped) setError('Live updates were interrupted. Reconnecting…'); } finally { if (!stopped) timer = setTimeout(poll, 1000); } } poll(); return () => { stopped = true; clearTimeout(timer); controller.abort(); }; }, [credentials]);
  useEffect(() => { if (!playing) return; const timers = [setTimeout(() => setReveal(1), 250), setTimeout(() => setReveal(2), 1200), setTimeout(() => { setReveal(3); setPlaying(false); }, 2300)]; return () => timers.forEach(clearTimeout); }, [playing, selectedId]);
  const go = target => { setStage(target); setTimeout(() => topRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0); }; const choose = id => { setMode('guided'); setSelectedId(id); setReveal(0); setPlaying(false); }; const play = () => { setReveal(0); setPlaying(true); };
  async function startLive() { try { setError(''); const response = await fetch(API + '/api/sessions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ consent }) }); const data = await response.json(); if (!response.ok) throw Error(data.detail || 'Could not start a browser call.'); const auth = { id: data.id, token: data.token }; setSession(data); setCredentials(auth); return auth; } catch (err) { setError(err.message); } }
  return <main className={`${styles.page} ${liveStyles.page}`} ref={topRef}><LabNav active="live" />
    {stage === 'demo' && <><section className={styles.productIntro}><span className={styles.kicker}>{STATIC_DEMO ? 'CALL SCREEN · DATA SCIENCE CASE STUDY' : 'LIVE CALL · SAME SCREENING PIPELINE'}</span><h1>Try Call Screen. Then see if it works at scale.</h1><p>{STATIC_DEMO ? 'Run one simulated call. Then review precision, recall, false alarms, and the remaining errors across 2,000 unseen test calls.' : 'The guided examples and your browser call use the same classifier and decision policy. Live calls demonstrate the experience; they do not change the published evaluation metrics.'}</p></section><section className={styles.demoGrid} aria-label="Call Screen demo"><aside className={styles.scenarioPanel}><span className={styles.kicker}>{STATIC_DEMO ? '1 / CHOOSE A CALL' : 'CHOOSE HOW TO TRY IT'}</span><h2>{STATIC_DEMO ? 'Pick a call.' : 'Guided or live.'}</h2><p>{STATIC_DEMO ? 'The correct action stays hidden until Call Screen decides.' : 'Guided calls use labeled examples from the final test set. Live calls use your microphone and have no known correct answer.'}</p><div className={styles.scenarioList}>{guidedCases.map(([id, title, subtitle, symbol]) => <button key={id} onClick={() => choose(id)} className={styles.scenarioButton + ' ' + (mode === 'guided' && selectedId === id ? styles.scenarioSelected : '')}><span className={styles.scenarioSymbol}>{symbol}</span><span><strong>{title}</strong><small>{subtitle}</small></span><b>›</b></button>)}</div>{!STATIC_DEMO && <><button className={styles.liveButton + ' ' + (mode === 'live' ? styles.liveSelected : '')} onClick={() => { setMode('live'); setReveal(0); }}>Use my microphone</button><p className={styles.quiet}>Uses Twilio and our transcript classifier. Use fictional details.</p></>}</aside><section className={styles.conversationPanel}><div className={styles.panelTopline}><span className={styles.kicker}>{mode === 'guided' ? '2 / RUN CALL SCREEN' : 'LIVE BROWSER CALL'}</span><span className={styles.statusPillActive}>{mode === 'guided' ? 'Simulated test call' : statusLabel[session?.status] || 'Ready'}</span></div>{mode === 'guided' ? <><h2>{guidedMeta[1]}</h2><p className={styles.subtitle}>One simulated transcript from the final test set.</p><div className={styles.timeline} aria-live="polite">{reveal === 0 && <div className={styles.walkthroughEmpty}><span>◈</span><h3>Ready to screen.</h3><p>Call Screen will score the transcript and choose an action.</p></div>}{reveal >= 1 && <article className={styles.message + ' ' + styles.agentMessage}><span className={styles.avatar}>✦</span><div><small>AI AGENT</small><p>{greeting}</p></div></article>}{reveal >= 2 && <article className={styles.message + ' ' + styles.callerMessage}><span className={styles.avatar}>●</span><div><small>CALLER</small><p>{selected?.conversation?.[0]?.text || 'Loading the test transcript…'}</p></div></article>}</div><div className={styles.replayFooter}>{reveal < 3 ? <button className={styles.playButton} onClick={play} disabled={playing || !selected}>{playing ? 'Running Call Screen…' : 'Run Call Screen'} <span>→</span></button> : <><span className={styles.transcriptState}>● Screening complete</span><button className={styles.restartButton} onClick={play}>Replay</button></>}<span>Transcript → risk → action</span></div></> : <><h2>Your call, live</h2><p className={styles.subtitle}>{session?.status === 'ANALYZING' ? 'Our classifier is assessing the completed caller turn.' : session?.partial ? 'Transcribing your response…' : 'Use a microphone to speak with the screening agent.'}</p><div className={styles.timeline} aria-live="polite">{!session?.conversation?.length && !session?.partial && <div className={styles.walkthroughEmpty}><span>◈</span><h3>Ready for a live call.</h3><p>Your transcript and risk score will appear here as you speak.</p></div>}{session?.conversation?.map((message, index) => <article className={styles.message + ' ' + (message.role === 'caller' ? styles.callerMessage : styles.agentMessage)} key={index}><span className={styles.avatar}>{message.role === 'caller' ? '●' : '✦'}</span><div><small>{message.role === 'caller' ? 'CALLER' : 'AI AGENT'}</small><p>{message.text}</p></div></article>)}{session?.partial && <article className={styles.message + ' ' + styles.callerMessage + ' ' + styles.partial}><span className={styles.avatar}>●</span><div><small>CALLER · TRANSCRIBING</small><p>{session.partial}</p></div></article>}</div><div className={styles.liveCallControls}><label className={styles.consent}><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} /><span>I understand that test speech is sent to Twilio and the transcript classifier. I will use fictional details.</span></label><BrowserCall enabled={config?.browser_calling} consent={consent} start={startLive} active={!!active} />{error && <p role="alert" className={styles.error}>{error}</p>}</div></>}</section><aside className={styles.decisionPanel}><span className={styles.kicker}>{STATIC_DEMO ? '3 / CHECK THE RESULT' : 'SCREENING DECISION'}</span><h2>{STATIC_DEMO ? 'Did it get it right?' : 'What the system found'}</h2>{mode === 'guided' ? reveal === 3 ? <Decision assessment={selected?.assessment} caseRecord={selected} simulated={false} onNext={() => { window.location.href=BASE_PATH + '/lab#evidence'; }} /> : <Decision /> : latest ? <Decision assessment={latest} live history={session?.risk_history} onNext={() => { window.location.href=BASE_PATH + '/lab#evidence'; }} /> : <Decision />}{mode === 'live' && <Telemetry session={session} latest={latest} enabled={telemetryOn} onToggle={() => setTelemetryOn(value => !value)} />}</aside></section></>}
    {stage === 'evidence' && <section className={styles.storyPage} aria-label="Evaluation evidence"><span className={styles.kicker}>STEP 2 · CONTROLLED EVALUATION</span><h1>Check the decision against labelled cases.</h1><p className={styles.storyLead}>The guided call is one row in a locked set of simulated control cases. Each row has an expected decision before the system is scored.</p>{evaluationError && <p className={styles.error}>{evaluationError}</p>}{!heldOut && !evaluationError && <p className={styles.loadingEvidence}>Loading the controlled test set…</p>}{heldOut && <><section className={styles.evaluationPanel}><div><span className={styles.kicker}>{simulated ? 'SIMULATED CONTROL FIXTURE' : 'RECORDED PIPELINE RUN'}</span><h2>{heldOut.n + ' held-out control cases'}</h2><p>{simulated ? 'The app ships this fixture to demonstrate the evaluation flow. It is deliberately not presented as Gemini performance.' : 'These are recorded scores from the same pipeline used by the live Call Screen.'}</p></div><Matrix summary={heldOut} selected={results.find(row => row.id === selectedId)} /></section><section className={styles.errorReview}><div><span className={styles.kicker}>WHAT THE TEST SET CATCHES</span><h2>Two errors can point to one practical change.</h2><p>We review a harmful call that was not blocked and a helpful call that was stopped. That is more useful than a single accuracy number.</p></div>{missed && <article><small>HARMFUL CALL NOT BLOCKED</small><strong>{missed.id}</strong><p>{missed.conversation?.[0]?.text}</p><span>Expected {missed.expected_decision.replaceAll('_', ' ')} · observed {missed.assessment.decision.replaceAll('_', ' ')}</span></article>}{falseBlock && <article><small>HELPFUL CALL BLOCKED</small><strong>{falseBlock.id}</strong><p>{falseBlock.conversation?.[0]?.text}</p><span>Expected {falseBlock.expected_decision.replaceAll('_', ' ')} · observed {falseBlock.assessment.decision.replaceAll('_', ' ')}</span></article>}</section><button className={styles.nextButton} onClick={() => go('recommendation')}>See what we would test next <span>→</span></button></>}</section>}
    {stage === 'recommendation' && <section className={styles.storyPage} aria-label="Recommendation and validation plan"><span className={styles.kicker}>STEP 3 · NEXT TEST</span><h1>Improve what the errors have in common.</h1><p className={styles.storyLead}>The missed harmful call requests a concrete action. The false block only talks about a scam. The policy needs to understand that difference.</p><section className={styles.recommendationPanel}><div><span className={styles.kicker}>CHANGE ONE THING</span><h2>Classify what the caller wants the recipient to do.</h2><p>Make a direct request for a code, remote access, or money transfer a strong safety signal. Do not treat a warning about those requests the same way.</p></div><div><span className={styles.kicker}>TEST IT SAFELY</span><h2>Keep the current policy as the holdout.</h2><p>First score the candidate offline. Then run it in shadow mode on real calls. Only then test it on unclear, non-high-risk calls.</p></div></section><section className={styles.validationPanel}><span className={styles.kicker}>DECISION SCORECARD</span><h2>Release only when protection improves without damaging calling.</h2><div className={styles.measureList}><article><strong>Primary</strong><span>Fewer harmful calls connected</span></article><article><strong>Guardrail</strong><span>No increase in helpful calls blocked</span></article><article><strong>Experience</strong><span>p95 wait time and call abandonment stay within target</span></article></div><div className={styles.abortRule}><strong>Abort criterion</strong><span>Stop the canary if recall falls below 95% on reviewed harmful calls.</span></div></section><button className={styles.backButton} onClick={() => go('demo')}>Run another case</button></section>}
    <footer className={styles.footer}>{STATIC_DEMO ? 'Guided calls come from the final simulated test set' : 'Live browser calls are operational traces · controlled cases are the only data used for model evaluation'}</footer>
  </main>;
}
