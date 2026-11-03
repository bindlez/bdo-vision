/* Exercise real Workerman browser actions with a deterministic paired-app fixture. */
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element{
 constructor(){this.nodes=new Map();this.listeners={};this.value='';this.checked=false;this.children=[];}
 appendChild(child){this.children.push(child);}
 querySelector(selector){if(!this.nodes.has(selector))this.nodes.set(selector,new Element());return this.nodes.get(selector);}
 querySelectorAll(selector){if(selector==='button')return ['load','prices','calc','target'].map(k=>this.querySelector('[data-wm-'+k+']'));if(selector==='[data-wm]')return ['workSpeed','moveSpeed','productivity','additionalCp','operatingCost'].map(k=>{const n=this.querySelector('[data-wm='+k+']');n.dataset={wm:k};return n;});return [];}
 addEventListener(name,fn){this.listeners[name]=fn;}
 set innerHTML(value){this.html=value;if(value.includes('data-wm="'))for(const m of value.matchAll(/data-wm="([^"]+)"[^>]*value="([^"]*)"/g))this.querySelector('[data-wm='+m[1]+']').value=m[2];if(value.includes('<option value="131"'))this.value='131';}
 get innerHTML(){return this.html||'';}
}
const calls=[],parent=new Element(),state={cp:490,target:500,days:90},job={id:'131',name:'Farm · Potato',town:'Velia',connectionCp:2,samples:110};
const model={job,breakEvenDays:150,investment:1e8,effectivePerDay:1e6,differenceAtHorizon:-1e7,shortageItems:0,unassignedCp:8,requiredCp:2,cycleMinutes:30.8,cyclesPerDay:46.75,outputs:[{name:'Potato',perDay:771,quote:{price:2000,at:'today'}}],eligible:true,status:'Modeled extra income',timeline:[{day:0,earned:0},{day:90,earned:9e7}]};
const context={window:{},document:{createElement:()=>new Element()},location:{protocol:'http:',hostname:'127.0.0.1'},AbortSignal,console,fetch:async(url,options)=>{const b=JSON.parse(options.body);calls.push(b);return {ok:true,json:async()=>b.action==='reference'?{jobs:[job],revision:'a'.repeat(40),fetchedAt:1}:model};}};
vm.createContext(context);vm.runInContext(fs.readFileSync('desktop/assets/cp-workerman.js','utf8'),context);
(async()=>{
 const view=context.window.VisionCPWorkerman.mount(parent,{state:()=>state,region:()=> 'NA',acceptQuotes(){},target:n=>state.target=n});
 assert.equal(calls.length,0,'mount must never start network work');
 const panel=parent.children[0];await panel.querySelector('[data-wm-load]').onclick();assert.equal(calls.length,1);assert.equal(panel.querySelector('[data-wm=additionalCp]').value,2);
 panel.querySelector('[data-wm-target]').onclick();assert.equal(state.target,492);
 await panel.querySelector('[data-wm-calc]').onclick();assert.equal(calls.length,2);assert.equal(calls[1].state.target,492);assert.equal(calls[1].region,'NA');
 assert(panel.querySelector('[data-wm-result]').innerHTML.includes('150.0 days'));assert(panel.querySelector('[data-wm-result]').innerHTML.includes('Modeled worker income'));
 view.invalidate();assert.equal(panel.querySelector('[data-wm-result]').innerHTML,'');assert.equal(calls.length,2,'invalidation must not request a new calculation');
 context.location.protocol='file:';context.window.VisionCPWorkerman.mount(parent,{state:()=>state,region:()=> 'NA'});const offline=parent.children[1];await offline.querySelector('[data-wm-load]').onclick();assert(offline.querySelector('[data-wm-status]').textContent.includes('paired planner'));assert.equal(calls.length,2);
 console.log('Workerman: explicit load/model, CP target, payback chart, stale-result clearing and offline state pass');
})().catch(e=>{console.error(e);process.exitCode=1;});
