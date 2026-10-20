'use client';

import Link from 'next/link';
import {useEffect, useMemo, useState} from 'react';
import LabNav from './LabNav';
import staticReport from '../data/public-report.json';
import styles from './page.module.css';

const API=process.env.NEXT_PUBLIC_API_URL||'http://127.0.0.1:8002';
const STATIC_DEMO=process.env.NEXT_PUBLIC_STATIC_DEMO==='1';
const pct=value=>value===null||value===undefined?'—':`${(value*100).toFixed(1)}%`;
const title=value=>value.replaceAll('_',' ');
const screenReplies=['Who am I speaking with, and what is this call about?','What do you need the person you called to do?'];

function ReportNumber({label,value,note}) {
  return <div className={styles.reportNumber}><span>{label}</span><strong>{value}</strong>{note&&<small>{note}</small>}</div>
}

function Matrix({matrix}) {
  return <div className={styles.matrix} aria-label="Confusion matrix">
    <span />
    <span className={styles.matrixHeader}>Predicted safe</span>
    <span className={styles.matrixHeader}>Predicted scam</span>
    <span className={styles.matrixRow}>Actual safe</span>
    <strong className={styles.correctPass}><b>{matrix.true_negative}</b><small>correct pass</small></strong>
    <strong className={styles.falseAlarm}><b>{matrix.false_positive}</b><small>false alarm</small></strong>
    <span className={styles.matrixRow}>Actual scam</span>
    <strong className={styles.missed}><b>{matrix.false_negative}</b><small>missed scam</small></strong>
    <strong className={styles.correctCatch}><b>{matrix.true_positive}</b><small>correct catch</small></strong>
  </div>
}

function Curve({points,precision,recall}) {
  const usable=points.filter(point=>point.precision!==null&&point.recall!==null);
  const left=48,top=20,width=402,height=190;
  const polyline=usable.map(point=>`${left+point.recall*width},${top+(1-point.precision)*height}`).join(' ');
  const chosen={x:left+recall*width,y:top+(1-precision)*height};
  return <svg className={styles.curve} viewBox="0 0 480 250" role="img" aria-label="Precision recall curve">
    <path d={`M${left} ${top}V${top+height}H${left+width}`}/>
    <path d={`M${left} ${top+height*.25}H${left+width}M${left} ${top+height*.5}H${left+width}M${left} ${top+height*.75}H${left+width}M${left+width*.25} ${top}V${top+height}M${left+width*.5} ${top}V${top+height}M${left+width*.75} ${top}V${top+height}`} className={styles.grid}/>
    <polyline points={polyline}/>
    <circle cx={chosen.x} cy={chosen.y} r="6"/>
    <text x="10" y={top+4}>1.00</text><text x="18" y={top+height*.5+4}>0.50</text><text x="29" y={top+height+4}>0</text><text transform="rotate(-90 7 135)" x="7" y="135">PRECISION</text>
    <text x={left-3} y="232">0</text><text x={left+width*.5-12} y="232">0.50</text><text x={left+width-18} y="232">1.00</text><text x="228" y="248">RECALL</text>
  </svg>
}

function RiskWalkthrough({report}) {
  const sample=useMemo(()=>report.calls.find(call=>call.subtype==='bank_impersonation'&&call.label==='scam')||report.calls.find(call=>call.label==='scam'),[report]);
  const [turn,setTurn]=useState(0);
  if(!sample)return null;
  const visible=sample.turns.slice(0,turn+1);
  const current=visible.at(-1);
  const signals=current.signals.signals.filter(signal=>signal.present);
  return <section className={styles.walkthrough} id="walkthrough">
    <div className={styles.sectionIntro}><span>01 / Try one call</span><h2>Watch the risk change as the caller speaks.</h2><p>This shows how one call is screened. The larger test below shows whether the classifier works consistently.</p></div>
    <div className={styles.screenFrame}>
      <div className={styles.transcriptPanel}>
        <header><strong>Incoming · Unknown caller</strong><span>TURN&nbsp;&nbsp;{turn+1} / {sample.turns.length}</span></header>
        <div className={styles.dialogue}>{visible.map((item,index)=><div className={styles.turnPair} key={item.turn_index}>
          <div className={styles.callerBubble}><small>CALLER&nbsp;&nbsp;·&nbsp;&nbsp;00:{String(3+index*9).padStart(2,'0')}</small><p>{item.text}</p>{item.signals.signals.filter(signal=>signal.present).map(signal=><em key={signal.type}>{title(signal.type)}</em>)}</div>
          {index<visible.length-1&&<div className={styles.screenBubble}><small>CALL SCREEN&nbsp;&nbsp;·&nbsp;&nbsp;00:{String(8+index*9).padStart(2,'0')}</small><p>{screenReplies[index]||'Can you explain the reason for your call?'}</p></div>}
        </div>)}</div>
      </div>
      <aside className={styles.decisionRail}>
        <span>P(SCAM) · CURRENT TURN</span><strong>{pct(current.probability)}</strong><b>{current.tier}</b>
        <div className={styles.riskBar}><i style={{width:pct(current.probability)}}/></div>
        <ul>{signals.map(signal=><li key={signal.type}><span>{title(signal.type)}</span><em>{signal.confidence.toFixed(2)}</em></li>)}{signals.length===0&&<li><span>No strong content signal</span><em>—</em></li>}</ul>
        <div className={styles.railControls}><button onClick={()=>setTurn(Math.max(0,turn-1))} disabled={turn===0}>Ⅱ</button><div>{sample.turns.map((_,index)=><i className={index===turn?styles.selectedDot:''} key={index}/>)}</div><button onClick={()=>setTurn(Math.min(sample.turns.length-1,turn+1))} disabled={turn===sample.turns.length-1}>→</button></div>
      </aside>
    </div>
    <Link className={styles.liveLink} href={STATIC_DEMO?'/':'/?mode=live'}>{STATIC_DEMO?'Run another guided call ↗':'Try the same pipeline with your voice ↗'}</Link>
  </section>
}

function System() {
  return <section className={styles.system} id="system">
    <div className={styles.sectionIntro}><span>02 / Test across 10,000 calls</span><h2>How the data was used.</h2><p>Training and final testing use different calls. The classifier never sees the correct answers for the final test calls.</p></div>
    <div className={styles.pipeline}><article><b>6,000 CALLS</b><h3>Train</h3><p>The classifier learns the difference between scam and legitimate language.</p></article><article><b>2,000 CALLS</b><h3>Tune</h3><p>A separate set adjusts how model scores map to probability.</p></article><article><b>2,000 CALLS</b><h3>Final test</h3><p>These calls are used only after training and tuning are complete.</p></article></div>
    <div className={styles.testBreakdown}><strong>Calls used for the final evaluation</strong><div><span><b>800</b> scams</span><span><b>800</b> legitimate</span><span><b>400</b> unclear</span></div><p>Precision and recall use the 1,600 calls with a clear scam or legitimate label. The 400 unclear calls test whether the system asks for more information.</p></div>
  </section>
}

function Evidence({report}) {
  const metrics=report.metrics;
  const matrix=metrics.confusion_matrix;
  const before=report.baseline_comparison?.before;
  const beforeMatrix=before?.confusion_matrix;
  const unclearCount=report.unclear_call_evaluation?.count||report.calls.filter(call=>call.label==='unclear').length;
  const unclearCorrect=report.unclear_call_evaluation?.after_evidence_gate??report.calls.filter(call=>call.label==='unclear'&&call.tier==='MONITOR').length;
  const unclearRate=report.unclear_call_evaluation?.after_rate??(unclearCount?unclearCorrect/unclearCount:0);
  const unclearBefore=report.unclear_call_evaluation?.before_evidence_gate;
  const unclearBeforeRate=report.unclear_call_evaluation?.before_rate;
  const missedScam=report.calls.find(call=>call.label==='scam'&&call.probability<.5);
  const falseAlarm=report.calls.find(call=>call.label==='legit'&&call.probability>=.5);
  const improvedExample=report.calls.find(call=>call.baseline_probability>=.5&&call.probability<.5);
  const transcript=call=>call?.turns.map(turn=>turn.text).join(' ');
  const legitimate=report.per_archetype.filter(row=>row.label==='legit');
  const hardest=legitimate.reduce((highest,row)=>(row.false_positive_rate||0)>(highest.false_positive_rate||0)?row:highest,legitimate[0]);
  return <section className={styles.evidence} id="evidence">
    <div className={styles.sectionIntro}><span>Final test results</span><h2>More training data improved both goals.</h2><p>The new classifier caught {matrix.true_positive} of {matrix.true_positive+matrix.false_negative} scams and incorrectly flagged {matrix.false_positive} of {matrix.true_negative+matrix.false_positive} legitimate calls.</p></div>
    <div className={styles.metricBasis}><strong>Where these numbers come from</strong><p>Precision and recall use the 1,600 final test calls with a clear answer: 800 scams and 800 legitimate calls. The remaining 400 unclear calls test whether the system continues screening.</p></div>
    {before&&<div className={styles.finding}><strong>Same test calls, before → after</strong><div><p>Precision rose from {pct(before.precision)} to {pct(metrics.precision)}. Recall rose from {pct(before.recall)} to {pct(metrics.recall)}. False alarms fell from {pct(before.false_positive_rate)} to {pct(metrics.false_positive_rate)}.</p>{improvedExample&&<blockquote>“{transcript(improvedExample)}”<small>Previous risk {pct(improvedExample.baseline_probability)} · New risk {pct(improvedExample.probability)} · Correctly changed to safe</small></blockquote>}</div></div>}
    <div className={styles.evidenceGrid}>
      <article className={styles.matrixPanel}><Matrix matrix={metrics.confusion_matrix}/><p><b>Recall {pct(metrics.recall)}</b>: of all scams, how many were caught. <b>Precision {pct(metrics.precision)}</b>: of all calls flagged, how many were actually scams.</p></article>
      <article className={styles.slicesPanel}><header><h3>False-block rate by call subtype</h3><small>LOWER IS BETTER</small></header><div className={styles.sliceList}>{legitimate.map(row=>{const width=Math.max(4,(row.false_positive_rate||0)*100);return <div key={row.subtype}><span>{title(row.subtype)}</span><b><i className={row.subtype===hardest?.subtype?styles.criticalBar:''} style={{width:`${width}%`}}/></b><em>{pct(row.false_positive_rate)}</em></div>})}</div>{hardest&&<p>This is the decision-critical slice in this evaluation: it is where the current system makes the most false-block mistakes.</p>}</article>
    </div>
    <div className={styles.unclearResult}><span>UNCLEAR CALLS</span><strong>{unclearBefore ?? '—'} of {unclearCount} before → {unclearCorrect} of {unclearCount} after</strong><p>A separate evidence check now keeps intentionally vague calls in screening until the caller gives a concrete purpose or request. That changed the simulated test result from {pct(unclearBeforeRate)} to {pct(unclearRate)}.</p></div>
    <div className={styles.mistakes}><header><span>Two remaining errors</span><h3>What the classifier still misunderstands.</h3></header><div>
      {missedScam&&<article><b>MISSED SCAM · {pct(missedScam.probability)} RISK</b><blockquote>“{transcript(missedScam)}”</blockquote><p>The request for a temporary code was phrased without the usual words “OTP” or “verification code.”</p></article>}
      {falseAlarm&&<article><b>FALSE ALARM · {pct(falseAlarm.probability)} RISK</b><blockquote>“{transcript(falseAlarm)}”</blockquote><p>The caller warned against sharing payment details, but the classifier treated the warning as a request.</p></article>}
    </div></div>
  </section>
}

function Recommendation({report}) {
  return <section className={styles.recommendation} id="recommendation">
    <div className={styles.sectionIntro}><span>03 / What comes next</span><h2>Check whether the improvement holds on real language.</h2><p>The simulated test supports the model change. Human-reviewed call transcripts are still required before any product rollout.</p></div>
    <div className={styles.recommendationGrid}>
      <article><b>WHAT CHANGED</b><h3>10× more simulated calls</h3><p>The training data now includes more difficult legitimate calls, paraphrased scams, and unclear callers.</p></article>
      <article><b>WHAT IMPROVED</b><h3>Fewer false alarms</h3><p>The false-positive rate fell while scam recall increased on the same final test set.</p></article>
      <article><b>POLICY FIX</b><h3>Ask when evidence is missing</h3><p>A high or low model score can no longer end a vague call. The caller must first give a concrete purpose or request.</p></article>
    </div>
    <div className={styles.rollout}><strong>How it would move beyond this prototype</strong><ol><li>Repeat the test on independently reviewed transcripts.</li><li>Run in shadow mode without changing call outcomes.</li><li>Compare with a holdout in a small canary rollout.</li><li>Expand only if false alarms, scam recall, and latency all hold.</li></ol><small>Proposed plan. No live experiment result is claimed.</small></div>
  </section>
}

function TechnicalDetails({report}) {
  const metrics=report.metrics;
  return <section className={styles.technical} id="technical">
    <details><summary><span>04 / Technical details</span><strong>Open model evaluation details</strong></summary>
      <div className={styles.technicalBody}>
      <article className={styles.curvePanel}><header><h3>Precision–recall curve</h3><small>FINAL SIMULATED TEST · N={metrics.count}</small></header><div><Curve points={report.pr_curve.points} precision={metrics.precision} recall={metrics.recall}/><aside><strong>{(metrics.precision*100).toFixed(1)} / {(metrics.recall*100).toFixed(1)}</strong><p>Each point changes the classification cutoff. Moving right catches more scams; moving down creates more false alarms.</p><p>The green point is the 50% cutoff.</p><small>AVERAGE PRECISION · {report.pr_curve.average_precision?.toFixed(3)}</small></aside></div></article>
        <ul><li><b>Model:</b> transcript embeddings with a trained and calibrated classification head.</li><li><b>Input:</b> raw transcript text only. Expected labels never enter inference.</li><li><b>Data:</b> fictional generated calls, not production traffic.</li><li><b>Limit:</b> these results cannot estimate real-world Google Call Screen performance.</li></ul>
      </div>
    </details>
  </section>
}

function Policy({report}) {
  const [cost,setCost]=useState(50);const [preview,setPreview]=useState(null);
  useEffect(()=>{let live=true;const timeout=setTimeout(()=>fetch(`${API}/api/lab/threshold-preview?false_positive_cost=${cost}`).then(response=>response.ok?response.json():null).then(data=>live&&setPreview(data)).catch(()=>live&&setPreview(null)),160);return()=>{live=false;clearTimeout(timeout)}},[cost]);
  const data=preview||{thresholds:report.derived_thresholds};
  return <section className={styles.policy} id="policy"><div className={styles.sectionIntro}><span>04 / Policy</span><h2>The threshold is a product decision.</h2><p>Raise the cost of blocking a legitimate caller. The system requires stronger evidence before it interrupts the call.</p></div><div className={styles.policyGrid}><div className={styles.sliderBlock}><strong>{cost}<small>× costlier</small></strong><p>A false block costs <b>{cost}×</b> a missed scam in this policy.</p><label htmlFor="cost">FALSE-BLOCK / MISSED-SCAM COST</label><input id="cost" type="range" min="1" max="200" value={cost} onChange={event=>setCost(Number(event.target.value))}/><div><span>1×</span><span>200×</span></div></div><table><thead><tr><th>Decision</th><th>From risk</th><th>Meaning</th></tr></thead><tbody><tr><td>Allow</td><td>0–{pct(data.thresholds.monitor)}</td><td>No interruption</td></tr><tr><td>Monitor</td><td>{pct(data.thresholds.monitor)}–{pct(data.thresholds.warn)}</td><td>Keep screening</td></tr><tr><td>Warn</td><td>{pct(data.thresholds.warn)}–{pct(data.thresholds.block)}</td><td>Show evidence</td></tr><tr><td>Block</td><td>{pct(data.thresholds.block)}–100%</td><td>Stop the call</td></tr></tbody></table></div><p className={styles.formula}>Expected cost = (1 − risk) × cost of a false block + risk × cost of a missed scam</p></section>
}

function Limits({report}) {
  return <section className={styles.limits} id="limits"><div className={styles.sectionIntro}><span>05 / Limits</span><h2>What this prototype does not prove.</h2><p>The gaps are part of the evaluation plan, not small print.</p></div><ol><li><b>01</b><div><strong>Simulated call set</strong><p>The 10,000 fictional calls test the pipeline. They do not estimate performance on real callers.</p></div></li><li><b>02</b><div><strong>Authored labels</strong><p>Scenario labels were assigned during generation, not reviewed by independent human raters.</p></div></li><li><b>03</b><div><strong>Limited final test</strong><p>The headline precision and recall use {report.corpus.binary_test_scenarios} labelled test calls, so the results remain uncertain.</p></div></li><li><b>04</b><div><strong>No live reputation feed</strong><p>The live demo marks caller reputation unavailable rather than inventing it.</p></div></li></ol></section>
}

export default function Lab() {
  const [report,setReport]=useState(staticReport);
  useEffect(()=>{if(STATIC_DEMO)return;fetch(API+'/api/lab/report').then(response=>response.ok?response.json():Promise.reject()).then(setReport).catch(()=>{})},[]);
  if(!report)return <main className={styles.loading}>Loading Call Screen Lab…</main>;
  if(report.error)return <main className={styles.error}><h1>Evaluation report unavailable.</h1><p>{report.error}</p></main>;
  return <main className={styles.page}>
    <LabNav active="overview" />
    <header className={styles.hero}><div><span className={styles.kicker}>PRODUCT DATA SCIENCE CASE STUDY</span><h1>Can Call Screen catch scams<br/><em>without blocking real callers?</em></h1><p>I trained the classifier on 10,000 simulated calls and measured whether more varied data catches more scams without creating more false alarms.</p><div className={styles.heroActions}><a className={styles.darkButton} href="#walkthrough">Start with one call ↓</a><a className={styles.outlineButton} href="#system">See how 10,000 calls were used</a></div></div><aside><span>THE DATASET · 10,000 SIMULATED CALLS</span><p className={styles.resultBasis}>Every call has a transcript and an expected outcome. No live calls are included in these results.</p><ReportNumber label="Used to train" value="6,000" note="Model learning"/><ReportNumber label="Used to tune" value="2,000" note="Probability calibration"/><ReportNumber label="Used for the final test" value="2,000" note="800 scam · 800 legitimate · 400 unclear"/><small>The final 2,000 calls are kept separate until training and tuning are complete.</small></aside></header>
    <RiskWalkthrough report={report}/><System/><Evidence report={report}/><Recommendation report={report}/><TechnicalDetails report={report}/>
    <footer><span>Call Screen Lab</span><span>Next.js · FastAPI · Twilio · Our classifier</span><span>Simulated benchmark · clearly labeled</span></footer>
  </main>
}
