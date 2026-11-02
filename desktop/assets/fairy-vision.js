/* Local observation adapter. No writes to the Fairy vault or native ledger. */
(function(root){
  'use strict';
  function nameKey(value){return String(value||'').normalize('NFKC').toLowerCase().replace(/[’‘]/g,"'").replace(/\s+/g,' ').trim();}
  function matchRows(items,catalog){
    const names=new Map();
    for(const treasure of catalog||[])for(const part of treasure.parts||[]){
      const key=nameKey(part.name);if(!names.has(key))names.set(key,[]);names.get(key).push(treasure.name);
    }
    return (items||[]).filter(row=>typeof row.item==='string'&&Number.isSafeInteger(row.quantity)&&row.quantity>0)
      .map(row=>({item:row.item,quantity:row.quantity,matches:[...new Set(names.get(nameKey(row.item))||[])]}))
      .sort((a,b)=>b.matches.length-a.matches.length||b.quantity-a.quantity).slice(0,80);
  }
  const api={nameKey,matchRows};
  if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
  root.VisionFairyLoot=api;
  const connect=document.getElementById('vision-connect'),state=document.getElementById('vision-loot-state'),body=document.getElementById('vision-loot-rows');
  if(!connect||!state||!body)return;
  let timer=null,busy=false,generation=0;
  function schedule(){clearTimeout(timer);timer=null;if(connect.checked&&!document.hidden)timer=setTimeout(refresh,10000);}
  async function refresh(){
    if(!connect.checked||document.hidden||busy)return;
    busy=true;const token=generation;
    try{
      const response=await fetch('/durability',{cache:'no-store',signal:AbortSignal.timeout(5000)});
      if(!response.ok)throw Error('Local bridge unavailable');
      const reading=await response.json();if(token!==generation)return;
      const loot=reading.crafting_loot;
      if(!loot){body.replaceChildren();state.textContent='Optional loot sharing is off. Enable it in Vision to connect this page.';return;}
      body.replaceChildren();
      const rows=matchRows(loot.items,root.VisionTreasureCatalog);
      for(const row of rows){
        const tr=document.createElement('tr');
        for(const value of [row.item,row.quantity,row.matches.join(', ')||'No exact treasure match']){
          const cell=document.createElement('td');cell.textContent=String(value);cell.style.padding='8px';tr.append(cell);
        }
        if(row.matches.length)tr.style.background='#30203e';body.append(tr);
      }
      state.textContent=(loot.available?'Observing':'Paused: '+(loot.reason||'capture unavailable'))+
        ' · '+Number(loot.units||0).toLocaleString()+' recorded units · '+Number(loot.events||0).toLocaleString()+
        ' events · '+(loot.market_silver==null?'value unavailable':Number(loot.market_silver).toLocaleString()+' gross silver')+
        ' · all recorded history, not just this session · showing up to 80 items. Refreshed '+new Date().toLocaleTimeString();
    }catch(error){if(token===generation)state.textContent='Disconnected: '+error.message+'. Last displayed observations may be stale.';}
    finally{busy=false;schedule();}
  }
  connect.addEventListener('change',()=>{generation++;clearTimeout(timer);if(connect.checked)refresh();else{body.replaceChildren();state.textContent='Disconnected. Loot observation link is off.';}});
  document.getElementById('vision-refresh').addEventListener('click',refresh);
  document.addEventListener('visibilitychange',()=>{if(document.hidden){clearTimeout(timer);generation++;}else if(connect.checked)refresh();});
})(typeof window==='undefined'?globalThis:window);
