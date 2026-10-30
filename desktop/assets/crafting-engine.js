/* Small, dependency-free planning math. No OCR guesses are written to history. */
(function(root){
'use strict';
const key=value=>String(value||'').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
const bounded=(v,min,max,fallback)=>Number.isFinite(Number(v))?Math.max(min,Math.min(max,Number(v))):fallback;
function settings(raw={}){return {yield:bounded(raw.yield,.01,100,1),seconds:bounded(raw.seconds,.1,3600,5),retention:bounded(raw.retention,0,100,100),extra:bounded(raw.extra,0,1e12,0),estimate:raw.estimate===true,goal:bounded(raw.goal,1,1e15,1e7)};}
function plan(recipe,batches,options,context){
 const cfg=settings(options),count=Math.floor(bounded(batches,1,1e9,1)),inventory={...(context.inventory||{})};
 const purchases=new Map(),steps=[],warnings=new Set(),economics=[];
 let totalCost=0,missing=false;
 const quote=(name,fallback)=>{
   const q=context.quote(name),live=q&&Number.isFinite(q.price)&&q.price>0;
   if(!live){warnings.add('Bundled estimate: '+name);if(!(fallback>0))missing=true;}
   return {price:live?q.price:Math.max(0,Number(fallback)||0),basis:live?'Central Market':'Bundled estimate'};
 };
 function material(name,qty,fallback,trail){
   const k=key(name),owned=Math.min(qty,Math.max(0,Number(inventory[k])||0));inventory[k]=Math.max(0,(inventory[k]||0)-owned);
   const needed=Math.max(0,qty-owned),p=quote(name,fallback);
   // Owned inputs still have an economic cost, separately from cash to buy.
   economics.push({name,quantity:qty,owned,unit:p.price,basis:p.basis});totalCost+=owned*p.price;
   const sub=context.recipes.find(r=>key(r.name)===k);
   if(needed>0&&context.make&&context.make[k]&&sub&&!trail.has(k)){
     const subCfg=settings(context.configFor?context.configFor(sub):{seconds:sub.secPerBatch}),runs=Math.ceil(needed/subCfg.yield);
     sub.mats.forEach(m=>material(m.name,m.qty*runs,m.fallback,new Set([...trail,k])));
     totalCost+=subCfg.extra*runs;steps.push({name:sub.name,batches:runs,seconds:runs*subCfg.seconds});
   }else if(needed>0){
     if(context.make&&context.make[k]&&trail.has(k))warnings.add('Recipe cycle: buy '+name);
     const row=purchases.get(k)||{name,quantity:0,unit:p.price,basis:p.basis};row.quantity+=needed;purchases.set(k,row);totalCost+=needed*p.price;
   }
 }
 recipe.mats.forEach(m=>material(m.name,m.qty*count,m.fallback,new Set([key(recipe.name)])));
 totalCost+=cfg.extra*count;
 const sell=quote(recipe.name,recipe.sell),output=count*cfg.yield,revenue=output*sell.price,proceeds=revenue*cfg.retention/100,profit=proceeds-totalCost;
 steps.push({name:recipe.name,batches:count,seconds:count*cfg.seconds});
 const seconds=steps.reduce((sum,s)=>sum+s.seconds,0);
 return {count,cfg,output,revenue,proceeds,cost:totalCost,profit,seconds,perHour:seconds?profit*3600/seconds:0,unitPrice:sell.price,breakEven:output&&cfg.retention?totalCost/(output*cfg.retention/100):null,missing,purchases:[...purchases.values()],cash:purchases.size?[...purchases.values()].reduce((s,p)=>s+p.quantity*p.unit,0):0,steps,warnings:[...warnings],economics};
}
function projection(timer,reading,now){
 const v=timer.vision,c=timer.craftPlan;
 if(!v||!c||!c.estimate||!['cooking','alchemy'].includes(c.type)||timer.status!=='running'||now>=timer.endAt||!reading||!Number.isFinite(Number(reading.updated_at))||reading.crafting_mode!==true||reading.available!==false||now-Number(reading.updated_at)*1000>15000||now-Number(reading.updated_at)*1000< -2000){if(v){v.gapAt=null;v.gapLast=null;}return {seconds:0,units:0,value:0};}
 // Only an actively connected, deliberately blocked game is eligible. Errors,
 // stopping recording, or stale OCR are not proof that crafting continued.
 if(!/covered by|must be visible, not minimized|in the tray/i.test(reading.reason||'')||/off|stale|unreadable|failed|error/i.test(reading.reason||'')){v.gapAt=null;v.gapLast=null;return {seconds:0,units:0,value:0};}
 if(v.gapAt==null||v.gapLast==null||now-v.gapLast>20000)v.gapAt=now;
 v.gapLast=now;
 const seconds=Math.max(0,Math.min(now,timer.endAt)-Math.max(v.gapAt,timer.startAt))/1000,batches=Math.min(timer.amount,seconds/c.seconds),units=batches*c.yield;
 return {seconds,units,value:units*c.unitPrice,cost:batches*c.costPerBatch};
}
function series(points,limit=48){if(points.length<=limit)return points;return Array.from({length:limit},(_,i)=>points[Math.round(i*(points.length-1)/(limit-1))]);}
root.VisionCraft={key,settings,plan,projection,series};
if(typeof module!=='undefined'&&module.exports)module.exports=root.VisionCraft;
})(typeof globalThis!=='undefined'?globalThis:this);
