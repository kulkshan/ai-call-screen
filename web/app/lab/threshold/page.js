'use client';

import {useEffect,useState} from 'react';
import LabNav from '../LabNav';
import styles from './page.module.css';

const API=process.env.NEXT_PUBLIC_API_URL||'http://127.0.0.1:8002';
const pct=value=>`${(value*100).toFixed(1)}%`;

function Metric({label,value,note}){
  return <article><span>{label}</span><strong>{value}</strong><small>{note}</small></article>
}

export default function ThresholdLab(){
  const [cost,setCost]=useState(50);
  const [data,setData]=useState(null);
  const [error,setError]=useState('');

  useEffect(()=>{
    let active=true;
    const timer=setTimeout(()=>{
      fetch(`${API}/api/lab/threshold-preview?false_positive_cost=${cost}`)
        .then(response=>{if(!response.ok)throw Error('Threshold preview unavailable.');return response.json()})
        .then(result=>{if(active){setData(result);setError('')}})
        .catch(reason=>{if(active)setError(reason.message)});
    },120);
    return()=>{active=false;clearTimeout(timer)};
  },[cost]);

  return <main className={styles.page}>
    <LabNav active="threshold" />

    <header className={styles.hero}>
      <div><span>DECISION TRADE-OFF</span><h1>How cautious should Call Screen be?</h1></div>
      <p>A lower cutoff catches more scams but may interrupt more legitimate callers. This page uses the same 160 labelled test calls to show that trade-off.</p>
    </header>

    <section className={styles.dataNote}><div><span>DATA USED</span><strong>80 scam + 80 legitimate test calls</strong></div><div><span>WHAT CHANGES</span><strong>The action cutoff</strong></div><div><span>WHAT WE COMPARE</span><strong>Scams caught vs. legitimate calls flagged</strong></div></section>

    <section className={styles.control}>
      <div className={styles.sliderCopy}>
        <span>COST OF A FALSE ALARM</span>
        <strong>{cost}<small>× a missed scam</small></strong>
        <p>Move the slider to require more or less evidence before the system warns or blocks.</p>
      </div>
      <div className={styles.slider}>
        <input aria-label="False-block cost" type="range" min="1" max="200" value={cost} onChange={event=>setCost(Number(event.target.value))}/>
        <div><span>1×</span><span>50× default</span><span>200×</span></div>
      </div>
    </section>

    {error&&<section className={styles.error}>{error}</section>}
    {data&&<>
      <section className={styles.metrics}>
        <Metric label="Precision" value={pct(data.metrics.precision)} note="Of calls flagged, how many were scams"/>
        <Metric label="Recall" value={pct(data.metrics.recall)} note="Of scams, how many were caught"/>
        <Metric label="False blocks" value={pct(data.metrics.false_positive_rate)} note={`${data.metrics.confusion_matrix.false_positive} legitimate call(s)`}/>
        <Metric label="Missed scams" value={pct(data.metrics.false_negative_rate)} note={`${data.metrics.confusion_matrix.false_negative} scam call(s)`}/>
      </section>

      <section className={styles.boundaries}>
        <header><div><span>RESULTING ACTIONS</span><h2>The call decision changes with the trade-off.</h2></div><p>The cutoffs are calculated from the error cost above and then measured on the same test calls.</p></header>
        <div className={styles.scale}>
          <div className={styles.labels}><span>0%</span><span>Risk score</span><span>100%</span></div>
          <div className={styles.track}>
            <i className={styles.allow} style={{width:pct(data.thresholds.monitor)}}/>
            <i className={styles.monitor} style={{left:pct(data.thresholds.monitor),width:pct(data.thresholds.warn-data.thresholds.monitor)}}/>
            <i className={styles.warn} style={{left:pct(data.thresholds.warn),width:pct(data.thresholds.block-data.thresholds.warn)}}/>
            <i className={styles.block} style={{left:pct(data.thresholds.block),width:pct(1-data.thresholds.block)}}/>
          </div>
          <div className={styles.marker} style={{left:pct(data.thresholds.monitor)}}><b>{pct(data.thresholds.monitor)}</b><span>Monitor</span></div>
          <div className={styles.marker} style={{left:pct(data.thresholds.warn)}}><b>{pct(data.thresholds.warn)}</b><span>Warn</span></div>
          <div className={styles.marker} style={{left:pct(data.thresholds.block)}}><b>{pct(data.thresholds.block)}</b><span>Block</span></div>
        </div>
        <div className={styles.tiers}>
          <article><b>ALLOW</b><p>No interruption below {pct(data.thresholds.monitor)}.</p></article>
          <article><b>MONITOR</b><p>Keep screening until {pct(data.thresholds.warn)}.</p></article>
          <article><b>WARN</b><p>Show evidence from {pct(data.thresholds.warn)}.</p></article>
          <article><b>BLOCK</b><p>Stop the call above {pct(data.thresholds.block)}.</p></article>
        </div>
      </section>

      <section className={styles.interpretation}>
        <span>WHAT CHANGED</span>
        <h2>{cost>50?'Fewer false blocks, with more scams allowed through.':cost<50?'More scams caught, with a greater risk of blocking legitimate callers.':'The default policy heavily protects legitimate calls.'}</h2>
        <p>The final test set now contains <b>{data.metrics.confusion_matrix.false_positive}</b> legitimate call(s) flagged and <b>{data.metrics.confusion_matrix.false_negative}</b> missed scam(s) at this cutoff.</p>
      </section>
    </>}
  </main>
}
