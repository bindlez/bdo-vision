/* Original, event-only planning math. Bounded recursion; no I/O or history writes. */
(function(root){
'use strict';
const key=v=>String(v||'').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
const bounded=(v,lo,hi,fallback)=>v!==null&&v!==''&&Number.isFinite(Number(v))?Math.max(lo,Math.min(hi,Number(v))):fallback;
function settings(raw={}){return {...raw,yield:bounded(raw.yield,.01,10000,1),seconds:bounded(raw.seconds,.1,3600,5),retention:bounded(raw.retention,0,100,84.5),extra:bounded(raw.extra,0,1e12,0),estimate:raw.estimate===true,goal:bounded(raw.goal,1,1e15,1e7),mastery:bounded(raw.mastery,0,3000,0),success:bounded(raw.success,1,100,100),rareYield:bounded(raw.rareYield,0,1000,0),byproductRate:bounded(raw.byproductRate,0,100,0),xpBonus:bounded(raw.xpBonus,0,10000,0),mass:raw.mass!==false,includeRare:raw.includeRare!==false,includeByproduct:raw.includeByproduct===true};}
function bracket(spec,type,mastery){const rows=spec?.mastery?.[type]||[];return rows.filter(r=>r.masteryLevel<=mastery).at(-1)||rows[0]||{};}
function rates(recipe,options={},spec={}){
 const cfg=settings(options),b=bracket(spec,recipe.type,cfg.mastery),low=recipe.minProc??1,high=recipe.maxProc??1,average=(low+high)/2,crafted=['cooking','alchemy'].includes(recipe.type);
 const normal=average+(crafted?(high-average)*(b.maxProcChance||0):0);let rare=0;
 if(recipe.rare){const r=recipe.rare,avg=(r.minProc+r.maxProc)/2;rare=crafted?(avg+(recipe.type==='cooking'?(r.maxProc-avg)*(b.maxProcChance||0):0))*(recipe.type==='cooking'?.2+(b.rareAdditionalChance||0):.2):avg*(r.procChance??0);}
 const massEligible=recipe.type==='processing'&&!['simple_alchemy','simple_cooking','manufacture','imperial_cooking','imperial_alchemy'].includes(recipe.method);
 const mass=recipe.type==='cooking'&&cfg.mass?1+9*(b.massProduceChance||0):massEligible&&cfg.mass?Math.max(1,(b.batchProcessing||10)/10):1;
 const seconds=bounded(options.baseSeconds,.1,3600,recipe.secPerBatch||10)/mass/(massEligible?cfg.success/100:1);
 return {normal,rare,mass,seconds,byproduct:spec.byproducts?.[recipe.type]?.rate||0,bracket:b};
}
function configure(recipe,options={},spec={}){const r=rates(recipe,options,spec);return settings({...options,yield:options.yield??r.normal,rareYield:options.rareYield??r.rare,seconds:options.seconds??r.seconds,byproductRate:options.byproductRate??r.byproduct});}
function resolved(recipe,context={}){const spec=context.spec||{},choices=context.choices||{};return recipe.mats.map((m,index)=>{const options=m.groupId?(spec.groups?.[m.groupId]||[]):[],wanted=choices[recipe.id+':'+index],choice=options.find(o=>o.itemId===Number(wanted))||options.find(o=>o.itemId===m.itemId)||{itemId:m.itemId,value:m.value||1},meta=spec.items?.[choice.itemId]||{};return {...m,itemId:choice.itemId,name:meta.name||m.name,qty:m.groupId?Math.ceil((m.required??m.qty)/choice.value):m.qty,options};});}
function indexRecipes(recipes){const byItem=new Map(),byName=new Map();for(const r of recipes){if(!byItem.has(r.itemId))byItem.set(r.itemId,[]);byItem.get(r.itemId).push(r);const k=key(r.name);if(!byName.has(k))byName.set(k,[]);byName.get(k).push(r);}return {byItem,byName};}
function plan(recipe,batches,options={},context={}){
 const spec=context.spec||{},cfg=configure(recipe,options,spec),count=Math.floor(bounded(batches,1,1e9,1)),inventory=context.sharedInventory||{...(context.inventory||{})};
 const purchases=new Map(),steps=[],economics=[],warnings=new Set(),unknown=new Set(),outputs=[],surplus=[],idx=context.index||indexRecipes(context.recipes||[recipe]),produced=context.sharedProduced||{};let cost=0,nodes=0;
 function price(itemId,name,input=false){const q=context.quote?.(name,itemId),v=q?.price??q?.unit_price,meta=spec.items?.[itemId]||{},market=typeof v==='number'&&Number.isFinite(v)&&v>0&&q?.price_basis!=='npc_vendor';if(input&&meta.npcBuy>0&&(!market||meta.npcBuy<v))return {price:meta.npcBuy,basis:'NPC purchase',known:true};return market?{price:v,basis:q.source||'Central Market',known:true,updatedAt:q.updatedAt||q.updated_at,stock:q.stock,volume:q.volume}:{price:null,basis:'Unpriced',known:false};}
 function charge(q,qty,name){if(q.known)cost+=q.price*qty;else if(qty){unknown.add(name);warnings.add('Missing price: '+name);}}
 function consume(mat,qty,trail,depth){
  if(++nodes>400||depth>12){warnings.add('Plan limit reached: reduce recursive steps');unknown.add('Recursion limit');return;}
  const k=key(mat.name),owned=Math.min(qty,Math.max(0,Number(inventory[k])||0));inventory[k]=Math.max(0,(inventory[k]||0)-owned);const reused=Math.min(owned,produced[k]||0);produced[k]=Math.max(0,(produced[k]||0)-reused);const needed=qty-owned,p=price(mat.itemId,mat.name,true);if(owned>reused)charge(p,owned-reused,mat.name);
  const variants=mat.itemId?idx.byItem.get(mat.itemId):idx.byName.get(k),wanted=context.variants?.[mat.itemId],sub=variants?.find(r=>r.id===wanted)||variants?.[0],make=context.make?.[k];economics.push({name:mat.name,itemId:mat.itemId,quantity:qty,owned,unit:p.price,basis:p.basis,depth});
  if(needed>0&&make&&sub&&!trail.has(sub.id)){
   const c=configure(sub,context.configFor?.(sub)||{},spec),effectiveYield=c.yield+(c.useRareInputs&&sub.rare?3*c.rareYield:0),runs=Math.ceil(needed/effectiveYield),inputs=resolved(sub,context).map(m=>({...m,quantity:m.qty*runs}));for(const m of inputs)consume(m,m.quantity,new Set([...trail,sub.id]),depth+1);cost+=c.extra*runs;steps.push({name:sub.name,recipeId:sub.id,itemId:sub.itemId,type:sub.type,batches:runs,seconds:runs*c.seconds,depth,needed,expected:runs*effectiveYield,surplus:runs*effectiveYield-needed,inputs});
   const extra=runs*effectiveYield-needed;if(extra>0){inventory[k]=(inventory[k]||0)+extra;produced[k]=(produced[k]||0)+extra;surplus.push({name:sub.name,quantity:extra});}
  }else if(needed>0){if(make&&sub&&trail.has(sub.id))warnings.add('Recipe cycle: buy '+mat.name);const row=purchases.get(k)||{name:mat.name,itemId:mat.itemId,quantity:0,unit:p.price,basis:p.basis,stock:p.stock};row.quantity+=needed;purchases.set(k,row);charge(p,needed,mat.name);}
 }
 const materials=resolved(recipe,context);for(const m of materials)consume(m,m.qty*count,new Set([recipe.id]),0);cost+=cfg.extra*count;const inputsMissing=unknown.size>0;
 function output(itemId,name,quantity,kind,kept=false,retention=cfg.retention/100,fixed=null){const p=fixed===null?price(itemId,name):{price:fixed,basis:'Imperial delivery model',known:true};if(quantity&&!p.known&&!kept){unknown.add(name);warnings.add('Missing price: '+name);}outputs.push({itemId,name,quantity,kind,unit:p.price,basis:p.basis,kept,retention,gross:p.known?quantity*p.price:null,net:p.known?quantity*p.price*retention:null,weight:(spec.items?.[itemId]?.weight||0)*quantity});}
 const imperial=/^imperial_/.test(recipe.method||''),imperialType=recipe.method==='imperial_cooking'?'cooking':'alchemy',imperialBase=imperial?spec.items?.[recipe.itemId]?.imperialBase:null;
 const delivery=imperial&&imperialBase?imperialBase*(2.5+(bracket(spec,imperialType,cfg.mastery).imperialBonus||0)):null;
 output(recipe.itemId,recipe.name,count*cfg.yield,'main',cfg.keepMain===true,imperial?1:cfg.retention/100,delivery);
 if(recipe.rare&&cfg.includeRare&&cfg.rareYield>0)output(recipe.rare.itemId,spec.items?.[recipe.rare.itemId]?.name||'Rare output',count*cfg.rareYield,'rare',cfg.keepRare===true);
 if(recipe.type==='alchemy'&&cfg.includeExtras){const b=bracket(spec,'alchemy',cfg.mastery);for(const [tier,rows] of Object.entries(spec.alchemyExtras||{})){const chance=b[{regular:'extraItemChanceRegular',special:'extraItemChanceSpecial',rare:'extraItemChanceRare'}[tier]]||0,total=rows.reduce((s,r)=>s+r[1],0);for(const [id,weight] of rows)output(id,spec.items?.[id]?.name||'Extra item '+id,count*chance*weight/total,'extra · '+tier);}}
 const byproduct=spec.byproducts?.[recipe.type];if(byproduct&&cfg.byproductRate>0)output(byproduct.id,spec.items?.[byproduct.id]?.name||'Byproduct',count*cfg.byproductRate,'byproduct',true);
 let byproductValue=0;if(byproduct&&cfg.includeByproduct&&cfg.byproductReward){const reward=spec.items?.[cfg.byproductReward],ratio=recipe.type==='cooking'?({9213:50,9065:12}[cfg.byproductReward]):({5301:20,4801:20,4802:20,4803:20,4804:20,4805:20,9733:.5}[cfg.byproductReward]);if(reward&&ratio){const q=price(reward.id,reward.name),units=Math.floor(count*cfg.byproductRate/10)*10*ratio;if(q.known)byproductValue=units*q.price*cfg.retention/100;else if(units>0){unknown.add(reward.name);warnings.add('Missing byproduct exchange: '+reward.name);}}}
 steps.push({name:recipe.name,recipeId:recipe.id,itemId:recipe.itemId,type:recipe.type,batches:count,seconds:count*cfg.seconds,depth:0,needed:count*cfg.yield,expected:count*cfg.yield,surplus:0,inputs:materials.map(m=>({...m,quantity:m.qty*count}))});
 const missing=unknown.size>0,knownRevenue=outputs.filter(o=>!o.kept&&o.gross!==null).reduce((s,o)=>s+o.gross,0),knownProceeds=outputs.filter(o=>!o.kept&&o.net!==null).reduce((s,o)=>s+o.net,0)+byproductValue,seconds=steps.reduce((s,x)=>s+x.seconds,0),profit=missing?null:knownProceeds-cost,outputQty=count*cfg.yield;
 const cashRows=[...purchases.values()],cashMissing=cashRows.some(m=>m.unit===null),unitPrice=outputs[0].unit,ownedBatches=materials.length?Math.floor(Math.min(...materials.map(m=>(context.inventory?.[key(m.name)]||0)/m.qty))):0,side=knownProceeds-(outputs[0].net||0),breakEven=missing||!outputQty||!cfg.retention?null:Math.max(0,(cost-side)/(outputQty*cfg.retention/100));
 return {count,cfg,output:outputQty,outputs,revenue:missing?null:knownRevenue,proceeds:missing?null:knownProceeds,cost:inputsMissing?null:cost,knownCost:cost,knownProceeds,profit,seconds,perHour:profit===null?null:profit*3600/seconds,unitPrice,breakEven,missing,unknown:[...unknown],purchases:cashRows,cash:cashMissing?null:cashRows.reduce((s,p)=>s+p.quantity*p.unit,0),steps,surplus,materials,warnings:[...warnings],economics,byproductValue,xp:count*(recipe.xp||0)*(1+cfg.xpBonus/100),ownedBatches,inventoryRemaining:inventory,weight:outputs.reduce((s,o)=>s+o.weight,0)};
}
function queue(targets,context){const inventory={...(context.inventory||{})},produced={},plans=targets.map(t=>plan(t.recipe,t.batches,t.config,{...context,sharedInventory:inventory,sharedProduced:produced}));return {plans,inventoryRemaining:inventory,profit:plans.some(p=>p.profit===null)?null:plans.reduce((s,p)=>s+p.profit,0),seconds:plans.reduce((s,p)=>s+p.seconds,0)};}
function scenarios(p){return [.8,.9,1,1.1,1.2].map(multiplier=>({multiplier,profit:p.missing?null:p.knownProceeds*multiplier-p.knownCost}));}
function tax(options={}){return Math.min(100,65*(1+(options.valuePack?.3:0)+(options.merchantRing?.05:0)+bounded(options.familyFame,0,1.5,0)/100));}
function series(points,limit=48){if(points.length<=limit)return points;return Array.from({length:limit},(_,i)=>points[Math.round(i*(points.length-1)/(limit-1))]);}
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


// Imperial costs are acquisition costs, not market-sale proceeds. Do not apply
// market tax or credit side products against the cost of filling today's boxes.
function imperialRanks(recipes,spec,quote,options={}){
 const count=Math.floor(bounded(options.boxes,1,10000,1)),index=indexRecipes(recipes),result={};
 for(const type of ['cooking','alchemy']){
  const boxes=recipes.filter(r=>r.method==='imperial_'+type&&(!options.guruOnly||[9856,9871].includes(r.itemId))&&(!options.tiers?.[type]||r.itemId===Number(options.tiers[type]))),buy=[],craft=[],craftInStock=[];
  const mastery=bounded(options.mastery?.[type],0,3000,0);
  for(const box of boxes){
   const boxYield=box.minProc||1,payout=(spec.items[box.itemId]?.imperialBase||0)*(2.5+(bracket(spec,type,mastery).imperialBonus||0));
   if(box.mats.length!==1||!payout)continue;
   const mat=box.mats[0],quantity=Math.ceil(mat.qty*count/boxYield),q=quote(mat.name,mat.itemId),price=q?.price??q?.unit_price;
   const row={boxId:box.itemId,boxName:box.name,boxRecipeId:box.id,itemId:mat.itemId,name:mat.name,quantity,boxes:count,payout:payout*count,stock:q?.stock,updatedAt:q?.updatedAt||q?.updated_at};
   const cost=Number.isFinite(price)&&price>0&&q?.price_basis!=='npc_vendor'?price*quantity:null;
   buy.push({...row,cost,perBox:cost===null?null:cost/count,profit:cost===null?null:row.payout-cost,inStock:cost!==null&&Number.isFinite(q?.stock)&&q.stock>=quantity});
   // A rare proc can fill a box even when it has no dedicated recipe. Its
   // acquisition cost uses the expected rare yield, with no main-output credit.
   const sources=recipes.filter(r=>r.type===type&&(r.itemId===mat.itemId||r.rare?.itemId===mat.itemId));let best=null,bestStock=null;
   for(const source of sources)for(const stockOnly of [false,true]){
    const cfg=configure(source,{...(options.characters?.[type]||{}),mastery},spec),yieldQty=source.itemId===mat.itemId?cfg.yield:cfg.rareYield;
    if(!(yieldQty>0))continue;
    const runs=Math.ceil(quantity/yieldQty),choices={};
    for(const [i,m] of source.mats.entries())if(m.groupId){let cheapest=null;for(const o of spec.groups[m.groupId]||[]){const meta=spec.items[o.itemId],p=quote(meta.name,o.itemId),market=p?.price??p?.unit_price,npc=meta.npcBuy,qty=Math.ceil((m.required??m.qty)/o.value);const available=!stockOnly||(Number.isFinite(p?.stock)&&p.stock>=qty*runs),unit=Math.min(available&&Number.isFinite(market)&&market>0?market:Infinity,npc>0?npc:Infinity),total=unit*qty;if(Number.isFinite(total)&&(!cheapest||total<cheapest.total))cheapest={id:o.itemId,total};}if(cheapest)choices[source.id+':'+i]=cheapest.id;}
    const needed=new Map();for(const m of resolved(source,{spec,choices}))needed.set(m.itemId,(needed.get(m.itemId)||0)+m.qty*runs);
    const stockQuote=(name,id)=>{const q=quote(name,id);return Number.isFinite(q?.stock)&&q.stock>=(needed.get(id)||0)?q:null;};
    const p=plan(source,runs,{...cfg,keepMain:true,keepRare:true,includeExtras:false,includeByproduct:false},{spec,recipes,index,quote:stockOnly?stockQuote:quote,choices});
    const inStock=p.cost!==null&&p.purchases.every(m=>(m.basis==='NPC purchase'&&spec.items[m.itemId]?.npcBuy>0&&m.unit===spec.items[m.itemId].npcBuy)||(Number.isFinite(m.stock)&&m.stock>=m.quantity));
    const candidate={...row,cost:p.cost,perBox:p.cost===null?null:p.cost/count,profit:p.cost===null?null:row.payout-p.cost,recipeId:source.id,runs,expectedOutput:runs*yieldQty,surplus:runs*yieldQty-quantity,inStock,ingredients:p.purchases,choices};
    if(!stockOnly&&(!best||(candidate.cost!==null&&(best.cost===null||candidate.cost<best.cost))))best=candidate;
    if(inStock&&(!bestStock||candidate.cost<bestStock.cost))bestStock=candidate;
   }
   craft.push(best||{...row,cost:null,perBox:null,profit:null});
   if(bestStock)craftInStock.push(bestStock);
  }
  const sort=(a,b)=>(a.cost===null)-(b.cost===null)||(a.cost??Infinity)-(b.cost??Infinity)||a.name.localeCompare(b.name);
  result[type]={buy:buy.sort(sort),craft:craft.sort(sort),craftInStock:craftInStock.sort(sort)};
 }
 return result;
}
root.VisionCraft={imperialRanks,projection,key,settings,configure,rates,bracket,resolved,indexRecipes,plan,queue,scenarios,tax,series};
if(typeof module!=='undefined'&&module.exports)module.exports=root.VisionCraft;
})(typeof globalThis!=='undefined'?globalThis:this);
