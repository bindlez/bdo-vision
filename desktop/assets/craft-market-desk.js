/* Market and Crafting use the same item IDs, recipe graph and regional quotes. */
var craftMarketItemId=null,craftMarketRecipeId=null,craftMarketQuery='';

var craftMarketHistory=new Map(),craftMarketFullCatalog=null,craftMarketCatalogRequest=null;
var craftMarketSearchIndex=new WeakMap();

function craftMarketLoadCatalog(){
 if(craftMarketFullCatalog)return Promise.resolve(craftMarketFullCatalog.size);
 if(craftMarketCatalogRequest)return craftMarketCatalogRequest;
 craftMarketCatalogRequest=(async()=>{
  var response=await fetch('https://api.arsha.io/util/db?lang=en',{signal:AbortSignal.timeout(12000)});
  if(!response.ok)throw Error('Full item index unavailable (HTTP '+response.status+')');
  var items=await response.json();
  if(!Array.isArray(items)||items.length>150000)throw Error('Invalid market item index');
  var catalog=new Map();
  for(var item of items){
   if(Number.isSafeInteger(item?.id)&&item.id>0&&typeof item.name==='string'&&item.name.trim()&&item.name.length<=200){
    catalog.set(item.id,{id:item.id,name:item.name});
   }
  }
  if(!catalog.size)throw Error('Market item index returned no valid names');
  craftMarketFullCatalog=catalog;
  return catalog.size;
 })().finally(()=>{craftMarketCatalogRequest=null;});
 return craftMarketCatalogRequest;
}

function craftMarketBaseQuotes(payload,ids,requestRegion){
 var rows=Array.isArray(payload)?payload.flat(2):[payload],allowed=new Set(ids),quotes=new Map();
 for(var row of rows){
  if(!row||!allowed.has(row.id)||row.sid!==0||typeof row.name!=='string'||!row.name.trim()||!Number.isSafeInteger(row.basePrice)||row.basePrice<=0)continue;
  var quote={id:row.id,name:row.name,price:row.basePrice,marketRegion:requestRegion,source:'Arsha Central Market',price_basis:'market_base'};
  for(var [field,key] of [['currentStock','stock'],['totalTrades','trades'],['lastSoldPrice','last_sold_price'],['lastSoldTime','last_sold_at'],['priceMin','min_price'],['priceMax','max_price']]){
   if(Number.isSafeInteger(row[field])&&row[field]>=0)quote[key]=row[field];
  }
  quotes.set(quote.id,quote);
 }
 return [...quotes.values()];
}

async function craftMarketFetchQuotes(ids,requestRegion){
 var market=String(requestRegion).toLowerCase();
 if(!['na','eu'].includes(market))throw Error('Choose NA or EU for market quotes');
 var end=Date.now()+18000,budget=32,received=0;
 async function lookup(batch){
  var remaining=end-Date.now();
  if(!budget||remaining<=0)return;
  budget--;
  var response=await fetch('https://api.arsha.io/v2/'+market+'/GetWorldMarketSubList?id='+batch.join(',')+'&lang=en',{signal:AbortSignal.timeout(Math.min(6000,remaining))});
  if([400,404,500].includes(response.status)){
   if(batch.length>1){var mid=Math.ceil(batch.length/2);await lookup(batch.slice(0,mid));await lookup(batch.slice(mid));}
   return;
  }
  if(!response.ok)throw Error('Arsha market returned HTTP '+response.status);
  var rows=craftMarketBaseQuotes(await response.json(),batch,requestRegion);
  received+=rows.length;visionRememberMarketQuotes(rows);
 }
 for(var i=0;i<ids.length&&budget&&Date.now()<end;i+=16)await lookup(ids.slice(i,i+16));
 return received;
}

function craftMarketHistoryPoints(payload,id){
 if(payload?.id!==id||payload.sid!==0||!payload.history||Array.isArray(payload.history))return [];
 return Object.entries(payload.history).map(([stamp,price])=>[Number(stamp),price])
  .filter(([stamp,price])=>Number.isSafeInteger(stamp)&&stamp>0&&Number.isSafeInteger(price)&&price>0)
  .sort((a,b)=>a[0]-b[0]).slice(-100);
}

async function craftMarketFetchHistory(id,requestRegion){
 var market=String(requestRegion).toLowerCase();
 if(!['na','eu'].includes(market)||!Number.isSafeInteger(id)||id<=0)throw Error('Select a valid market item');
 var response=await fetch('https://api.arsha.io/v2/'+market+'/GetMarketPriceInfo?id='+id+'&sid=0&lang=en',{signal:AbortSignal.timeout(10000)});
 if(!response.ok)throw Error('Price history unavailable (HTTP '+response.status+')');
 var points=craftMarketHistoryPoints(await response.json(),id);
 if(!points.length)throw Error('No base-item history returned');
 var key=market+':'+id;craftMarketHistory.set(key,points);
 if(craftMarketHistory.size>30)craftMarketHistory.delete(craftMarketHistory.keys().next().value);
}

function craftMarketHistoryHTML(item){
 var points=craftMarketHistory.get(String(region).toLowerCase()+':'+item.id);
 if(!points)return '';
 var start=points[0],latest=points.at(-1),prices=points.map(point=>point[1]),date=stamp=>new Date(stamp).toLocaleDateString();
 return '<section class="market-history"><h3>Base price history</h3>'+
  '<p>'+date(start[0])+' – '+date(latest[0])+' · Latest '+craftStudioMoney(latest[1])+' · Low '+craftStudioMoney(Math.min(...prices))+' · High '+craftStudioMoney(Math.max(...prices))+'</p>'+
  craftStudioGraph(points,'Arsha base-item price history')+
  '<details><summary>Recent price observations</summary><ul>'+points.slice(-7).reverse().map(([stamp,price])=>'<li>'+date(stamp)+' · '+craftStudioMoney(price)+'</li>').join('')+'</ul></details></section>';
}

function craftMarketOpen(itemId,recipeId=null){
 craftMarketItemId=itemId;craftMarketRecipeId=recipeId;craftMarketQuery='';
 showView('market');
 document.getElementById('craftMarketDesk')?.scrollIntoView({block:'start'});
}

function craftMarketCatalog(){
 var catalog=new Map(craftMarketFullCatalog||[]);
 for(var item of Object.values(VISION_CRAFT_DATA.items))catalog.set(item.id,item);
 var selected=craftMarketItemId,quote=selected?craftStudioQuote('',selected):null;
 if(selected&&!catalog.has(selected))catalog.set(selected,{id:selected,name:quote?.name||'Item #'+selected});
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
 if(normalized.length<2)return [];
 if(!craftMarketSearchIndex.has(catalog))craftMarketSearchIndex.set(catalog,[...catalog.values()].map(item=>[VisionCraft.key(item.name),item]));
 return craftMarketSearchIndex.get(catalog).filter(([key])=>key.includes(normalized))
  .sort(([a,x],[b,y])=>Number(b.startsWith(normalized))-Number(a.startsWith(normalized))||x.name.localeCompare(y.name)||x.id-y.id)
  .slice(0,20).map(([,item])=>item);
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
  '<dl class="market-facts"><div><dt>Last sale</dt><dd>'+number(quote?.last_sold_price)+'</dd></div><div><dt>Lifetime trades</dt><dd>'+number(quote?.trades)+'</dd></div>'+
  '<div><dt>Listed price range</dt><dd>'+number(quote?.min_price)+' – '+number(quote?.max_price)+'</dd></div></dl>'+
  '<div class="studio-actions"><button type="button" class="btn-secondary" data-market-refresh="'+item.id+'">Refresh quote</button>'+
  '<button type="button" class="btn-secondary" data-market-history="'+item.id+'">Load price history</button></div>'+craftMarketHistoryHTML(item)+
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
 host.innerHTML='<header class="market-desk-header"><div><small>VISION / MARKET INTELLIGENCE</small><h1>Market workbench</h1><p>Check live listings, trace recipes, and price your production line.</p></div><b>'+esc(String(region).toUpperCase())+'</b></header>'+
  '<div class="market-desk-grid"><section class="market-desk-panel"><form id="marketItemSearch"><label for="marketItemQuery">Item name or exact ID</label><div><input id="marketItemQuery" type="search" value="'+esc(craftMarketQuery)+'" placeholder="Wheat Flour, Balenos Meal, 9601"><button class="btn-secondary" type="submit">Find</button></div></form>'+
  (craftMarketFullCatalog?'<p class="studio-muted">Full name index loaded. Live lookup determines whether an item has a listing.</p>':'<button class="market-inline" type="button" data-market-index>Load full item name index</button>')+
  '<div id="marketItemResults"></div><p id="marketDeskStatus" role="status"></p>'+craftMarketInspect(item)+'</section>'+
  '<section class="market-desk-panel">'+craftMarketBasket(recipe,plan)+'</section></div>';
 var results=host.querySelector('#marketItemResults'),input=host.querySelector('#marketItemQuery');
 function search(){
  craftMarketQuery=input.value;
  var matches=craftMarketMatches(catalog,craftMarketQuery);
  results.innerHTML=matches.map(row=>'<button type="button" data-market-item="'+row.id+'">'+esc(row.name)+' <small>#'+row.id+'</small></button>').join('')||
   (craftMarketQuery.trim()?'<p class="studio-muted">No matching name. Load the full index or enter an exact item ID.</p>':'');
 }
 input.oninput=search;
 host.querySelector('#marketItemSearch').onsubmit=event=>{
  event.preventDefault();search();
  var hits=craftMarketMatches(catalog,craftMarketQuery);
  var exact=/^\d{1,9}$/.test(craftMarketQuery.trim())?Number(craftMarketQuery):null;
  if(hits.length===1||exact>0){craftMarketItemId=hits[0]?.id||exact;craftMarketRender();}

 };
 search();
 host.onclick=async event=>{
  var button=event.target.closest('button');if(!button)return;
  if(button.hasAttribute('data-market-open-craft')){showView('craft');craftWorkflowSet('planner');return;}
  if(button.dataset.marketRecipe){showView('craft');craftWorkflowSet('planner');selectRecipe(button.dataset.marketRecipe);return;}
  if(button.dataset.marketItem){craftMarketItemId=Number(button.dataset.marketItem);craftMarketRender();return;}
  if(button.hasAttribute('data-market-index')){
   var indexLabel=host.querySelector('#marketDeskStatus');
   indexLabel.textContent='Loading item names…';button.disabled=true;
   try{
    var count=await craftMarketLoadCatalog();
    if(currentView==='market'&&host.querySelector('#marketDeskStatus')===indexLabel){
     craftMarketRender();host.querySelector('#marketDeskStatus').textContent=count.toLocaleString()+' item names loaded.';
    }
   }catch(error){if(host.querySelector('#marketDeskStatus')===indexLabel){indexLabel.textContent=error.message;button.disabled=false;}}
   return;
  }
  if(button.dataset.marketHistory){
   var historyLabel=host.querySelector('#marketDeskStatus'),requestRegion=region;
   historyLabel.textContent='Loading base-item price history…';button.disabled=true;
   try{
    await craftMarketFetchHistory(Number(button.dataset.marketHistory),requestRegion);
    if(currentView==='market'&&host.querySelector('#marketDeskStatus')===historyLabel)craftMarketRender();
   }catch(error){if(host.querySelector('#marketDeskStatus')===historyLabel){historyLabel.textContent=error.message;button.disabled=false;}}
   return;
  }
  var ids=button.dataset.marketRefresh?[Number(button.dataset.marketRefresh)]:
   button.hasAttribute('data-market-refresh-basket')&&recipe?craftStudioIds(recipe):null;
  if(!ids)return;
  var label=host.querySelector('#marketDeskStatus');
  label.textContent='Refreshing exact regional quotes…';button.disabled=true;
  var result=await craftStudioRequestQuotes(ids,true);
  if(currentView!=='market'||host.querySelector('#marketDeskStatus')!==label)return;
  craftMarketRender();
  host.querySelector('#marketDeskStatus').textContent=result.ok?(result.count+' quotes returned. Missing prices stay unknown.') :result.message;
 };
}
