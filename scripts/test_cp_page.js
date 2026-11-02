/* Execute the actual shipped CP page in a small DOM fixture. No browser driver. */
'use strict';
const assert=require('assert'),fs=require('fs'),vm=require('vm');
const nodes=new Map(),timers=[];
class Element{
 constructor(){this.dataset={};this.style={};this.listeners={};this.value='';this.classList={add(){},toggle(){}};this.parentNode={setAttribute(){}};}
 set innerHTML(value){this.html=value;for(const match of value.matchAll(/id="([^"]+)"/g))if(!nodes.has(match[1]))nodes.set(match[1],new Element());}
 get innerHTML(){return this.html||'';}
 appendChild(){} addEventListener(type,fn){this.listeners[type]=fn;}
 querySelector(selector){return this.querySelectorAll(selector)[0]||new Element();}
 querySelectorAll(selector){if(!this.inputs)this.inputs=[...this.innerHTML.matchAll(/data-(cp|stock)="([^"]+)"[^>]*value="([^"]*)"/g)].map(m=>{const n=new Element();n.dataset[m[1]]=m[2];n.value=m[3];return n;});return this.inputs.filter(n=>selector==='[data-cp]'?n.dataset.cp:selector==='[data-stock]'?n.dataset.stock:selector==='[data-cp=cashPolicy]'?n.dataset.cp==='cashPolicy':false);}
}
for(const id of ['sidebarNav','viewCraft'])nodes.set(id,new Element());nodes.get('viewCraft').parentNode=new Element();
const storage=new Map(),context={console,structuredClone,URL,URLSearchParams,AbortSignal,MouseEvent:class{},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},location:{protocol:'file:',hostname:'',hash:'#cp'},history:{replaceState(){}},showView(){},document:{getElementById:id=>nodes.get(id),createElement:()=>new Element(),querySelectorAll:()=>[]},setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout(){},addEventListener(){}};context.window=context;
vm.createContext(context);
const html=fs.readFileSync('bdo-market-intelligence.html','utf8'),block=html.split('<!-- VISION CP START -->')[1].split('<!-- VISION CP END -->')[0],script=block.match(/<script>([\s\S]*)<\/script>/)[1];
vm.runInContext(script,context);
const host=nodes.get('visionCP'),output=nodes.get('cpOutput');assert(output.innerHTML.includes('567 CP'));assert(output.innerHTML.includes('Market prices needed'));const snapshot=JSON.parse(fs.readFileSync('desktop/assets/demo-market-snapshot.json','utf8'));context.VisionCPPage.acceptQuotes(snapshot.items,'NA');assert(output.innerHTML.includes('124.85B'));assert(output.innerHTML.includes('Break-even'));assert(output.innerHTML.includes('data-frontier="50"'));
const income=host.querySelectorAll('[data-cp]').find(n=>n.dataset.cp==='income');assert(income);income.value='500000';host.listeners.input({target:income});timers.pop()();assert(output.innerHTML.includes('A longer commitment'));assert(output.innerHTML.includes('Time to recover the investment'));
income.value='-1';host.listeners.input({target:income});timers.pop()();assert(output.innerHTML.includes('Check the highlighted'));assert(nodes.get('cpError').textContent.includes('Previous results are hidden'));
nodes.get('cpExample').onclick();nodes.get('cpClear').onclick();assert(output.innerHTML.includes('Enter your byproducts'));assert(output.innerHTML.includes('0 complete exchanges'));
nodes.get('cpExample').onclick();assert(output.innerHTML.includes('45,200'));assert(output.innerHTML.includes('117.32B'));
host.listeners.click({target:{closest:selector=>selector==='[data-frontier]'?{dataset:{frontier:'50'}}:null}});assert(output.innerHTML.includes('Custom split · the plan'));assert(output.innerHTML.includes('541 CP'));
host.listeners.click({target:{closest:selector=>selector==='[data-cp-solve]'?{dataset:{cpSolve:'90'}}:null}});assert(output.innerHTML.includes('Payback fits your horizon'));
const originalMarkup=output.innerHTML;host.listeners.input({target:{hasAttribute:name=>name==='data-cp-elapsed',value:'30',dataset:{}}});assert.equal(nodes.get('cpSimDay').textContent,'30');assert.equal(output.innerHTML,originalMarkup);
console.log('Actual shipped CP page boots; scenario edits, invalid inputs, stock reset, target allocation and graph interactions render correctly');
