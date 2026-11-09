/* Market and Crafting use the same item IDs, recipe graph and regional quotes. */
var craftMarketItemId=null,craftMarketRecipeId=null,craftMarketQuery='';

function craftMarketOpen(itemId,recipeId=null){
 craftMarketItemId=itemId;craftMarketRecipeId=recipeId;craftMarketQuery='';
 showView('market');
 document.getElementById('craftMarketDesk')?.scrollIntoView({block:'start'});
}

function craftMarketCatalog(){
 var catalog=new Map(Object.values(VISION_CRAFT_DATA.items).map(item=>[item.id,item]));
 for(var item of [...hotItems,...currentItems]){
  if(Number.isInteger(item.id)&&!catalog.has(item.id))catalog.set(item.id,item);
 }
 return catalog;
}

function craftMarketMatches(catalog,query){
 var normalized=VisionCraft.key(query);
 if(!normalized)return [];
 var exactId=/^\d+$/.test(query.trim())?Number(query):null;
 if(exactId!==null)return catalog.has(exactId)?[catalog.get(exactId)]:[];
 return [...catalog.values()].filter(item=>VisionCraft.key(item.name).includes(normalized))
  .sort((a,b)=>Number(VisionCraft.key(b.name).startsWith(normalized))-Number(VisionCraft.key(a.name).startsWith(normalized))||a.name.localeCompare(b.name)||a.id-b.id).slice(0,20);
}

function craftMarketInspect(item){
 if(!item)return '<p class="studio-muted">Choose a result to inspect price, stock, and recipes.</p>';
 var esc=visionEscape,quote=craftStudioQuote(item.name,item.id),links=VisionRecipes.uses(item.id,RECIPES,VISION_CRAFT_DATA);
 var number=n=>Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:2}):'Unknown',stamp=quote?.updatedAt||quote?.updated_at;
 var observed=stamp&&!Number.isNaN(Date.parse(stamp))?new Date(stamp).toLocaleString():null;
 var comparisons=links.producedBy.filter(row=>row.kind==='main').slice(0,6).map(({recipe})=>{
  var model=craftStudioPlan(recipe,100),unit=model.cost===null||!model.output?null:model.cost/model.output;
  return '<li><button type="button" data-market-recipe="'+esc(recipe.id)+'">'+esc(recipe.name)+'</button><small>'+esc((recipe.method||recipe.type).replaceAll('_',' '))+
   ' · '+craftStudioMoney(unit)+' make / item'+(quote&&unit!==null?' · '+craftStudioMoney(Math.abs(quote.price-unit))+' '+(unit<=quote.price?'below':'above')+' buy quote':'')+'</small></li>';
 });

 function recipes(rows,label){
  return '<details'+(rows.length&&rows.length<=6?' open':'')+'><summary>'+label+' · '+rows.length+'</summary><ul class="market-recipe-links">'+rows.map(({recipe,kind,slots})=>
   '<li><button type="button" data-market-recipe="'+esc(recipe.id)+'">'+esc(recipe.name)+'</button><small>'+esc((recipe.method||recipe.type).replaceAll('_',' '))+
   (kind?' · '+esc(kind)+' output':slots?' · '+slots.reduce((sum,slot)=>sum+slot.quantity,0)+' per craft'+(slots.some(slot=>slot.alternative)?' · substitution':''):'')+'</small></li>').join('')+'</ul></details>';
 }
 return '<h2>'+esc(item.name)+'</h2><p class="studio-muted">Item '+item.id+' · '+esc(String(region).toUpperCase())+'</p>'+
  '<dl class="market-facts"><div><dt>'+(quote?.price_basis==='market_reference'?'Reference quote':'Base quote')+'</dt><dd>'+number(quote?.price)+'</dd></div><div><dt>Listed stock</dt><dd>'+number(quote?.stock)+'</dd></div><div><dt>14-day daily volume</dt><dd>'+number(quote?.daily_volume)+'</dd></div>'+
  (item.npcBuy>0?'<div><dt>NPC buy price</dt><dd>'+number(item.npcBuy)+'</dd></div>':'')+'</dl>'+
  '<p class="studio-muted">'+esc(quote?.source||'No regional quote')+(observed?' · '+esc(observed):'')+'</p>'+
  '<button type="button" class="btn-secondary" data-market-refresh="'+item.id+'">Refresh item quote</button>'+
  (comparisons.length?'<details open><summary>Compare making vs buying</summary><p class="studio-muted">Modeled unit cost uses 100 batches, saved inputs and expected output. Comparison excludes sale tax and rare proceeds.</p><ul class="market-recipe-links">'+comparisons.join('')+'</ul></details>':'')+
  recipes(links.producedBy,'How to make it')+recipes(links.usedBy,'Recipes that use it');
}

function craftMarketBasket(recipe,plan){
 if(!recipe)return '<h2>Shopping basket</h2><p class="studio-muted">Open a recipe’s market basket to see shortages from your saved plan.</p><button class="btn-secondary" data-market-open-craft>Browse recipes</button>';
 var esc=visionEscape,quote=craftStudioQuote(recipe.name,recipe.itemId),volume=quote?.daily_volume;
 var days=Number.isFinite(volume)&&volume>0?plan.output/volume:null;
 var rows=plan.purchases.map(item=>{
  var market=item.basis!=='NPC purchase',gap=market&&Number.isFinite(item.stock)?Math.max(0,item.quantity-item.stock):null;
  return '<tr><th scope="row"><button class="market-inline" data-market-item="'+item.itemId+'">'+esc(item.name)+'</button></th><td>'+item.quantity.toLocaleString()+'</td><td>'+craftStudioMoney(item.unit)+'</td><td>'+esc(item.basis)+'</td><td>'+(market?(gap===null?'Unknown':gap.toLocaleString()):'NPC')+'</td><td>'+craftStudioMoney(item.unit===null?null:item.quantity*item.unit)+'</td></tr>';
 }).join('');
 return '<div class="market-basket-heading"><div><small>CRAFT PLAN</small><h2>'+esc(recipe.name)+'</h2></div><button class="btn-secondary" data-market-recipe="'+esc(recipe.id)+'">Back to recipe</button></div>'+
  '<p>'+plan.count.toLocaleString()+' batches · '+fmtTime(plan.seconds)+' production time · '+craftStudioMoney(plan.perHour)+' net / hour</p>'+
  (days===null?'':'<p class="studio-muted">Expected output equals '+days.toLocaleString(undefined,{maximumFractionDigits:2})+' days of average market-wide sales. Your fills may differ.</p>')+
  '<p><strong>'+craftStudioMoney(plan.cash)+'</strong> silver to prepare after owned stock and selected make/buy routes.</p>'+
  '<button class="btn-secondary" data-market-refresh-basket>Refresh basket quotes</button>'+
  (rows?'<div class="studio-table-wrap"><table><thead><tr><th>Item</th><th>Need</th><th>Unit price</th><th>Source</th><th>Stock short</th><th>Cash</th></tr></thead><tbody>'+rows+'</tbody></table></div>':'<p>No purchases required by this plan.</p>')+
  '<p class="studio-muted">Stock compares required quantity with quoted listings. Buy orders, fills, and actual sale price are separate.</p>';
}

function craftMarketRender(){
 var host=document.getElementById('craftMarketDesk');if(!host)return;
 var esc=visionEscape,catalog=craftMarketCatalog(),item=catalog.get(craftMarketItemId);
 var recipe=RECIPES.find(r=>r.id===craftMarketRecipeId),plan=recipe?craftStudioPlan(recipe,lastCraftAmount||1):null;
 host.innerHTML='<header class="market-desk-header"><div><small>VISION / MARKET INTELLIGENCE</small><h1>Market workbench</h1><p>Look up an ingredient, find what makes it, and price your production line.</p></div><b>'+esc(String(region).toUpperCase())+'</b></header>'+
  '<div class="market-desk-grid"><section class="market-desk-panel"><form id="marketItemSearch"><label for="marketItemQuery">Item name or exact ID</label><div><input id="marketItemQuery" type="search" value="'+esc(craftMarketQuery)+'" placeholder="Wheat Flour, Balenos Meal, 9601"><button class="btn-secondary" type="submit">Find</button></div></form>'+
  '<div id="marketItemResults"></div><p id="marketDeskStatus" role="status"></p>'+craftMarketInspect(item)+'</section>'+
  '<section class="market-desk-panel">'+craftMarketBasket(recipe,plan)+'</section></div>';
 var results=host.querySelector('#marketItemResults'),input=host.querySelector('#marketItemQuery');
 function search(){
  craftMarketQuery=input.value;
  var matches=craftMarketMatches(catalog,craftMarketQuery);
  results.innerHTML=matches.map(row=>'<button type="button" data-market-item="'+row.id+'">'+esc(row.name)+' <small>#'+row.id+'</small></button>').join('')||
   (craftMarketQuery.trim()?'<p class="studio-muted">No matching item in the crafting catalog or loaded market categories.</p>':'');
 }
 input.oninput=search;
 host.querySelector('#marketItemSearch').onsubmit=event=>{
  event.preventDefault();search();
  var hits=craftMarketMatches(catalog,craftMarketQuery);
  if(hits.length===1){craftMarketItemId=hits[0].id;craftMarketRender();}
 };
 search();
 host.onclick=async event=>{
  var button=event.target.closest('button');if(!button)return;
  if(button.hasAttribute('data-market-open-craft')){showView('craft');craftWorkflowSet('planner');return;}
  if(button.dataset.marketRecipe){showView('craft');craftWorkflowSet('planner');selectRecipe(button.dataset.marketRecipe);return;}
  if(button.dataset.marketItem){craftMarketItemId=Number(button.dataset.marketItem);craftMarketRender();return;}
  var ids=button.dataset.marketRefresh?[Number(button.dataset.marketRefresh)]:
   button.hasAttribute('data-market-refresh-basket')&&recipe?craftStudioIds(recipe):null;
  if(!ids)return;
  var label=host.querySelector('#marketDeskStatus');
  label.textContent='Refreshing exact regional quotes…';button.disabled=true;
  var result=await craftStudioRequestQuotes(ids,true);
  if(currentView!=='market'||host.querySelector('#marketDeskStatus')!==label)return;
  craftMarketRender();
  host.querySelector('#marketDeskStatus').textContent=result.ok?'Quote lookup complete. Missing prices stay unknown.':result.message;
 };
}
