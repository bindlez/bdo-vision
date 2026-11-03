/* Isolated what-if scenarios and separate Crafting workspaces. No OCR or timers. */
var craftWorkflow='planner';
try{var storedWorkflow=localStorage.getItem('vision.craft.workspace.v1');if(['planner','simulator','imperial','timers'].includes(storedWorkflow))craftWorkflow=storedWorkflow;}catch(e){}
var craftSimulation=(function(){try{var s=JSON.parse(localStorage.getItem('vision.craft.simulator.v1'));return s&&typeof s==='object'&&!Array.isArray(s)?s:{};}catch(e){return {};}})();
if(!craftSimulation.stock||typeof craftSimulation.stock!=='object'||Array.isArray(craftSimulation.stock))craftSimulation.stock={};
var craftSimulationResult=null,craftSimulationAt=0;

function craftWorkflowInit(){
 var nav=document.getElementById('craftWorkflows');if(!nav||nav.dataset.bound)return;
 nav.dataset.bound='yes';nav.querySelectorAll('[data-craft-workspace]').forEach(button=>button.onclick=()=>craftWorkflowSet(button.dataset.craftWorkspace));
 craftWorkflowSet(craftWorkflow);
}
function craftWorkflowSet(mode){
 if(!['planner','simulator','imperial','timers'].includes(mode))return;
 craftWorkflow=mode;try{localStorage.setItem('vision.craft.workspace.v1',mode);}catch(e){}
 for(var [id,owner] of [['craftPlanningPanel','planner'],['craftSimulatorPanel','simulator'],['craftImperialPanel','imperial'],['craftTimersPanel','timers'],['craftHistoryPanel','timers']]){var el=document.getElementById(id);if(el)el.hidden=owner!==mode;}
 var recorded=document.getElementById('craftRecordedPanel');if(recorded)recorded.hidden=!['planner','timers'].includes(mode);
 var nav=document.getElementById('craftWorkflows');if(nav)nav.querySelectorAll('[data-craft-workspace]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.craftWorkspace===mode)));
 if(mode==='simulator')craftSimulatorRender();
 if(mode==='imperial')craftImperialRender();
 if(mode==='timers'){if(typeof renderActiveTimers==='function')renderActiveTimers();if(typeof renderHistory==='function')renderHistory();}
 craftWorkflowBadge();
}
function craftWorkflowBadge(){
 var count=typeof activeTimers==='undefined'?0:activeTimers.filter(t=>t.status==='running'||t.status==='paused').length;
 var badge=document.getElementById('craftTimerCount');if(badge)badge.textContent=count?' ('+count+')':'';
}
function craftSimulatorSave(){try{localStorage.setItem('vision.craft.simulator.v1',JSON.stringify(craftSimulation));}catch(e){toast('Scenario storage','Export this simulation to keep a copy.',false);}}
function craftSimulatorChanged(message){
 craftSimulationResult=null;craftSimulatorSave();var results=document.getElementById('simulationResults');if(results)results.innerHTML='<p role="status" class="studio-muted">'+visionEscape(message||'Scenario changed. Run the simulation to update the results.')+'</p>';
 var exportButton=document.getElementById('simulationExport');if(exportButton)exportButton.disabled=true;
}
function craftSimulatorRecipe(){
 return RECIPES.find(r=>r.id===craftSimulation.recipeId&&craftSimulatorTarget(r))||RECIPES.find(r=>r.id===selectedRecipe?.id&&craftSimulatorTarget(r))||RECIPES.find(r=>r.type==='cooking');
}
function craftSimulatorTarget(r){return r.mats?.length&&!/^imperial_/.test(r.method||'')&&(r.type!=='processing'||!!r.method);}
function craftSimulatorRender(){
 var host=document.getElementById('chainSimulator');if(!host)return;
 var esc=visionEscape,recipe=craftSimulatorRecipe();craftSimulation.recipeId=recipe.id;
 var type=['cooking','alchemy','processing'].includes(craftSimulation.type)?craftSimulation.type:recipe.type;
 var search=String(craftSimulation.search||''),matching=RECIPES.filter(r=>r.type===type&&craftSimulatorTarget(r)&&VisionCraft.key(r.name).includes(VisionCraft.key(search))).slice(0,120);
 if(!matching.some(r=>r.id===recipe.id))matching.unshift(recipe);
 var graph=VisionCraft.productionGraph(recipe,craftStudioContext()),inputIds=[...new Set(graph.edges.filter(e=>e.kind==='input').map(e=>Number(e.from.slice(5))))];
 var items=inputIds.map(id=>({id,name:VISION_CRAFT_DATA.items[id]?.name||String(id)})).sort((a,b)=>a.name.localeCompare(b.name));
 if(!inputIds.includes(Number(craftSimulation.sourceId)))craftSimulation.sourceId=items[0]?.id;
 if(craftSimulation.quantity==null)craftSimulation.quantity=1000;
 host.innerHTML='<div class="studio-eyebrow">SEPARATE WHAT-IF SCENARIO / NO LIVE INVENTORY CHANGES</div><h3>What can these ingredients become?</h3><p class="studio-muted">Choose the final product, then start anywhere along its ingredient chain: a raw material or a ready-made intermediate. This scenario has its own stock and never changes your packing cards, queue or running timers.</p><div class="studio-fields"><label class="studio-field">Recipe category<select id="simulationType">'+['cooking','alchemy','processing'].map(t=>'<option value="'+t+'" '+(t===type?'selected':'')+'>'+t+'</option>').join('')+'</select></label><label class="studio-field">Find final product<input id="simulationSearch" type="search" value="'+esc(search)+'" placeholder="Meal, elixir, processing product"></label><label class="studio-field">Final recipe / variant<select id="simulationRecipe">'+matching.map(r=>'<option value="'+esc(r.id)+'" '+(r.id===recipe.id?'selected':'')+'>'+esc(r.name+' / '+r.mats.map(m=>m.qty+' '+m.name).join(', '))+'</option>').join('')+'</select></label><label class="studio-field">Starting ingredient<select id="simulationSource">'+items.map(m=>'<option value="'+m.id+'" '+(m.id===Number(craftSimulation.sourceId)?'selected':'')+'>'+esc(m.name)+'</option>').join('')+'</select></label><label class="studio-field">Total starting ingredient<input id="simulationQuantity" type="number" min="1" max="1000000000000" step="1" value="'+esc(craftSimulation.quantity)+'"></label><label class="studio-field">Companion ingredients<select id="simulationMode"><option value="buy" '+(!craftSimulation.stockOnly?'selected':'')+'>Buy missing companions</option><option value="stock" '+(craftSimulation.stockOnly?'selected':'')+'>Use only the stock entered below</option></select></label></div><p class="studio-muted">At most 120 matching variants are listed; search to narrow them. The starting ingredient is a fixed supply: it is never bought or manufactured to extend the run.</p><details data-section="simulation-stock"><summary>Other ingredients already available / '+items.filter(m=>m.id!==Number(craftSimulation.sourceId)&&Number(craftSimulation.stock[m.id])>0).length+' with stock</summary><div class="simulation-stock">'+items.filter(m=>m.id!==Number(craftSimulation.sourceId)).map(m=>'<label class="studio-field">'+esc(m.name)+'<input data-simulation-stock="'+m.id+'" type="number" min="0" max="1000000000000" step="1" value="'+esc(craftSimulation.stock[m.id]??0)+'"></label>').join('')+'</div><p class="studio-muted">Only this scenario’s entered quantities count. Bag/planner stock and recorded loot are not imported. Stock is allocated once across shared branches.</p></details><div class="studio-actions"><button id="simulationRun" class="btn-primary">Simulate entire line</button><button id="simulationExport" class="btn-secondary" '+(!craftSimulationResult?'disabled':'')+'>Export simulation</button></div><div id="simulationResults">'+(craftSimulationResult?craftSimulatorResults(craftSimulationResult,recipe):'<p role="status" class="studio-muted">Ready. Nothing runs until you choose Simulate.</p>')+'</div>';
 document.getElementById('simulationType').onchange=e=>{craftSimulation.type=e.target.value;craftSimulation.search='';craftSimulatorChanged();craftSimulatorRender();};
 document.getElementById('simulationSearch').oninput=e=>{var value=e.target.value;craftSimulation.search=value;craftSimulatorChanged();craftSimulatorRender();var input=document.getElementById('simulationSearch');input.focus();input.setSelectionRange?.(value.length,value.length);};
 document.getElementById('simulationRecipe').onchange=e=>{craftSimulation.recipeId=e.target.value;delete craftSimulation.sourceId;craftSimulatorChanged();craftSimulatorRender();};
 document.getElementById('simulationSource').onchange=e=>{craftSimulation.sourceId=Number(e.target.value);craftSimulatorChanged();craftSimulatorRender();};
 document.getElementById('simulationQuantity').oninput=e=>{craftSimulation.quantity=e.target.value;craftSimulatorChanged();};
 document.getElementById('simulationMode').onchange=e=>{craftSimulation.stockOnly=e.target.value==='stock';craftSimulatorChanged();};
 host.querySelectorAll('[data-simulation-stock]').forEach(input=>input.oninput=()=>{craftSimulation.stock[input.dataset.simulationStock]=input.value;craftSimulatorChanged();});
 document.getElementById('simulationRun').onclick=()=>{
  try{craftSimulationResult=VisionCraft.simulateProduction(recipe,craftSimulation,craftStudioContext());craftSimulationAt=Date.now();craftSimulatorSave();craftSimulatorRender();}
  catch(e){craftSimulationResult=null;document.getElementById('simulationResults').innerHTML='<p role="alert" class="studio-warning">'+esc(e.message)+'</p>';document.getElementById('simulationExport').disabled=true;}
 };
 document.getElementById('simulationExport').onclick=()=>craftSimulatorExport(recipe);
 var graphs=document.getElementById('simulationGraphs');if(graphs&&craftSimulationResult?.plan)graphs.ontoggle=()=>{if(!graphs.open)return;var p=craftSimulationResult.plan;document.getElementById('simulationGraphBody').innerHTML='<div class="workshop-pies">'+craftStudioPie(p.steps.map(s=>({label:s.name,value:s.seconds})),'Time by production stage','seconds')+craftStudioPie(p.purchases.filter(m=>m.unit!==null).map(m=>({label:m.name,value:m.quantity*m.unit})),'Cash for missing ingredients','silver')+'</div>'+craftStudioGraph(p.steps.reduce((points,s)=>{points.push([points.length,points.at(-1)[1]+s.seconds]);return points;},[[0,0]]),'Cumulative modeled production seconds by completed stage');};
}
function craftSimulatorResults(result,recipe){
 var esc=visionEscape,p=result.plan,number=n=>Number(n).toLocaleString(undefined,{maximumFractionDigits:3});
 if(!p)return '<p class="studio-warning" role="status">Not enough stock for one modeled final craft. Enter companion stock or choose Buy missing companions.</p>'+craftSimulatorShortfalls(result.shortfalls);
 var finalOutputs=p.outputs.filter(o=>['main','rare'].includes(o.kind)),valued=finalOutputs.every(o=>o.net!=null),potential=valued?finalOutputs.reduce((sum,o)=>sum+o.net,0):null;
 var outputMap=new Map();for(var o of [...p.outputs,...result.sideOutputs]){var prev=outputMap.get(o.itemId);outputMap.set(o.itemId,prev?{...prev,quantity:prev.quantity+o.quantity,kind:prev.kind.includes(o.kind)?prev.kind:prev.kind+' / '+o.kind}:{...o});}
 var outputs=[...outputMap.values()],remaining=result.remaining.filter(m=>m.quantity>0);
 return '<p class="studio-muted" role="status">Scenario calculated '+esc(new Date(craftSimulationAt).toLocaleString())+' / '+(result.stockOnly?'entered stock only':'starting stock + companion purchases')+'. Saved recipe/mastery/substitution assumptions; expected yields, not guaranteed production.'+(result.capped?' Calculation cap reached; reduce the scenario.':'')+'</p><div class="studio-kpis"><div><small>MODELED FINAL CRAFTS</small><strong>'+number(result.batches)+'</strong></div><div><small>EXPECTED FINAL MAIN ITEMS</small><strong>'+number(p.output)+'</strong></div><div><small>PRODUCTION TIME / ALL STAGES</small><strong>'+fmtTime(p.seconds)+'</strong></div><div><small>CASH FOR MISSING COMPANIONS</small><strong>'+craftStudioMoney(p.cash)+'</strong></div></div><h4>Follow the whole production line</h4><ol class="simulation-stages">'+p.steps.map(s=>'<li><b>'+esc(s.name)+'</b><span>'+number(s.batches)+' crafts / '+fmtTime(s.seconds)+' / '+number(s.expected)+' expected main or equivalent units</span><p>'+s.inputs.map(m=>esc(m.name)+' x '+number(m.quantity)).join(' + ')+'</p></li>').join('')+'</ol><details open><summary>Expected products and kept extras</summary><div class="studio-table-wrap"><table><thead><tr><th>Product</th><th>Expected units</th><th>Type</th></tr></thead><tbody>'+outputs.map(o=>'<tr><td>'+esc(o.name)+'</td><td>'+number(o.quantity)+'</td><td>'+esc(o.kind)+'</td></tr>').join('')+'</tbody></table></div><p class="studio-muted">Main intermediate output feeds its consumers. Unused main surplus is in remaining stock. Intermediate rare procs used as normal equivalents are not also listed as kept. Random alchemy extras are excluded; quantities are model averages.</p></details><details><summary>Purchases, leftovers and one-more-craft limits</summary><h4>Buy missing companions</h4>'+(p.purchases.length?p.purchases.map(m=>'<p>'+esc(m.name)+' x '+number(m.quantity)+' / '+craftStudioMoney(m.unit===null?null:m.quantity*m.unit)+' / '+esc(m.basis)+'</p>').join(''):'<p>No purchases needed.</p>')+'<h4>Remaining scenario stock</h4>'+(remaining.length?remaining.map(m=>'<p>'+esc(m.name)+' x '+number(m.quantity)+'</p>').join(''):'<p>No entered/input stock remains.</p>')+'<h4>Missing for one more final craft</h4>'+craftSimulatorShortfalls(result.shortfalls)+'</details><details id="simulationGraphs"><summary>Time, costs and graphs</summary><div id="simulationGraphBody"></div><p>Potential final main/rare sale value after configured deductions: '+craftStudioMoney(potential)+'. Economic input value (including starting stock): '+craftStudioMoney(p.cost)+'. Potential difference: '+craftStudioMoney(potential===null||p.cost===null?null:potential-p.cost)+'. Kept byproducts, intermediate surplus and side rares receive no silver credit here. Unknown prices stay unvalued.</p></details><p class="studio-muted">This simulates quantities/time using expected yields. It does not simulate one bag across every stage, LT restocks, market stock reservations, inventory slots or travel. Use packing cards separately for LT. No inventory/loot/timer changes or gameplay commands.</p>';
}
function craftSimulatorShortfalls(rows){return rows?.length?rows.map(m=>'<p>'+visionEscape(m.name)+' x '+Number(m.quantity).toLocaleString(undefined,{maximumFractionDigits:3})+' missing</p>').join(''):'<p>No further limiting input within the calculation cap.</p>';}
function craftSimulatorExport(recipe){
 var r=craftSimulationResult;if(!r)return;
 var text='BDO Vision / ISOLATED PRODUCTION SIMULATION\n'+recipe.name+'\n'+new Date(craftSimulationAt).toISOString()+'\nExpected yields, not verified inventory or loot.\nStarting stock:\n'+r.inputs.map(m=>m.name+' x '+m.quantity).join('\n');
 if(r.plan)text+='\nSTAGES\n'+r.plan.steps.map(s=>s.name+': '+s.batches+' crafts; '+s.inputs.map(m=>m.name+' x '+m.quantity).join(' + ')).join('\n')+'\nBUY\n'+r.plan.purchases.map(m=>m.name+' x '+m.quantity).join('\n')+'\nREMAINING\n'+r.remaining.filter(m=>m.quantity>0).map(m=>m.name+' x '+m.quantity).join('\n');
 intelDownload('bdo-vision-production-simulation.txt',text,'text/plain');
}

// Launcher shortcuts land in the website-owned workspace directly.
if(typeof window.addEventListener==='function'){
 var craftWorkspaceRoute=()=>{if(location.hash==='#imperial'){showView('craft');craftWorkflowSet('imperial');}};
 window.addEventListener('hashchange',craftWorkspaceRoute);window.addEventListener('load',craftWorkspaceRoute);
}
