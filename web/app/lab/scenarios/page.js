'use client';

import {useEffect, useMemo, useState} from 'react';
import LabNav from '../LabNav';
import styles from './page.module.css';

const API=process.env.NEXT_PUBLIC_API_URL||'http://127.0.0.1:8002';
const pct=value=>`${(value*100).toFixed(1)}%`;
const label=value=>value.replaceAll('_',' ');

function isError(call){
  const predictedScam=call.probability>=.5;
  return (call.label==='scam'&&!predictedScam)||(call.label==='legit'&&predictedScam);
}

const modelLabel=call=>call.probability>=.5?'SCAM':'SAFE';

function RiskChart({turns}){
  const width=520;
  const height=190;
  const left=32;
  const top=20;
  const usableWidth=width-left-18;
  const usableHeight=height-top-30;
  const point=(turn,index)=>({
    x:left+(turns.length===1?usableWidth/2:(index/(turns.length-1))*usableWidth),
    y:top+(1-turn.probability)*usableHeight
  });
  const points=turns.map(point);
  return <svg className={styles.chart} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Risk score by call turn">
    <path className={styles.axis} d={`M${left} ${top}V${height-30}H${width-18}`}/>
    {[.25,.5,.75,1].map(value=><g key={value}><path className={styles.grid} d={`M${left} ${top+(1-value)*usableHeight}H${width-18}`}/><text x="1" y={top+(1-value)*usableHeight+4}>{Math.round(value*100)}%</text></g>)}
    <polyline points={points.map(p=>`${p.x},${p.y}`).join(' ')}/>
    {points.map((p,index)=><g key={index}><circle cx={p.x} cy={p.y} r="5"/><text className={styles.turnLabel} x={p.x-10} y={height-10}>T{index+1}</text></g>)}
  </svg>
}

function ScenarioDetail({call}){
  const activeSignals=call.turns.flatMap(turn=>turn.signals.signals.filter(signal=>signal.present).map(signal=>({...signal,turn:turn.turn_index})));
  return <section className={styles.detail}>
    <header>
      <div><span>SELECTED SCENARIO</span><h2>{label(call.subtype)}</h2></div>
      <div className={styles.outcome}><span>Expected <b>{call.label==='scam'?'SCAM':call.label==='legit'?'LEGITIMATE':'ASK FOR MORE'}</b></span><span>Classifier <b>{modelLabel(call)}</b></span><span>Call action <b>{call.tier}</b></span></div>
    </header>

    <div className={styles.detailGrid}>
      <article className={styles.transcript}>
        <div className={styles.panelTitle}><h3>Transcript</h3><span>{call.turns.length} turns</span></div>
        {call.turns.map(turn=><div className={styles.turn} key={turn.turn_index}>
          <small>CALLER · TURN {turn.turn_index}</small>
          <p>{turn.text}</p>
          <div><b>{pct(turn.probability)} risk</b><em>{turn.tier}</em></div>
        </div>)}
      </article>

      <aside className={styles.analysis}>
        <div className={styles.panelTitle}><h3>Risk progression</h3><span>{call.difficulty}</span></div>
        <RiskChart turns={call.turns}/>
        <h3>Detected evidence</h3>
        <ul>{activeSignals.length?activeSignals.map((signal,index)=><li key={`${signal.turn}-${signal.type}-${index}`}><span><b>T{signal.turn}</b> {label(signal.type)}</span><em>{signal.confidence.toFixed(2)}</em><small>“{signal.evidence}”</small></li>):<li className={styles.empty}>No positive transcript signals.</li>}</ul>
      </aside>
    </div>

    <div className={styles.metadata}>
      <span>Reputation risk <b>{pct(call.metadata.reputation_risk)}</b></span>
      <span>Frequency anomaly <b>{pct(call.metadata.frequency_anomaly)}</b></span>
      <span>Neighbour spoof <b>{call.metadata.neighbor_spoof?'Yes':'No'}</b></span>
      <span>Known contact <b>{call.metadata.is_contact?'Yes':'No'}</b></span>
    </div>
  </section>
}

export default function Scenarios(){
  const [report,setReport]=useState(null);
  const [labelFilter,setLabelFilter]=useState('all');
  const [difficulty,setDifficulty]=useState('all');
  const [errorOnly,setErrorOnly]=useState(false);
  const [selectedId,setSelectedId]=useState(null);

  useEffect(()=>{fetch(API+'/api/lab/report').then(response=>{if(!response.ok)throw Error('Evaluation report unavailable.');return response.json()}).then(setReport).catch(error=>setReport({error:error.message}))},[]);

  const filtered=useMemo(()=>{
    if(!report||report.error)return[];
    return report.calls.filter(call=>(labelFilter==='all'||call.label===labelFilter)&&(difficulty==='all'||call.difficulty===difficulty)&&(!errorOnly||isError(call)));
  },[report,labelFilter,difficulty,errorOnly]);

  const selected=useMemo(()=>{
    if(!filtered.length)return null;
    return filtered.find(call=>call.scenario_id===selectedId)||filtered[0];
  },[filtered,selectedId]);

  if(!report)return <main className={styles.loading}>Loading scenarios…</main>;
  if(report.error)return <main className={styles.loading}>Evaluation report unavailable.</main>;

  return <main className={styles.page}>
    <LabNav active="scenarios" />

    <header className={styles.hero}>
      <span>TEST CALL REVIEW</span>
      <h1>See the calls behind every metric.</h1>
      <p>These are the {report.corpus.test_scenarios.toLocaleString()} final simulated test calls. The classifier received only each transcript. The expected label was used afterward to decide whether the prediction was right.</p>
    </header>

    <section className={styles.dataNote}>
      <div><span>DATA SHOWN</span><strong>{report.corpus.test_scenarios.toLocaleString()} final test calls</strong></div>
      <div><span>USED TO CALCULATE</span><strong>Precision, recall, false alarms</strong></div>
      <div><span>NOT USED FOR</span><strong>Training or tuning</strong></div>
    </section>

    <section className={styles.browser}>
      <div className={styles.filters}>
        <label>Call label<select value={labelFilter} onChange={event=>{setLabelFilter(event.target.value);setSelectedId(null)}}><option value="all">All calls</option><option value="scam">Scam</option><option value="legit">Legitimate</option><option value="unclear">Unclear</option></select></label>
        <label>Test set<select value={difficulty} onChange={event=>{setDifficulty(event.target.value);setSelectedId(null)}}><option value="all">All final test calls</option><option value="controlled">Simulated calls</option></select></label>
        <label className={styles.check}><input type="checkbox" checked={errorOnly} onChange={event=>{setErrorOnly(event.target.checked);setSelectedId(null)}}/> Mistakes only</label>
        <strong>Showing {Math.min(filtered.length,60)} of {filtered.length} calls</strong>
      </div>

      <div className={styles.callList}>
        <div className={styles.listHeader}><span>Call type</span><span>Expected</span><span>Risk score</span><span>Classifier</span><span>Call action</span></div>
        <div className={styles.rows}>{filtered.slice(0,60).map(call=><button className={call.scenario_id===selected?.scenario_id?styles.selected:''} onClick={()=>setSelectedId(call.scenario_id)} key={call.scenario_id}><span>{label(call.subtype)}{isError(call)&&<em>Review</em>}</span><span>{call.label}</span><span>{pct(call.probability)}</span><span>{modelLabel(call)}</span><span>{call.tier}</span></button>)}</div>
      </div>
    </section>

    {selected?<ScenarioDetail call={selected}/>:<section className={styles.noResults}>No scenarios match these filters.</section>}
  </main>
}
