/* Optional recorded output. Prices are joined by market ID or exact item name. */
var visionLootLast=null,visionMarketById={},visionMarketByName={},visionMarketGeneration=0,visionLootTableKey=null;
function visionName(name){return String(name||'').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();}
function visionRememberMarketQuotes(list){
  visionMarketGeneration++;
  list.forEach(function(item){
    var key=String(item.marketRegion||region).toLowerCase()+':';
    if(Number.isSafeInteger(Number(item.price)) && Number(item.price)>0){
      if(item.id)visionMarketById[key+String(item.id)]=Number(item.price);
      visionMarketByName[key+visionName(item.name)]=Number(item.price);
    }
  });
  if(visionLootLast)renderVisionCraftingLoot(visionLootLast);
}
function renderVisionCraftingLoot(reading){
  var panel=document.getElementById('visionCraftingLoot');
  var data=reading && reading.crafting_loot;
  if(!data){panel.hidden=true;visionLootLast=null;return;}
  visionLootLast=reading;panel.hidden=false;
  var age=data.updated_at?Math.max(0,Date.now()/1000-Number(data.updated_at)):Infinity;
  var stamp=data.updated_at?new Date(Number(data.updated_at)*1000).toLocaleTimeString():'no reading yet';
  document.getElementById('visionLootState').textContent=data.available===true && age<=15?'Observed '+stamp:'Unavailable now · '+(data.reason||'reading is no longer current')+' · last observation '+stamp;
  document.getElementById('visionLootCounts').textContent=data.captured_items_available===true?(Number(data.elixir_units)||0).toLocaleString()+' recorded elixirs / draughts · '+(Number(data.extra_units)||0).toLocaleString()+' extra / other units · '+(Number(data.rare_units)||0).toLocaleString()+' rare-notice units':'No recorded loot totals available';
  var body=document.getElementById('visionLootItems');
  var tableKey=JSON.stringify([region,data.items,visionMarketGeneration]),rebuild=tableKey!==visionLootTableKey;
  if(rebuild){body.replaceChildren();visionLootTableKey=tableKey;}
  var total=0n,priced=0,unpriced=0,key=String(region).toLowerCase()+':';
  (Array.isArray(data.items)?data.items:[]).slice(0,300).forEach(function(item){
    var quantity=Number(item.quantity),unit=visionMarketById[key+String(item.market_id)]||visionMarketByName[key+visionName(item.item)];
    if(unit==null && item.market_region && String(item.market_region).toLowerCase()===String(region).toLowerCase())unit=item.unit_price;
    var known=Number.isSafeInteger(unit) && unit>=0 && Number.isSafeInteger(quantity) && quantity>=0;
    var value=known?BigInt(unit)*BigInt(quantity):null;
    if(known){total+=value;priced++;}else unpriced++;
    if(!rebuild)return;
    var row=document.createElement('tr');var nameCell=document.createElement('td');
    var recipe=RECIPES.find(function(recipe){return visionName(recipe.name)===visionName(item.item);});
    if(recipe){var button=document.createElement('button');button.type='button';button.className='cat-btn';button.textContent=String(item.item);button.setAttribute('aria-label','Open existing recipe for '+item.item);button.onclick=function(){selectRecipe(recipe.id);document.getElementById('craftDetail').scrollIntoView({block:'start'});};nameCell.appendChild(button);}
    else nameCell.textContent=String(item.item||'');
    if(item.market_id){var code=document.createElement('small');code.textContent=' · #'+item.market_id;nameCell.appendChild(code);}row.appendChild(nameCell);
    [Number.isSafeInteger(quantity)?quantity.toLocaleString():'—',known?unit.toLocaleString():'Unpriced',known?value.toLocaleString():'—',String(item.group||'')+(item.price_basis==='npc_vendor'?' · NPC vendor':'')].forEach(function(text){var cell=document.createElement('td');cell.textContent=text;row.appendChild(cell);});body.appendChild(row);
  });
  document.getElementById('visionLootSilver').textContent=priced?total.toLocaleString()+' silver of recorded item value':'Waiting for matched market prices';
  document.getElementById('visionLootCoverage').textContent=unpriced?'Partial total: '+unpriced+' unmatched / unpriced item types excluded.':'Quantity × market or verified NPC sell value. No costs or fees deducted.';
}
