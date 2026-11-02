/* Pure CP arithmetic; parity-tested against cp_planner.py. No DOM or networking. */
(function(root){
'use strict';
function create(spec){
 const number=(v,lo,hi,integer=false)=>{if(typeof v==='boolean'||v===null||v==='')throw Error('Enter a number');const n=Number(v);if(!Number.isFinite(n)||n<lo||n>hi||(integer&&!Number.isInteger(n)))throw Error('Enter '+(integer?'a whole number':'a number')+' from '+lo.toLocaleString()+' to '+hi.toLocaleString());return n;};
 const xpPerCp=cp=>cp<0||cp>=spec.maxCp?null:[...spec.curve].reverse().find(x=>cp>=x[0])[1];
 function advance(cp,percent,gain){const start=cp;let remaining=xpPerCp(cp)*percent/100+gain;while(cp<spec.maxCp&&remaining+1e-7>=xpPerCp(cp)){remaining-=xpPerCp(cp);cp++;}const xp=xpPerCp(cp);return {cp,percent:xp?remaining/xp*100:null,gained:cp-start,unmodeledXp:xp===null?Math.max(0,remaining):0};}
 function toTarget(cp,percent,target){if(target<=cp)return 0;let xp=-xpPerCp(cp)*percent/100;for(let p=cp;p<target;p++)xp+=xpPerCp(p);return Math.max(0,xp);}
 function calculate(s,quotes={}){
  const cp=number(s.cp??490,0,599,true),pct=number(s.percent??19.26,0,99.9999),target=number(s.target??500,0,600,true),retention=number(s.retention??84.5,0,100)/100;
  const days=number(s.days??90,1,3650,true),income=number(s.income??0,0,1e9),deploy=number(s.deploy??100,0,600,true),delay=number(s.delay??0,0,3650),split=number(s.split??50,0,100),cashPolicy=s.cashPolicy??'best';
  if(!['best','vendor'].includes(cashPolicy)||!s.counts||Array.isArray(s.counts)||typeof s.counts!=='object')throw Error('Choose a valid cash route and item counts');
  const missing=[],exchangeRoutes=[],products=spec.products.map(p=>{
   const count=number(s.counts[p.key]??0,0,1e9,true),batches=Math.floor(count/p.batch),leftover=count%p.batch,vendor=p.batch*p.vendor;
   const routes=[{item:'Direct NPC sale',units:p.batch,unit:p.vendor,gross:vendor*batches+leftover*p.vendor,net:vendor*batches+leftover*p.vendor,perBatch:vendor,source:'NPC · no market tax',updated_at:'2026-11-02',known:true,npc:true}];
   for(const [item,units] of p.rewards){const q=Object.hasOwn(quotes,item)?quotes[item]:{},v=q.unit_price,known=typeof v==='number'&&Number.isFinite(v)&&v>0&&v<=1e12&&q.price_basis!=='npc_vendor';if(count&&!known)missing.push(item);const gross=known?v*units*batches:null;routes.push({item,units,unit:known?v:null,gross,net:known?gross*retention+leftover*p.vendor:null,perBatch:known?v*units*retention:null,known,npc:false,source:String(q.source||'Unpriced'),updated_at:String(q.updated_at||'')});}
   const best=cashPolicy==='vendor'?routes[0]:routes.filter(r=>r.known).reduce((a,b)=>a.perBatch>=b.perBatch?a:b);
   if(count)exchangeRoutes.push(...routes.map(r=>({product:p.name,batches,leftover,...r})));
   return {...p,count,batches,leftover,best,routes};
  });
  const ordered=[...products].sort((a,b)=>a.best.perBatch-b.best.perBatch||a.key.localeCompare(b.key)),totalBatches=products.reduce((v,p)=>v+p.batches,0),cashTotal=products.reduce((v,p)=>v+p.best.net,0),targetXp=toTarget(cp,pct,target),targetBatches=Math.ceil(Math.max(0,targetXp-1e-7)/900);
  function route(key,requested){let remaining=requested,foregone=0;const allocation=ordered.map(p=>{const batches=Math.min(remaining,p.batches);remaining-=batches;foregone+=batches*p.best.perBatch;return {key:p.key,name:p.name,batches,items:batches*p.batch,remaining:p.count-batches*p.batch,cashRoute:p.best.item};});
   const batches=requested-remaining,finish=advance(cp,pct,batches*900),deployed=Math.min(finish.gained,deploy),daily=deployed*income,earnings=daily*Math.max(0,days-delay),cash=cashTotal-foregone;
   return {key,...finish,batches,xp:batches*900,cash,foregone,allocation,daily,deployed,future:cash+earnings,earnings,difference:earnings-foregone,breakEvenDays:daily>0?delay+foregone/daily:null,requiredPerCpDay:deployed&&days>delay?foregone/(deployed*(days-delay)):null};
  }
  const routes=[route('cash',0),route('cp',totalBatches),route('target',Math.min(targetBatches,totalBatches)),route('split',Math.floor(totalBatches*split/100))];
  const winner=routes.reduce((a,b)=>a.future>=b.future?a:b).key,nextXp=xpPerCp(cp)*(1-pct/100);
  return {cp,percent:pct,target,days,retention,income,deploy,delay,split,cashPolicy,nextXp,nextBatches:Math.ceil(Math.max(0,nextXp-1e-7)/900),targetXp,targetBatches,targetReachable:targetBatches<=totalBatches,totalXp:totalBatches*900,totalBatches,vendorTotal:products.reduce((v,p)=>v+p.count*p.vendor,0),products,exchangeRoutes,missing:[...new Set(missing)].sort(),cashTotal,routes,winner,curveVersion:spec.version};
 }
 return {calculate,xpPerCp,advance,toTarget};
}
root.VisionCP={create};if(typeof module!=='undefined')module.exports=root.VisionCP;
})(typeof globalThis!=='undefined'?globalThis:this);
