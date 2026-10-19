const examples = {
 gift: {label:'Gift-card scenario', text:'This is the tax department. You need to buy $500 in gift cards immediately and read me the codes. If you don’t pay today, you will be arrested.'},
 bank: {label:'Bank impersonation scenario',text:'Hello, this is your bank’s fraud team. We need to secure your account immediately. Please read out the one-time verification code we just sent to your phone.'},
 legit: {label:'Appointment reminder scenario',text:'Hi, this is the dental office calling to remind you about your appointment tomorrow at 10 a.m. If you need to reschedule, please call our usual office number. Have a lovely day.'},
 custom: {label:'Your transcript',text:''}
};
const input=document.querySelector('#transcript'), button=document.querySelector('#analyze'), result=document.querySelector('#result');
let selected='gift', busy=false;
function count(){document.querySelector('#count').textContent=`${input.value.length.toLocaleString()} / 12,000`;button.disabled=busy||!input.value.trim();}
const initial=result.innerHTML;
function clearResult(){result.innerHTML=initial;document.querySelector('#result-tag').textContent='Awaiting analysis';}
function select(key){selected=key;input.value=examples[key].text;document.querySelector('#scenario-label').textContent=examples[key].label;document.querySelectorAll('.scenario').forEach(b=>{const active=b.dataset.scenario===key;b.classList.toggle('active',active);b.setAttribute('aria-pressed',active);});clearResult();count();if(key==='custom')input.focus();}
document.querySelectorAll('.scenario').forEach(b=>b.addEventListener('click',()=>{if(!busy)select(b.dataset.scenario);}));
document.querySelector('#reset').addEventListener('click',()=>select(selected));
input.addEventListener('input',()=>{clearResult();count();});
function element(tag,cls,text){const e=document.createElement(tag);e.className=cls;e.textContent=text;return e;}
button.addEventListener('click',async()=>{
 if(busy||!input.value.trim())return;busy=true;count();input.disabled=true;document.querySelector('#reset').disabled=true;document.querySelectorAll('.scenario').forEach(b=>b.disabled=true);document.querySelector('.agent').classList.add('busy');document.querySelector('#agent-status').textContent='LOOKING FOR SIGNALS';document.querySelector('#result-tag').textContent='Analyzing';result.replaceChildren(element('p','muted','Reading the conversation and looking for patterns…'));
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),40000);
 try{const response=await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({transcript:input.value.trim()}),signal:controller.signal});const data=await response.json();if(!response.ok)throw new Error(response.status===403?'Open the local studio on port 8001 to run an assessment.':data.detail||'The assessment could not be completed. Please try again.');
 result.replaceChildren();const names={low:'Low concern',medium:'Some cause for concern',high:'High scam risk',unknown:'Not enough information'};result.append(element('div',`result-title ${data.risk_level}`,names[data.risk_level]||'Assessment returned'));const list=element('ul','reasons','');data.reasons.forEach(reason=>list.append(element('li','',reason)));result.append(list);const actions={continue:'Continue with care',verify_independently:'Verify through an independent, trusted channel',hang_up:'End the call'};result.append(element('div','next-step',`Suggested next step: ${actions[data.recommended_action]}`));document.querySelector('#result-tag').textContent='Analysis complete';
 }catch(error){result.replaceChildren(element('p','error',error.name==='AbortError'?'This is taking longer than expected. Please try again.':error.message));document.querySelector('#result-tag').textContent='Try again';}
 finally{clearTimeout(timer);busy=false;input.disabled=false;document.querySelector('#reset').disabled=false;document.querySelectorAll('.scenario').forEach(b=>b.disabled=false);document.querySelector('.agent').classList.remove('busy');document.querySelector('#agent-status').textContent='READY WHEN YOU ARE';count();}
});
fetch('/health').then(r=>{if(!r.ok)throw Error();document.querySelector('#connection').textContent='Backend connected';}).catch(()=>{document.querySelector('#connection').textContent='Backend offline';document.querySelector('.connection i').style.background='#c99184';});select('gift');
