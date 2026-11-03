/* Original, event-only planning math. Bounded recursion; no I/O or history writes. */
(function(root){
'use strict';
const recipeNetwork=root.VisionRecipes||(typeof module!=='undefined'&&module.exports?require('./recipe-network.js'):null);
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
function indexRecipes(recipes,spec){return recipeNetwork.catalog(recipes,spec);}
function plan(recipe,batches,options={},context={}){
 const spec=context.spec||{},cfg=configure(recipe,options,spec),count=Math.floor(bounded(batches,1,1e9,1)),inventory=context.sharedInventory||{...(context.inventory||{})};
 const purchases=new Map(),steps=[],economics=[],warnings=new Set(),unknown=new Set(),outputs=[],surplus=[],idx=context.index||indexRecipes(context.recipes||[recipe],spec),produced=context.sharedProduced||{};let cost=0,nodes=0;
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
function carry(recipe,options={},context={}){
 const numeric=(v,name,maximum=1e9)=>{if(v===''||v==null||typeof v==='boolean'||!Number.isFinite(Number(v))||Number(v)<0||Number(v)>maximum)throw Error('Enter a valid '+name);return Number(v);};
 const maximum=numeric(options.maximum,'maximum LT',1e6),current=numeric(options.current,'current LT',1e6),reserve=numeric(options.reserve??25,'reserved LT',1e6),spec=context.spec||{};
 if(maximum<=0)throw Error('Maximum LT must be positive');
 const combined=new Map();for(const m of resolved(recipe,context)){const old=combined.get(m.itemId);combined.set(m.itemId,old?{...old,qty:old.qty+m.qty}:m);}
 const mats=[...combined.values()],missing=[],bag=options.bag||{},rows=mats.map(m=>{let weight=spec.items?.[m.itemId]?.weight;if(typeof weight!=='number'||!Number.isFinite(weight)||weight<0){missing.push(m.name);weight=null;}return {...m,weight,bag:numeric(bag[m.itemId]??0,'carried '+m.name)};});
 if(rows.some(m=>!Number.isInteger(m.bag)))throw Error('Already-carried quantities must be whole items');
 const cfg=configure(recipe,context.configFor?.(recipe)||{},spec),ratesModel=rates(recipe,context.configFor?.(recipe)||{},spec);
 const outputRows=[{id:recipe.itemId,name:recipe.name,units:cfg.yield,max:Math.max(cfg.yield,recipe.maxProc||cfg.yield)}];
 if(recipe.rare)outputRows.push({id:recipe.rare.itemId,name:spec.items?.[recipe.rare.itemId]?.name||'Rare output',units:Math.max(cfg.rareYield,ratesModel.rare),max:Math.max(cfg.rareYield,recipe.rare.maxProc||0)});
 const by=spec.byproducts?.[recipe.type];if(by)outputRows.push({id:by.id,name:spec.items?.[by.id]?.name||'Byproduct',units:cfg.byproductRate,max:Math.max(1,cfg.byproductRate)});
 const mode=options.mode||'expected';if(!['ingredients','expected','maxOutput'].includes(mode))throw Error('Choose a supported weight model');
 for(const o of outputRows){o.weight=spec.items?.[o.id]?.weight;if(mode!=='ingredients'&&(typeof o.weight!=='number'||!Number.isFinite(o.weight)||o.weight<0))missing.push(o.name);}
 if(missing.length)return {available:false,missing:[...new Set(missing)],maximum,current,reserve};
 const perBatch=rows.reduce((s,m)=>s+m.qty*m.weight,0),outputsKnown=outputRows.every(o=>typeof o.weight==='number'&&Number.isFinite(o.weight)&&o.weight>=0),outputPerBatch=outputsKnown?outputRows.reduce((s,o)=>s+o.weight*(mode==='maxOutput'?o.max:o.units),0):null;
 if(rows.reduce((s,m)=>s+m.bag*m.weight,0)>current+1e-6)throw Error('Carried ingredient weight exceeds current LT. Current LT must include those items.');
 const cap=options.tool===''||options.tool==null?1e9:Math.floor(numeric(options.tool,'remaining tool uses'));
 const usedLimit=Math.max(0,maximum-reserve),load=b=>rows.reduce((s,m)=>s+Math.max(0,b*m.qty-m.bag)*m.weight,0);
 const peak=b=>current+load(b)+(mode==='ingredients'?0:Math.max(0,b*(outputPerBatch-perBatch)));
 let lo=0,hi=cap;while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(peak(mid)<=usedLimit+1e-8)lo=mid;else hi=mid-1;}
 const rawBatches=lo,roundTo=numeric(options.roundTo??1,'rounding increment',1e6);if(roundTo<1||!Number.isInteger(roundTo))throw Error('Rounding increment must be a positive whole number');lo=Math.floor(lo/roundTo)*roundTo;
 const ingredientMax=perBatch>0?Math.max(0,Math.floor((Math.max(0,usedLimit-current)+rows.reduce((s,m)=>s+m.bag*m.weight,0))/perBatch)):cap;
 const at=b=>({batches:b,seconds:b*cfg.seconds,rows:rows.map(m=>({...m,required:b*m.qty,grab:Math.max(0,b*m.qty-m.bag),grabWeight:Math.max(0,b*m.qty-m.bag)*m.weight})),initialWeight:current+load(b),endWeight:outputsKnown?current+load(b)+b*(outputPerBatch-perBatch):null,peakWeight:peak(b),loadWeight:load(b),fits:peak(b)<=usedLimit+1e-8&&b<=cap,overBy:Math.max(0,peak(b)-usedLimit),exceedsTool:b>cap});
 const selected=options.batches==null?null:at(Math.floor(numeric(options.batches,'load batches')));
 return {available:true,selected,maximum,current,reserve,free:Math.max(0,usedLimit-current),batches:lo,seconds:lo*cfg.seconds,mainOutput:lo*cfg.yield,
   perBatch,outputPerBatch,mode,initialWeight:current+load(lo),endWeight:outputsKnown?current+load(lo)+lo*(outputPerBatch-perBatch):null,peakWeight:peak(lo),loadWeight:load(lo),
   rows:rows.map(m=>({...m,required:lo*m.qty,grab:Math.max(0,lo*m.qty-m.bag),grabWeight:Math.max(0,lo*m.qty-m.bag)*m.weight})),
   rawBatches,roundTo,rounded:rawBatches!==lo,outputLimited:mode!=='ingredients'&&rawBatches<Math.min(cap,ingredientMax),toolLimited:rawBatches===cap&&cap<1e9,unbounded:rawBatches===1e9,
   samples:Array.from({length:25},(_,i)=>({batches:Math.floor(lo*i/24),peak:peak(Math.floor(lo*i/24))}))};
}
// Catalog data stays normalized: edges hold IDs and per-craft ratios, not copies
// of nested recipes. Build only the chosen variant/substitution route on demand.
function productionGraph(recipe,context={},options={}){
 const index=context.index||indexRecipes(context.recipes||[recipe],context.spec),nodes=new Map(),edges=new Map(),steps=[],visited=new Set(),warnings=new Set();
 const edge=(from,to,quantity,kind)=>{const k=from+'>'+to+':'+kind,old=edges.get(k);edges.set(k,{from,to,quantity:(old?.quantity||0)+quantity,kind});};
 const item=id=>'item:'+id;
 function visit(r,path,depth){
  if(path.has(r.id)){warnings.add('Recipe cycle: '+r.name);return;}if(visited.has(r.id))return;
  if(depth>12||nodes.size>=340||visited.size>=60){warnings.add('Production map limit reached');return;}
  visited.add(r.id);nodes.set(r.id,{id:r.id,kind:'recipe',recipe:r});const cfg=configure(r,context.configFor?.(r)||{},context.spec||{}),output=item(r.itemId);nodes.set(output,{id:output,itemId:r.itemId,kind:'item'});edge(r.id,output,cfg.yield,'output');
  if(r.rare){const rare=item(r.rare.itemId);nodes.set(rare,{id:rare,itemId:r.rare.itemId,kind:'item'});edge(r.id,rare,cfg.rareYield,'rareOutput');}
  const trail=new Set([...path,r.id]);
  for(const m of resolved(r,context)){const id=item(m.itemId);nodes.set(id,{id,itemId:m.itemId,kind:'item'});edge(id,r.id,m.qty,'input');
   const variants=index.byItem.get(m.itemId)||[],sub=variants.find(v=>v.id===context.variants?.[m.itemId])||variants[0];
   if(sub&&m.itemId!==Number(options.stopItemId)&&(sub.type!=='processing'||sub.method))visit(sub,trail,depth+1);
  }steps.push(r.id);
 }
 visit(recipe,new Set(),0);return {nodes:[...nodes.values()],edges:[...edges.values()],steps,warnings:[...warnings]};
}
function ingredientRatio(recipe,itemId,quantity,context={}){
 if(quantity===''||quantity==null||typeof quantity==='boolean'||!Number.isFinite(Number(quantity))||Number(quantity)<0||Number(quantity)>1e12||!Number.isInteger(Number(quantity)))throw Error('Enter a whole ingredient quantity');
 const combined=new Map();for(const m of resolved(recipe,context)){const old=combined.get(m.itemId);combined.set(m.itemId,old?{...old,qty:old.qty+m.qty}:m);}
 const rows=[...combined.values()],anchor=combined.get(Number(itemId));if(!anchor||!(anchor.qty>0))throw Error('Ingredient does not belong to this recipe');
 const batches=Math.floor(Number(quantity)/anchor.qty);if(batches<1||batches>1e9)throw Error('Quantity must cover at least one whole craft, up to one billion crafts');
 return {batches,entered:Number(quantity),used:batches*anchor.qty,leftover:Number(quantity)-batches*anchor.qty,rows:rows.map(m=>({...m,quantity:batches*m.qty}))};
}
function runLimit(recipe,options={},context={}){
 const modes=['tool','ingredients','hybrid','manual'],mode=modes.includes(options.mode)?options.mode:['cooking','alchemy'].includes(recipe.type)?'tool':'manual';
 if(mode==='manual')return {mode,available:true,batches:Math.floor(bounded(options.count,1,1e9,1)),reason:'Manual target'};
 const inputs=new Map();for(const m of resolved(recipe,context)){const old=inputs.get(m.itemId);inputs.set(m.itemId,{...m,qty:(old?.qty||0)+m.qty});}
 const missing=[],stock=options.stock||{};let ingredientBatches=1e9;
 for(const m of inputs.values()){const raw=stock[m.itemId];if(raw===''||raw==null||typeof raw==='boolean'||!Number.isSafeInteger(Number(raw))||Number(raw)<0){missing.push(m.name);continue;}ingredientBatches=Math.min(ingredientBatches,Math.floor(Number(raw)/m.qty));}
 const value=options.tool?.remaining,toolKnown=options.tool?.available===true&&Number.isInteger(value)&&value>=0&&value<=1e6;
 if(mode!=='ingredients'&&!toolKnown)return {mode,available:false,batches:0,missing,reason:'Waiting for a current tool reading; connect/send the tool timer or enter remaining uses.'};
 if(mode!=='tool'&&missing.length)return {mode,available:false,batches:0,missing,reason:'Enter available inventory quantities for: '+missing.join(', ')};
 const n=mode==='tool'?value:mode==='ingredients'?ingredientBatches:Math.min(value,ingredientBatches);
 return {mode,available:true,batches:n,toolRemaining:toolKnown?value:null,ingredientBatches:missing.length?null:ingredientBatches,limiting:mode==='hybrid'?(value===ingredientBatches?'both':value<ingredientBatches?'tool':'ingredients'):mode,reason:n===0?'No complete craft remains':mode==='hybrid'?'Stops at the first limit: tool or ingredients':mode==='tool'?'Stops when this tool is exhausted':'Stops when an entered ingredient runs out'};
}
// A separate what-if calculation. Never mutate planner inventory or route choices.
function simulateProduction(recipe,options={},context={}){
 if(/^imperial_/.test(recipe.method||''))throw Error('Use the separate Imperial turn-ins workspace for box delivery calculations');
 if(recipe.type==='processing'&&!recipe.method)throw Error('This target has no verified production method');
 const graph=productionGraph(recipe,context,{stopItemId:options.sourceId});if(graph.warnings.length)throw Error('Resolve the production map warnings before simulating: '+graph.warnings.join('; '));
 const spec=context.spec||{},inputIds=new Set(graph.edges.filter(e=>e.kind==='input').map(e=>Number(e.from.slice(5)))),sourceId=Number(options.sourceId);
 if(!inputIds.has(sourceId)||sourceId===recipe.itemId)throw Error('Choose a starting ingredient in this production line');
 const whole=(v,label)=>{if(v===''||v==null||typeof v==='boolean'||!Number.isSafeInteger(Number(v))||Number(v)<0||Number(v)>1e12)throw Error('Enter a whole '+label+' between zero and one trillion');return Number(v);};
 const quantity=whole(options.quantity,'starting quantity');if(!quantity)throw Error('Starting quantity must be positive');
 const inventory={},names=new Map(),items=[];
 for(const id of inputIds){const name=spec.items?.[id]?.name||context.recipes?.flatMap(r=>r.mats).find(m=>m.itemId===id)?.name;
  if(!name)throw Error('Missing item identity for '+id);const k=key(name);if(names.has(k)&&names.get(k)!==id)throw Error('Ambiguous item names in this line; exact stock allocation is unavailable');names.set(k,id);
  const amount=id===sourceId?quantity:whole(options.stock?.[id]??0,'stock quantity');inventory[k]=amount;items.push({itemId:id,name,quantity:amount});
 }
 const producedIds=new Set(graph.nodes.filter(n=>n.kind==='recipe').map(n=>n.recipe.itemId)),make={};
 for(const row of items)make[key(row.name)]=producedIds.has(row.itemId)&&row.itemId!==sourceId;
 const cfg={...(context.configFor?.(recipe)||{}),keepMain:true,keepRare:true,includeRare:true,includeExtras:false,includeByproduct:false},ctx={...context,inventory,make,sharedInventory:undefined,sharedProduced:undefined},cap=1e9;let evaluations=0;
 function evaluate(batches){evaluations++;const p=plan(recipe,batches,cfg,ctx);
  if(p.warnings.some(w=>/limit reached|Recipe cycle/.test(w)))throw Error('Production calculation reached a safety limit; choose a shorter route');
  const forbidden=p.purchases.filter(m=>m.quantity>0&&(options.stockOnly===true||m.itemId===sourceId));return {p,feasible:forbidden.length===0,forbidden};
 }
 const first=evaluate(1);
 if(!first.feasible)return {batches:0,plan:null,inputs:items,remaining:items,shortfalls:first.forbidden,quantity,sourceId,stockOnly:options.stockOnly===true,evaluations,capped:false};
 let lo=1,hi=2;
 while(hi<cap&&evaluate(hi).feasible){lo=hi;hi=Math.min(cap,hi*2);}
 while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(evaluate(mid).feasible)lo=mid;else hi=mid-1;}
 const p=evaluate(lo).p,next=lo<cap?evaluate(lo+1):null,sideOutputs=[];
 for(const stage of p.steps){if(stage.recipeId===recipe.id)continue;const r=(context.recipes||[]).find(r=>r.id===stage.recipeId);if(!r)continue;const c=configure(r,context.configFor?.(r)||{},spec),by=spec.byproducts?.[r.type];
  if(r.rare&&!c.useRareInputs&&c.rareYield>0)sideOutputs.push({itemId:r.rare.itemId,name:spec.items?.[r.rare.itemId]?.name||'Rare output',quantity:stage.batches*c.rareYield,kind:'Intermediate rare / kept'});
  if(by&&c.byproductRate>0)sideOutputs.push({itemId:by.id,name:spec.items?.[by.id]?.name||'Byproduct',quantity:stage.batches*c.byproductRate,kind:'Intermediate byproduct / kept'});
 }
 return {batches:lo,plan:p,sideOutputs,inputs:items,remaining:items.map(m=>({...m,quantity:p.inventoryRemaining[key(m.name)]||0})),shortfalls:next?.forbidden||[],quantity,sourceId,stockOnly:options.stockOnly===true,evaluations,capped:lo===cap};
}
function consumers(recipes,spec){
 return recipeNetwork.catalog(recipes,spec).consumers;
}
function downstream(recipe,units,context={},options={}){
 if(!Number.isFinite(units)||units<0||units>1e12)throw Error('Choose a valid product quantity');
 const depth=Math.max(1,Math.min(4,Math.floor(options.depth||2))),limit=60,index=consumers(context.recipes||[],context.spec||{}),nodes=[];let truncated=false;
 function visit(itemId,quantity,path,seen,choices,level){
  if(level>depth)return;const candidates=[...(index.get(itemId)?.values()||[])].filter(c=>!seen.has(c.recipe.itemId)).sort((a,b)=>a.recipe.name.localeCompare(b.recipe.name));
  for(const c of candidates){if(nodes.length>=limit){truncated=true;return;}const perBatch=c.slots.reduce((s,m)=>s+m.quantity,0);if(!perBatch)continue;
   const batches=Math.floor(quantity/perBatch),cfg=configure(c.recipe,context.configFor?.(c.recipe)||{},context.spec||{}),selected={...choices};for(const m of c.slots)selected[c.recipe.id+':'+m.index]=itemId;
   const next={recipe:c.recipe,batches,perBatch,inputId:itemId,used:batches*perBatch,leftover:quantity-batches*perBatch,output:batches*cfg.yield,seconds:batches*cfg.seconds,level,path:[...path,{recipeId:c.recipe.id,batches,inputId:itemId}],choices:selected};nodes.push(next);
   if(batches>0)visit(c.recipe.itemId,next.output,next.path,new Set([...seen,c.recipe.itemId]),selected,level+1);
  }
 }
 visit(options.itemId||recipe.itemId,units,[],new Set([options.itemId||recipe.itemId]),{},1);return {nodes,truncated,depth};
}
function productionQueue(targets,context={}){
 const inventory=Object.fromEntries(Object.entries(context.inventory||{}).map(([k,v])=>[k,Number.isFinite(Number(v))?Math.max(0,Math.floor(Number(v))):0])),produced={},plans=[];
 for(const t of targets){const p=plan(t.recipe,t.batches,t.config,{...context,sharedInventory:inventory,sharedProduced:produced,choices:t.choices||context.choices,make:t.make||context.make,variants:t.variants||context.variants});plans.push(p);
  if(t.carryOutputs)for(const o of p.outputs)if(o.kept&&o.quantity>0&&['main','rare'].includes(o.kind)){const k=key(o.name),whole=Math.floor(o.quantity+1e-9);inventory[k]=(inventory[k]||0)+whole;produced[k]=(produced[k]||0)+whole;}
 }
 return {plans,inventoryRemaining:inventory,profit:plans.some(p=>p.profit===null)?null:plans.reduce((n,p)=>n+p.profit,0),seconds:plans.reduce((n,p)=>n+p.seconds,0)};
}
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
root.VisionCraft={runLimit,simulateProduction,productionGraph,ingredientRatio,carry,downstream,productionQueue,imperialRanks,projection,key,settings,configure,rates,bracket,resolved,indexRecipes,plan,queue,scenarios,tax,series};
if(typeof module!=='undefined'&&module.exports)module.exports=root.VisionCraft;
})(typeof globalThis!=='undefined'?globalThis:this);
