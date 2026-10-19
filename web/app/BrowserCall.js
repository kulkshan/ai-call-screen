'use client';
import {useEffect,useRef,useState} from 'react';
const API=process.env.NEXT_PUBLIC_API_URL||'http://127.0.0.1:8002';
export default function BrowserCall({enabled,consent,start,active}){
 const device=useRef(null),call=useRef(null),generation=useRef(0),locked=useRef(false);
 const [phase,setPhase]=useState('idle'),[error,setError]=useState(''),[muted,setMuted]=useState(false);
 function release(){call.current?.disconnect();call.current=null;device.current?.destroy();device.current=null;locked.current=false;}
 useEffect(()=>()=>{generation.current++;release()},[]);
 function end(){generation.current++;release();setPhase('ended');setMuted(false)}
 async function begin(){
  if(locked.current)return;locked.current=true;
  const run=++generation.current;setError('');setPhase('connecting');setMuted(false);
  try{
   if(!window.isSecureContext||!navigator.mediaDevices)throw Error('Open this demo on HTTPS or localhost to use your microphone.');
   // Ask only after the visitor deliberately starts the call; release the permission-check stream.
   const stream=await navigator.mediaDevices.getUserMedia({audio:true});stream.getTracks().forEach(t=>t.stop());
   if(run!==generation.current)return;
   const auth=await start();if(!auth)throw Error('Could not start a session. Please try again.');
   if(run!==generation.current)return;
   const response=await fetch(API+'/api/sessions/'+auth.id+'/voice-token',{method:'POST',headers:{Authorization:'Bearer '+auth.token}});
   const data=await response.json();if(!response.ok)throw Error(data.detail||'Browser calling is unavailable.');
   const {Device}=await import('@twilio/voice-sdk');
   if(run!==generation.current)return;
   const d=new Device(data.token);device.current=d;
   const failed=()=>{if(run!==generation.current)return;generation.current++;release();setPhase('ended');setError('The audio connection failed. Check your microphone and network, then try again.');};
   d.on('error',failed);
   const c=await d.connect();
   if(run!==generation.current){c.disconnect();return;}call.current=c;
   const finished=()=>{if(run!==generation.current)return;generation.current++;release();setPhase('ended');setMuted(false)};
   c.on('accept',()=>setPhase('connected'));c.on('disconnect',finished);c.on('cancel',finished);c.on('reject',finished);c.on('error',failed);
   if(c.status()==='open')setPhase('connected');
  }catch(e){if(run!==generation.current)return;generation.current++;release();setPhase('ended');setError(e.name==='NotAllowedError'?'Microphone permission was denied. Allow it in your browser to talk to the agent.':e.message||'Unable to start the call.');}
 }
 const ongoing=phase==='connecting'||phase==='connected';
 return <div><button className="primary" onClick={begin} disabled={!enabled||!consent||ongoing||active}>{phase==='connecting'?'Connecting…':'Talk to the screening agent'}</button><p className="muted">Use your microphone and speakers. No phone or session code needed.</p>{!enabled&&<p className="note">Browser calling is awaiting Twilio configuration.</p>}<p role="status">{phase==='connected'?'● Call connected — speak naturally':phase==='connecting'?'Allow microphone access when prompted.':phase==='ended'?'Call ended. Your screening results stay on this page.':''}</p>{ongoing&&<div className="metrics"><button onClick={()=>{const value=!muted;call.current?.mute(value);setMuted(value)}} disabled={phase!=='connected'}>{muted?'Unmute':'Mute'}</button><button onClick={end}>End call</button></div>}{error&&<p className="error" role="alert">{error}</p>}</div>;
}
