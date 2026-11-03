/* Exercise the actual shipped owned blocks. DOM fixture, not visual browser QA. */
'use strict';
const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const nodes=new Map();
class Element{
 constructor(){this.dataset={};this.style={};this.value='';this.checked=false;this.open=false;this.children=[];this.controls=[];}
 set innerHTML(value){this.html=value;this.controls=[];for(const match of value.matchAll(/<(input|select|button|details|div|section|p|a)\b([^>]*)>/g)){const n=new Element(),attrs=match[2];n.checked=/\bchecked\b/.test(attrs);n.open=/\bopen\b/.test(attrs);for(const a of attrs.matchAll(/([\w-]+)="([^"]*)"/g)){if(a[1].startsWith('data-'))n.dataset[a[1].slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=a[2];else n[a[1]]=a[2];}if(match[1]==='select'){const options=value.slice(match.index+match[0].length,value.indexOf('</select>',match.index));n.html=options;n.value=(options.match(/<option value="([^"]*)" selected/)||options.match(/<option value="([^"]*)"/))?.[1]||'';}if(n.id)nodes.set(n.id,n);if(n.id==='productionRoadmap')n.innerHTML=value.slice(match.index+match[0].length,value.indexOf('</section>',match.index));this.controls.push(n);}}
 get innerHTML(){return this.html||'';}
 querySelectorAll(selector){if(selector==='details[open]')return this.controls.filter(n=>n.dataset.section&&n.open);if(selector==='details')return this.controls.filter(n=>n.dataset.section);const attr=selector.match(/^\[data-([\w-]+)\]$/);if(attr){const k=attr[1].replace(/-([a-z])/g,(_,c)=>c.toUpperCase());return this.controls.filter(n=>Object.hasOwn(n.dataset,k));}return [];}
 insertBefore(){}querySelector(){return null;}focus(){}setSelectionRange(){}matches(){return false;}
 setAttribute(k,v){this[k]=v;}removeAttribute(k){delete this[k];}
}
for(const id of ['craftDetail','recipeList'])nodes.set(id,new Element());
const recipes=JSON.parse(fs.readFileSync('desktop/assets/recipes.json','utf8')),spec=JSON.parse(fs.readFileSync('desktop/assets/crafting-data.json','utf8')),snapshot=JSON.parse(fs.readFileSync('desktop/assets/demo-market-snapshot.json','utf8'));
let started=null,download=null;const context={console,Map,Set,URL,AbortSignal,structuredClone,RECIPES:recipes,VISION_CRAFT_DATA:spec,region:'na',recipeTab:'alchemy',lastCraftAmount:100,selectedRecipe:recipes.find(r=>r.itemId===678),location:{protocol:'file:',hostname:''},bridgeSelectedOrigin:null,visionMarketById:{},visionMarketByName:{},visionMarketQuoteDetails:{},visionEscape:v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),visionName:n=>n.toLowerCase(),localStorage:{getItem:()=>null,setItem(){}},saveState(){},toast(){},fmtTime:n=>n.toFixed(1)+'s',setTimeout,clearTimeout,document:{getElementById:id=>nodes.get(id)||null,createElement:()=>new Element(),activeElement:new Element(),querySelectorAll:()=>[]},startCraft:(r,n,opts)=>{started={r,n,opts};},intelDownload:(...args)=>{download=args;},openModal(){},closeModal(){}};
context.window=context;for(const q of snapshot.items){context.visionMarketById['na:'+q.id]=q.price;context.visionMarketQuoteDetails['na:'+q.id]=q;}
vm.createContext(context);const html=fs.readFileSync('bdo-market-intelligence.html','utf8');
for(const marker of ['RECIPE_NETWORK_JS','CRAFTING_ENGINE_JS','CRAFTING_STUDIO_JS','CRAFTING_SIMULATOR_JS','PRODUCTION_ROADMAP_JS','RECIPE_BROWSER_JS']){const script=html.split('/* OWNED '+marker+' START */')[1]?.split('/* OWNED '+marker+' END */')[0];assert(script,marker);vm.runInContext(script,context);}
nodes.set('imperialQuick',new Element());
context.craftRoadState.runModes={cooking:'manual',alchemy:'manual'};
context.craftStudioRender(context.selectedRecipe,100);context.renderRecipeList();
assert(nodes.get('imperialQuick').innerHTML.includes('BEST TO BUY & PACK'));
assert(nodes.get('imperialQuick').innerHTML.includes('BEST TO CRAFT & PACK'));
assert(nodes.get('imperialQuick').innerHTML.includes('BEST TO BUY & PACK · IN STOCK'));
assert(nodes.get('imperialQuick').innerHTML.includes('BEST TO CRAFT & PACK · IN STOCK'));
assert(nodes.get('imperialQuick').innerHTML.includes('Turn-in silver'));
nodes.get('imperialGuruOnly').onchange({target:{checked:true}});assert(context.imperialSettings.guruOnly);
nodes.get('imperialGuruOnly').onchange({target:{checked:false}});assert(!context.imperialSettings.guruOnly);
assert(!nodes.get('imperialAnalysis').innerHTML);
const oldQuote=context.craftStudioQuote;context.craftStudioQuote=()=>({price:100,stock:100000});context.craftImperialRender();
nodes.get('imperialAdvanced').ontoggle({target:{open:true}});
assert(nodes.get('imperialAnalysis').innerHTML.includes('role="img"'));assert(nodes.get('imperialAnalysis').innerHTML.includes('Ingredient'));
nodes.get('imperialCP').onchange({target:{value:'491'}});assert.equal(context.imperialSettings.cp,491);
assert(nodes.get('imperialQuick').innerHTML.includes('245 boxes/day maximum'));
assert(nodes.get('imperialQuick').innerHTML.includes('Daily craft profit'));
const daily=context.VisionCraft.imperialRanks(recipes,spec,context.craftStudioQuote,{boxes:245}).cooking.buy.sort((a,b)=>b.profit-a.profit)[0];
assert(nodes.get('imperialQuick').innerHTML.includes(context.craftStudioMoney(daily.profit)+' potential daily profit'));
nodes.get('imperialCP').onchange({target:{value:'0'}});assert(!nodes.get('imperialQuick').innerHTML.includes('potential daily profit'));
context.craftStudioQuote=oldQuote;context.craftImperialRender();
assert(!nodes.get('imperialQuick').innerHTML.includes('<select'));
assert.equal(nodes.get('imperialQuick').controls.filter(n=>n.id==='imperialMastery').length,1);
nodes.get('imperialMastery').onchange({target:{value:'1500'}});assert.equal(context.imperialSettings.mastery.cooking,1500);
nodes.get('imperialSortCraft').onclick();assert.equal(context.imperialSettings.sort,'craft');
nodes.get('imperialAlchemy').onclick();assert.equal(context.imperialSettings.type,'alchemy');
nodes.get('imperialMastery').onchange({target:{value:'1200'}});assert.equal(context.imperialSettings.mastery.alchemy,1200);
nodes.get('imperialCooking').onclick();assert.equal(context.imperialSettings.mastery.cooking,1500);
assert(nodes.get('craftDetail').innerHTML.includes('EXPECTED NET PROFIT'));assert(nodes.get('craftDetail').innerHTML.includes('choose substitutions'));
nodes.get('studioTarget').onchange({target:{value:'1000'}});assert.equal(context.lastCraftAmount,400);
nodes.get('studioQueue').onclick();assert.equal(context.craftStudioState.queue.length,1);assert.equal(context.craftStudioState.queue[0].amount,400);
nodes.get('studioExport').onclick();assert(download[0].endsWith('.txt'));assert(download[1].includes('Expected plan'));
nodes.get('btnStartCraft').onclick();assert.equal(started.n,400);assert.equal(started.opts.craftPlan.itemId,678);assert(started.opts.craftPlan.materials.every(m=>m.itemId>0));
nodes.get('studioRing').checked=true;nodes.get('studioFame').value='1.5';nodes.get('studioTax').onclick();assert(Math.abs(Number(nodes.get('studioRetention').value)-88.725)<1e-8);
nodes.get('studioFavorite').onclick();assert(context.craftStudioState.favorites.includes(context.selectedRecipe.id));
context.recipeTab='processing';context.renderRecipeList();assert(nodes.get('recipeList').innerHTML.includes('746 matching'));
context.recipeSearch='flax';context.renderRecipeList();assert(nodes.get('recipeList').innerHTML.includes('Flax Fabric'));
context.craftStudioRender({...context.selectedRecipe,name:'<img src=x onerror=alert(1)>'},1);assert(nodes.get('craftDetail').innerHTML.includes('&lt;img'));assert(!nodes.get('craftDetail').innerHTML.includes('<img src=x'));

// Actual multilevel cooking and alchemy workflows, not a separate mock calculator.
for(const name of ['Balenos Meal','Elixir of Demihuman Hunt','Organic Feed','Kamasylvia Meal']){
 const r=recipes.find(r=>r.name===name);context.selectedRecipe=r;context.lastCraftAmount=100;context.craftStudioRender(r,100);
 nodes.get('workshopMake').onclick();const chain=context.craftStudioPlan(r,100);
 assert(chain.steps.length>2,name+' needs real intermediate stages');if(name==='Kamasylvia Meal')assert(chain.steps.length>20);
 assert(nodes.get('craftDetail').innerHTML.includes('Expected retained output value'));assert(nodes.get('craftDetail').innerHTML.includes('Priced cash ingredient budget'));
 nodes.get('workshopStartNext').onclick();assert.equal(started.r.id,chain.steps[0].recipeId);assert.equal(started.n,chain.steps[0].batches);
 const once=started;nodes.get('workshopStartNext').onclick();assert.equal(started,once,'same stage must not start duplicate timers');nodes.get('btnStartCraft').onclick();assert.equal(started,once,'main action must not skip intermediates');
 assert(nodes.get('craftDetail').innerHTML.includes('workshop-next'));assert(!nodes.get('craftDetail').controls.find(n=>n.dataset.section==='all-stages').open);assert(!nodes.get('craftDetail').controls.find(n=>n.dataset.section==='route-comparison').open);
 nodes.get('workshopSubstitutions').onclick();
 assert(chain.steps.at(-1).recipeId===r.id);assert(chain.steps.every(s=>s.inputs.length&&s.expected>=s.needed));
 assert(nodes.get('craftDetail').innerHTML.includes('Cash required'));assert(nodes.get('craftDetail').innerHTML.includes('Where your time and silver go'));
 let check=nodes.get('craftDetail').controls.find(n=>n.dataset.chainDone==='0');check.checked=true;check.onchange();
 assert.equal(context.craftStudioState.workshop.done.length,1);
 context.lastCraftAmount=101;context.craftStudioRender(r,101);assert.equal(context.craftStudioState.workshop.done.length,0,'changed requirements reset progress');
 nodes.get('workshopExport').onclick();assert(download[1].includes('STAGES'));assert(download[1].includes('/batch'));assert(download[1].includes('Expected quantities'));
 nodes.get('workshopBuy').onclick();assert.equal(context.craftStudioPlan(r,101).steps.length,1,'buy route must remove every intermediate');
}

assert(context.craftStudioPie([{label:'<img src=x>',value:1}],'Budget','silver').includes('&lt;img'));assert(!context.craftStudioPie([{label:'<img src=x>',value:1}],'Budget','silver').includes('<img'));

const nursery=recipes.find(r=>r.id==='recipe:820831:8dd94cf6d723');context.selectedRecipe=nursery;context.lastCraftAmount=100;context.craftStudioState.queue=[];
context.craftStudioState.carry={maximum:100,current:10,reserve:5,mode:'ingredients'};context.craftStudioRender(nursery,100);
assert(nodes.get('craftDetail').innerHTML.includes('crafts max'));assert(nodes.get('craftDetail').innerHTML.includes('772'));assert(nodes.get('craftDetail').innerHTML.includes('Grab extra'));
nodes.get('carryApply').onclick();assert.equal(context.lastCraftAmount,772);nodes.get('carryRank').onclick();assert.equal(context.recipeSort,'carryTime');assert(nodes.get('recipeList').innerHTML.includes('crafts / load'));
const ranked=recipes.filter(r=>r.type==='cooking').map(r=>({r,c:context.VisionCraft.carry(r,context.craftStudioCarrySettings(),context.craftStudioContext())})).sort((a,b)=>b.c.seconds-a.c.seconds||a.r.name.localeCompare(b.r.name));
assert.equal(nodes.get('recipeList').controls.find(n=>n.dataset.id&&n.dataset.id!=='durability_timer').dataset.id,ranked[0].r.id);
const previousQuote=context.craftStudioQuote;context.craftStudioQuote=()=>({price:100,stock:100000});context.craftStudioRender(nursery,772);
const routes=context.VisionCraft.downstream(nursery,Math.floor(context.craftStudioPlan(nursery,772).output),context.craftStudioContext(),{depth:2});const routeIndex=routes.nodes.findIndex(n=>n.batches>0&&n.level===1);assert(routeIndex>=0);
nodes.get('craftDetail').controls.find(n=>n.dataset.futureRoute===String(routeIndex)).onclick();const staged=context.craftStudioQueuePlans();assert(staged.length===2);assert.equal(staged[0].p.proceeds,0);assert(!staged[1].p.purchases.some(m=>m.itemId===nursery.itemId));assert(nodes.get('studioQueuePanel').innerHTML.includes('Modeled remaining planning stock'));
context.craftStudioQuote=previousQuote;

// The real subrecipe load controls start that stage, not the final recipe.
context.craftStudioState.carry={maximum:2700,current:0,reserve:0,mode:'ingredients',roundTo:100};
context.craftStudioChainRoute(nursery,true);context.craftStudioRender(nursery,100);
const riceStage=nodes.get('craftDetail').controls.find(n=>n.dataset.startLoad==='recipe:820815:79c52fba90af');assert(riceStage);
assert(nodes.get('craftDetail').innerHTML.includes('5,100 crafts max'));
riceStage.onclick();assert.equal(started.r.name,'Cooked Rice');assert.equal(started.n,5100);assert.equal(started.opts.craftPlan.itemId,820815);
context.activeTimers=[{status:'running',recipeId:started.r.id}];started=null;riceStage.onclick();assert.equal(started,null,'load control cannot duplicate an active timer');delete context.activeTimers;
const roundInput=nodes.get('craftDetail').controls.find(n=>n.dataset.carry==='roundTo');roundInput.onchange();assert.equal(context.craftStudioCarrySettings().roundTo,'100');

nodes.get('lineWiden').onclick();assert(context.craftStudioState.productionWide);assert(nodes.get('craftDetail').innerHTML.includes('production-line is-wide'));nodes.get('lineWiden').onclick();assert(!context.craftStudioState.productionWide);

// Edit one ingredient in the real final-product card: companions and target snap.
const sung=recipes.find(r=>r.id==='recipe:820833:5447701ae647');context.selectedRecipe=sung;context.lastCraftAmount=100;context.craftStudioRender(sung,100);
assert(nodes.get('craftDetail').innerHTML.indexOf('Your production line')<nodes.get('craftDetail').innerHTML.indexOf('EXPECTED NET PROFIT'));
assert(nodes.get('craftDetail').innerHTML.includes('Feeds Nurungji'));assert(nodes.get('craftDetail').innerHTML.includes('Feeds Sungnyung'));
let anchor=nodes.get('craftDetail').controls.find(n=>n.dataset.ratioRecipe===sung.id&&n.dataset.ratioItem==='820831');anchor.value='14000';anchor.oninput();
assert.equal(context.lastCraftAmount,7000);
assert.equal(nodes.get('craftDetail').controls.find(n=>n.dataset.ratioRecipe===sung.id&&n.dataset.ratioItem==='9059').value,'21000');
anchor=nodes.get('craftDetail').controls.find(n=>n.dataset.ratioRecipe===sung.id&&n.dataset.ratioItem==='9059');anchor.value='1000';anchor.oninput();assert.equal(context.lastCraftAmount,333);assert(nodes.get('craftDetail').innerHTML.includes('1 of the edited ingredient remain'));
anchor=nodes.get('craftDetail').controls.find(n=>n.dataset.ratioRecipe===sung.id&&n.dataset.ratioItem==='9059');anchor.onblur();assert.equal(anchor.value,'999');
anchor=nodes.get('craftDetail').controls.find(n=>n.dataset.ratioRecipe===sung.id&&n.dataset.ratioItem==='820831');anchor.value='140000';anchor.oninput();assert(nodes.get('craftDetail').innerHTML.includes('Does not fit'));
started=null;nodes.get('craftDetail').controls.find(n=>n.dataset.startLoad===sung.id).onclick();assert.equal(started,null,'overweight load cannot start via a stale button');
// Separate workspaces and starting-stock simulation exercise the shipped UI.
for(const id of ['craftWorkflows','craftPlanningPanel','craftSimulatorPanel','craftImperialPanel','craftTimersPanel','craftHistoryPanel','craftRecordedPanel','chainSimulator','craftTimerCount'])nodes.set(id,new Element());
nodes.get('craftWorkflows').innerHTML=['planner','simulator','imperial','timers'].map(mode=>'<button data-craft-workspace="'+mode+'"></button>').join('');
const scenarioWrites=[];context.localStorage.setItem=(key,value)=>scenarioWrites.push(key);
context.activeTimers=[{id:'preserved',status:'running',recipeId:sung.id}];
const untouched=JSON.stringify([context.craftStudioState,context.lastCraftAmount,context.selectedRecipe,context.activeTimers]);
context.craftSimulation={recipeId:sung.id,sourceId:820815,quantity:1000,stock:{}};context.craftWorkflowInit();
nodes.get('craftWorkflows').controls.find(n=>n.dataset.craftWorkspace==='simulator').onclick();assert(!nodes.get('craftSimulatorPanel').hidden);assert(nodes.get('craftPlanningPanel').hidden);assert(nodes.get('craftImperialPanel').hidden);assert(nodes.get('craftTimersPanel').hidden);
nodes.get('simulationRun').onclick();assert.equal(context.craftSimulationResult.batches,500);assert(nodes.get('chainSimulator').innerHTML.includes('Nurungji'));assert(nodes.get('chainSimulator').innerHTML.includes('Follow the whole production line'));
assert(!nodes.get('simulationGraphBody').innerHTML);nodes.get('simulationGraphs').open=true;nodes.get('simulationGraphs').ontoggle();assert(nodes.get('simulationGraphBody').innerHTML.includes('role="img"'));
nodes.get('simulationExport').onclick();assert(download[0].endsWith('production-simulation.txt'));assert(download[1].includes('ISOLATED PRODUCTION SIMULATION'));
nodes.get('simulationQuantity').oninput({target:{value:'2000'}});assert.equal(context.craftSimulationResult,null);assert(nodes.get('simulationResults').innerHTML.includes('Scenario changed'));assert(nodes.get('simulationExport').disabled);
nodes.get('simulationRun').onclick();assert.equal(context.craftSimulationResult.batches,1000);
assert.equal(JSON.stringify([context.craftStudioState,context.lastCraftAmount,context.selectedRecipe,context.activeTimers]),untouched,'simulator must leave real planning/timer state unchanged');
assert(scenarioWrites.every(key=>['vision.craft.simulator.v1','vision.craft.workspace.v1'].includes(key)),'simulator may write only its own state/workspace keys');
nodes.get('craftWorkflows').controls.find(n=>n.dataset.craftWorkspace==='timers').onclick();assert(!nodes.get('craftTimersPanel').hidden);assert(!nodes.get('craftHistoryPanel').hidden);assert(nodes.get('craftSimulatorPanel').hidden);assert.equal(nodes.get('craftTimerCount').textContent,' (1)');
nodes.get('craftWorkflows').controls.find(n=>n.dataset.craftWorkspace==='imperial').onclick();assert(!nodes.get('craftImperialPanel').hidden);assert(nodes.get('craftTimersPanel').hidden);assert(nodes.get('craftRecordedPanel').hidden);
context.craftWorkflowSet('planner');assert(!nodes.get('craftPlanningPanel').hidden);assert(nodes.get('craftImperialPanel').hidden);delete context.activeTimers;

// Optional all-card overview mirrors the large meal reference without changing routes.
const meal=recipes.find(r=>r.name==='Balenos Meal');context.selectedRecipe=meal;context.lastCraftAmount=100000;context.craftStudioState.productionOverview=false;
context.craftStudioRender(meal,100000);const makeBefore=JSON.stringify(context.craftStudioState.make),stockBefore=JSON.stringify(context.craftStudioState.inventory);
assert.equal((nodes.get('craftDetail').innerHTML.match(/class="load-card"/g)||[]).length,1);
nodes.get('lineOverview').onclick();const mealMap=context.VisionCraft.productionGraph(meal,context.craftStudioContext());
assert.equal((nodes.get('craftDetail').innerHTML.match(/class="load-card"/g)||[]).length,mealMap.steps.length);assert(nodes.get('craftDetail').innerHTML.includes('Whole-chain ingredient tree'));assert(nodes.get('craftDetail').innerHTML.includes('Full make preview totals'));
assert.equal(JSON.stringify(context.craftStudioState.make),makeBefore);assert.equal(JSON.stringify(context.craftStudioState.inventory),stockBefore);
nodes.get('lineOverview').onclick();assert(!context.craftStudioState.productionOverview);assert.equal((nodes.get('craftDetail').innerHTML.match(/class="load-card"/g)||[]).length,1);

// Map-first planner: real downstream goals, clickable nodes and a matching timeline.
const wine=recipes.find(r=>r.name==='Fruit Wine'),serendia=recipes.find(r=>r.name==='Serendia Meal');context.selectedRecipe=wine;context.lastCraftAmount=100;context.craftStudioRender(wine,100);
assert(nodes.get('craftDetail').innerHTML.includes('From ingredient to finished product'));assert(!nodes.get('craftDetail').controls.find(n=>n.dataset.section==='single-recipe').open);
const routeState=JSON.stringify([context.craftStudioState.make,context.craftStudioState.choices,context.craftStudioState.inventory]);
assert(nodes.get('roadGoal').innerHTML.includes(serendia.id));assert(!nodes.get('roadGoal').innerHTML.includes('value="'+meal.id+'"'));
nodes.get('roadGoal').onchange({target:{value:serendia.id}});assert.equal(context.craftRoadLive.goal.id,serendia.id);assert(nodes.get('productionRoadmap').innerHTML.includes('Production timeline'));
assert(context.craftRoadLive.timeline.rows.some(s=>s.recipeId===wine.id));assert.equal(context.craftRoadLive.timeline.rows.at(-1).recipeId,serendia.id);
const focusLink=nodes.get('productionRoadmap').controls.find(n=>n.dataset.roadFocus===serendia.id);focusLink.onclick({preventDefault(){}});assert.equal(context.craftRoadLive.focus,serendia.id);
nodes.get('roadCount').onchange({target:{value:'200'}});assert.equal(context.craftRoadLive.count,200);assert.equal(context.lastCraftAmount,100,'future goal quantities do not overwrite the selected ingredient packing target');
assert.equal(JSON.stringify([context.craftStudioState.make,context.craftStudioState.choices,context.craftStudioState.inventory]),routeState,'viewing a full map must not adopt a make route or consume stock');
nodes.get('roadExport').onclick();const exported=JSON.parse(download[1]);assert.equal(exported.goalRecipeId,serendia.id);assert.equal(exported.estimated,true);assert(exported.stages.some(s=>s.recipeId===wine.id));
context.activeTimers=[];started=null;nodes.get('roadStart').onclick();assert.equal(started.r.id,serendia.id);assert.equal(started.n,200);assert.equal(context.craftWorkflow,'timers');
context.activeTimers=[{status:'running',recipeId:serendia.id}];started=null;nodes.get('roadStart').onclick();assert.equal(started,null,'do not duplicate a running stage timer');delete context.activeTimers;

// Cooking/alchemy remember independent tool/ingredient/hybrid stopping rules.
context.selectedRecipe=wine;context.lastCraftAmount=100;context.craftRoadTool=null;context.craftRoadState.runModes={};context.craftRoadState.toolFallback={};context.craftStudioRender(wine,100);
assert.equal(context.craftRoadLive.limit.mode,'tool');assert(!context.craftRoadLive.limit.available);assert.equal(context.craftRoadLive.timeline.rows.length,0);
nodes.get('roadToolFallback').onchange({target:{value:'10'}});assert.equal(context.craftRoadLive.limit.batches,10);assert.equal(context.craftRoadLive.timeline.rows.find(s=>s.recipeId===wine.id).batches,10);
const runStock={};for(const m of context.craftRoadInputs(wine,context.craftRoadLive.ctx))runStock[m.itemId]=m.qty*5;context.craftRoadState.runStock[wine.id]=runStock;
nodes.get('roadRunMode').onchange({target:{value:'ingredients'}});assert.equal(context.craftRoadLive.limit.batches,5);assert.equal(context.craftRoadLive.timeline.rows.find(s=>s.recipeId===wine.id).batches,5);
nodes.get('roadRunMode').onchange({target:{value:'hybrid'}});assert.equal(context.craftRoadLive.limit.batches,5);assert.equal(context.craftRoadMode(recipes.find(r=>r.type==='alchemy')),'tool');
const stamp=Date.now()+100;context.craftRoadAcceptToolReading({signal:1,current:4,maximum:100,seconds_per_craft:1,observed_at:stamp/1000,instance_id:'test',session_id:'new-tool',source:'ocr'});assert.equal(context.craftRoadToolNow('cooking',stamp+2000).remaining,2);assert.equal(context.craftRoadLive.limit.batches,4);assert.equal(context.craftRoadLive.timeline.rows.find(s=>s.recipeId===wine.id).batches,4);
const currentLink=nodes.get('productionRoadmap').controls.find(n=>n.dataset.roadFocus===wine.id);currentLink.onclick({preventDefault(){}});started=null;nodes.get('roadStart').onclick();assert.equal(started.r.id,wine.id);assert.equal(started.n,4);assert.equal(started.opts.craftPlan.seconds,1);assert.equal(started.r.secPerBatch,1);
for(const id of Object.keys(runStock))runStock[id]=0;context.craftRoadState.runStock[wine.id]=runStock;nodes.get('roadApplyLimit').onclick();assert.equal(context.craftRoadLive.limit.batches,0);assert.equal(context.craftRoadLive.timeline.rows.length,0);
let rebuilds=0;const priorRefresh=context.craftRoadToolRefresh;context.craftRoadToolRefresh=()=>{rebuilds++;priorRefresh();};context.craftRoadAcceptToolReading({signal:2,current:4,maximum:100,seconds_per_craft:1,observed_at:stamp/1000,instance_id:'test',session_id:'new-tool',source:'ocr'});assert.equal(rebuilds,0,'ordinary tool ticks must not replan the whole map');

console.log('Shipped Crafting UI: rendering, target conversion, queue, export, timer linkage, tax, favorites, processing search and escaping passed.');

// Whole-route pricing: fixed choices, bounded requests and offline retry recovery.
(async()=>{
 const load=context.craftStudioLoadPrices,vm=context.craftRoadLive,ids=context.craftStudioIds(vm.goal,vm.ctx);assert(ids.includes(wine.itemId));assert(ids.includes(serendia.itemId));assert(ids.length<=256);
 context.bridgeSelectedOrigin=null;const offline=await load(vm.goal,false,vm.ctx);assert.equal(offline.ok,false);await Promise.resolve();assert.equal(context.craftStudioPricePending.size,0);
 let requests=0;context.bridgeSelectedOrigin='http://127.0.0.1:7288';context.visionRememberMarketQuotes=()=>{};context.fetch=async(url,opts)=>{requests++;assert(url.endsWith('/craft-quotes'));const body=JSON.parse(opts.body);assert(body.ids.length<=64);assert.equal(body.region,'NA');return {ok:true,json:async()=>({items:[]})};};
 const online=await load(vm.goal,false,vm.ctx);assert(online.ok);assert(requests>0);const before=requests;assert((await load(vm.goal,false,vm.ctx)).cached);assert.equal(requests,before);
 console.log('Whole-line price requests: route IDs, 64-item batches, offline recovery and shared cache passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
