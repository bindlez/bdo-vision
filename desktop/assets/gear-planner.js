/* BDO Vision Gear Studio. No framework, polling or OCR worker while idle. */
(function () {
  'use strict';
  const slots = [
    ['main','Main weapon',1],['awakening','Awakening weapon',10],['sub','Sub-weapon',5],
    ['helmet','Helmet',15,1],['armor','Armor',15,2],['gloves','Gloves',15,3],['shoes','Shoes',15,4],
    ['necklace','Necklace',20,2],['belt','Belt',20,4],['ring1','Ring · left',20,1],['ring2','Ring · right',20,1],
    ['earring1','Earring · left',20,3],['earring2','Earring · right',20,3],['stone','Alchemy stone',45],
    ['artifact1','Artifact · left',85,6],['artifact2','Artifact · right',85,6],
    ['tool','Life tool',40],['clothes','Life skill / costume clothes',15,5],
    ['lightstone1','Lightstone 1',85,0],['lightstone2','Lightstone 2',85,0],['lightstone3','Lightstone 3',85,0],['lightstone4','Lightstone 4',85,0]
  ];
  const categories=[1,5,10,15,20,40,45,85];
  const number=(v,max=1e15)=>(typeof v==='number'||typeof v==='string'&&v.trim()!=='')&&Number.isSafeInteger(Number(v))&&Number(v)>=0&&Number(v)<=max?Number(v):null;
  const clean=s=>String(s||'').slice(0,150);
  function fits(item,slot){return item.mainCategory===slot[2]&&
    (slot[0]==='tool'?item.subCategory<=8:slot[0]==='clothes'?[5,6].includes(item.subCategory):slot[3]===0?item.subCategory<=5:slot[3]===undefined||item.subCategory===slot[3]);}
  function sanitizeItem(v){
    if(!v||typeof v!=='object'||!clean(v.name).trim())return null;
    const id=number(v.id,1e7),enhance=number(v.enhance,30);
    if(id===null||id===0||enhance===null||!categories.includes(v.mainCategory))return null;
    return {id,name:clean(v.name),mainCategory:v.mainCategory,subCategory:number(v.subCategory,100)||0,enhance,caphras:number(v.caphras,20)||0};
  }
  function sanitizeState(raw){
    const blank={version:1,active:'starter',builds:[{id:'starter',name:'My equipment',character:'',current:{},target:{},sheet:{ap:null,aap:null,dp:null},budget:0}]};
    if(!raw||!Array.isArray(raw.builds))return blank;
    const seen=new Set();const builds=raw.builds.slice(0,12).filter(x=>x&&typeof x.id==='string'&&!seen.has(x.id)&&(seen.add(x.id),true)).map(b=>{
      const out={id:clean(b.id),name:clean(b.name)||'Untitled build',character:clean(b.character),current:{},target:{},sheet:{},budget:number(b.budget)||0};
      for(const side of ['current','target'])for(const slot of slots){const item=sanitizeItem(b[side]&&b[side][slot[0]]);if(item&&fits(item,slot))out[side][slot[0]]=item;}
      for(const key of ['ap','aap','dp'])out.sheet[key]=b.sheet?number(b.sheet[key],2000):null;
      return out;
    });
    return builds.length?{version:1,active:builds.some(b=>b.id===raw.active)?raw.active:builds[0].id,builds}:blank;
  }
  function priceFor(rows,level){
    const matches=(Array.isArray(rows)?rows:[]).filter(r=>number(r.minEnhance,30)!==null&&number(r.maxEnhance,30)!==null&&level>=Number(r.minEnhance)&&level<=Number(r.maxEnhance)&&number(r.basePrice)!==null);
    return matches.length===1&&Number(matches[0].basePrice)>0?Number(matches[0].basePrice):null;
  }
  function enhancementLabel(level,max){
    if(!level)return 'Base';const roman=['I','II','III','IV','V','VI','VII','VIII','IX','X'];
    return max<=10?(roman[level-1]||'+'+level):level>=16&&level<=20?roman[level-16]:'+'+level;
  }
  function importEnhancement(value,rows){
    if(!value)return null;const max=Math.max(0,...rows.map(r=>Number(r.maxEnhance)||0));
    const level=value.kind==='roman'?(max<=10?value.value:value.value<=5?15+value.value:null):value.value;
    return level!==null&&rows.some(r=>level>=r.minEnhance&&level<=r.maxEnhance)?level:null;
  }
  function totals(build,quote){
    let current=0,target=0,buy=0,missing=0,changed=0;
    for(const [slot] of slots){const a=build.current[slot],b=build.target[slot]||a;
      const av=a?quote(a):0,bv=b?quote(b):0;
      if(a&&av===null)missing++;if(b&&bv===null&&b!==a)missing++;
      current+=av||0;target+=bv||0;
      if(b&&(!a||a.id!==b.id||a.enhance!==b.enhance)){changed++;buy+=bv||0;}
    }
    return {current,target,buy,missing,changed};
  }
  const core={slots,fits,sanitizeState,priceFor,enhancementLabel,importEnhancement,totals};
  if(typeof module!=='undefined'&&module.exports)module.exports=core;
  if(typeof document==='undefined')return;
  window.VisionGear=core;
  const KEY='vision-gear-v1';let state;try{state=sanitizeState(JSON.parse(localStorage.getItem(KEY)||'null'));}catch(_){state=sanitizeState(null);}
  let side='current',selected='main',catalog=[],catalogRegion='',catalogAt=0,loading=null,search='',message='',busy=false;
  const quoteCache=new Map(),inflight=new Map();let imports=[],importReport=null,importTarget=null,saveTimer=0,renderTimer=0;
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money=n=>n===null?'Unpriced':Math.round(n).toLocaleString();
  const current=()=>state.builds.find(b=>b.id===state.active)||state.builds[0];
  const marketRegion=()=>String(typeof region!=='undefined'?region:'NA').toLowerCase();
  const localBase=()=>location.protocol==='http:'&&/^(127\.0\.0\.1|localhost)$/.test(location.hostname)?location.origin:typeof bridgeSelectedOrigin!=='undefined'?bridgeSelectedOrigin:null;
  function persist(){clearTimeout(saveTimer);saveTimer=setTimeout(()=>{try{localStorage.setItem(KEY,JSON.stringify(state));}catch(_){message='Browser storage is full. Export a backup to keep this build.';render();}},250);}
  function schedule(){clearTimeout(renderTimer);renderTimer=setTimeout(()=>{if(currentView==='gear')render();},60);}
  function quote(item){const entry=quoteCache.get(marketRegion()+':'+item.id);return entry?priceFor(entry.rows,item.enhance):null;}
  async function variants(item){
    const r=marketRegion(),key=r+':'+item.id,existing=quoteCache.get(key);
    if(existing&&Date.now()-existing.at<300000)return existing.rows;
    if(inflight.has(key))return inflight.get(key);
    const request=(async()=>{const response=await fetch('https://api.arsha.io/v2/'+r+'/GetWorldMarketSubList?id='+item.id+'&lang=en');if(!response.ok)throw Error('Equipment prices unavailable');
      const rows=await response.json();if(!Array.isArray(rows)||rows.some(x=>x.id!==item.id))throw Error('Invalid equipment identity in market response');
      if(quoteCache.size>=128)quoteCache.delete(quoteCache.keys().next().value);quoteCache.set(key,{rows,at:Date.now()});schedule();return rows;
    })();inflight.set(key,request);try{return await request;}finally{inflight.delete(key);}
  }
  async function loadCatalog(force=false){
    const r=marketRegion();if(loading)return loading;
    if(catalogRegion!==r){catalog=[];catalogAt=0;catalogRegion=r;try{
      const saved=JSON.parse(localStorage.getItem('vision-gear-catalog-v1-'+r)||'null');
      if(saved&&Array.isArray(saved.items)&&saved.items.length<=5000){catalog=saved.items.filter(x=>number(x.id,1e7)>0&&categories.includes(x.mainCategory)&&typeof x.name==='string').map(x=>({id:x.id,name:clean(x.name),mainCategory:x.mainCategory,subCategory:Number(x.subCategory)||0}));catalogAt=Number(saved.at)||0;}
    }catch(_){} }
    if(!force&&catalog.length&&Date.now()-catalogAt<86400000){message=catalog.length.toLocaleString()+' cached equipment records · '+r.toUpperCase()+' · catalog '+new Date(catalogAt).toLocaleString();return catalog;}
    loading=(async()=>{
      const collected=[],failed=[];message='Loading equipment from '+r.toUpperCase()+' Central Market…';schedule();
      // Two requests at a time; no resident market polling for gear.
      for(let i=0;i<categories.length;i+=2){const groups=await Promise.all(categories.slice(i,i+2).map(async category=>{
        try{const response=await fetch('https://api.arsha.io/v2/'+r+'/GetWorldMarketList?mainCategory='+category+'&lang=en',{signal:AbortSignal.timeout(12000)});if(!response.ok)throw Error('Market catalog unavailable');
        const rows=await response.json();if(!Array.isArray(rows))throw Error('Invalid equipment catalog');
        return rows.filter(x=>number(x.id,1e7)>0&&x.mainCategory===category&&typeof x.name==='string').map(x=>({id:x.id,name:clean(x.name),mainCategory:category,subCategory:Number(x.subCategory)||0}));
        }catch(_){failed.push(category);return catalog.filter(x=>x.mainCategory===category);}
      }));collected.push(...groups.flat());}
      if(marketRegion()!==r)throw Error('Region changed. Reopen Gear Studio to load the selected region.');
      if(!collected.length)throw Error('Market catalog unavailable. Saved builds are safe; try refresh.');
      catalog=collected;catalogRegion=r;if(!failed.length)catalogAt=Date.now();
      try{localStorage.setItem('vision-gear-catalog-v1-'+r,JSON.stringify({at:catalogAt,items:catalog}));}catch(_){}
      message=catalog.length.toLocaleString()+' equipment records · '+r.toUpperCase()+' · '+(failed.length?failed.length+' categories unavailable or cached; refresh later':'loaded '+new Date().toLocaleTimeString());return catalog;
    })();try{return await loading;}finally{loading=null;schedule();}
  }
  async function refreshBuild(){
    const b=current(),items=[...Object.values(b.current),...Object.values(b.target)];const unique=[...new Map(items.map(x=>[x.id,x])).values()];
    for(let i=0;i<unique.length;i+=2)await Promise.all(unique.slice(i,i+2).map(x=>variants(x).catch(()=>null)));schedule();
  }
  const nav=document.createElement('button');nav.className='nav-item';nav.dataset.view='gear';nav.id='navGear';nav.innerHTML='<span class="icon">◇</span> Gear Studio';nav.style.cssText='font:inherit;width:100%;text-align:left;background:none;border:0;color:inherit';
  document.getElementById('sidebarNav').insertBefore(nav,document.getElementById('sidebarNav').firstChild);
  const view=document.createElement('section');view.id='viewGear';view.className='view';
  document.getElementById('viewCraft').parentNode.appendChild(view);
  const originalShow=showView;
  showView=function(name){originalShow(name);view.classList.toggle('active',name==='gear');nav.classList.toggle('active',name==='gear');if(name==='gear'){
    document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n===nav));history.replaceState(null,'','#gear');render();loadCatalog().then(refreshBuild).catch(e=>{message=e.message;schedule();});
  }};
  nav.addEventListener('click',e=>{e.stopPropagation();showView('gear');});
  function itemName(item){if(!item)return 'Choose equipment';const cached=quoteCache.get(marketRegion()+':'+item.id);const max=cached?Math.max(...cached.rows.map(x=>Number(x.maxEnhance)||0)):20;return enhancementLabel(item.enhance,max)+' · '+item.name;}
  function render(){
    const b=current(),slot=slots.find(s=>s[0]===selected),item=b[side][selected],summary=totals(b,quote);
    const q=item&&quoteCache.get(marketRegion()+':'+item.id),rows=q?q.rows:[],max=Math.max(0,...rows.map(r=>Number(r.maxEnhance)||0));
    const levels=[...new Set(rows.flatMap(r=>Array.from({length:Math.max(0,Math.min(31,Number(r.maxEnhance)-Number(r.minEnhance)+1))},(_,i)=>Number(r.minEnhance)+i)))].sort((a,b)=>a-b);
    const filtered=catalog.filter(i=>fits(i,slot)&&(!search||i.name.toLowerCase().includes(search.toLowerCase())));
    view.innerHTML='<div class="gear-head"><div><div class="gear-eyebrow">BDO VISION / GEAR STUDIO</div><h1>Your next upgrade,<br><span>made tangible.</span></h1><p>Build your loadout. Map your next piece. Keep your silver goal in sight.</p></div><div class="gear-local">LOCAL FIRST<span>Saved in this browser · no account needed</span></div></div>'+
      '<div class="gear-toolbar"><label>Build<select id="gearBuild">'+state.builds.map(x=>'<option value="'+esc(x.id)+'" '+(x.id===b.id?'selected':'')+'>'+esc(x.name)+'</option>').join('')+'</select></label><label>Build name<input id="gearName" value="'+esc(b.name)+'" maxlength="80"></label><label>Character / class<input id="gearCharacter" value="'+esc(b.character)+'" placeholder="Optional" maxlength="80"></label><button id="gearNew">New build</button><button id="gearDuplicate">Duplicate</button><button id="gearExport">Export builds</button><label class="gear-file">Import backup<input id="gearBackup" type="file" accept="application/json,.json"></label></div>'+
      '<div class="gear-kpis"><div><small>CURRENT MARKET VALUE</small><strong>'+money(summary.current)+'</strong><span>'+marketRegion().toUpperCase()+' silver · '+(summary.missing?'partial / unpriced pieces':'loaded quotes')+'</span></div><div><small>BUY YOUR PLANNED UPGRADES</small><strong>'+money(summary.buy)+'</strong><span>'+summary.changed+' changed slots · before selling current gear</span></div><div><small>SAVINGS GOAL</small><strong>'+money(Math.max(0,summary.buy-b.budget))+'</strong><span>remaining silver · enter saved budget below</span></div></div>'+
      '<div class="gear-controls"><div role="group" aria-label="Equipment loadout"><button data-side="current" aria-pressed="'+(side==='current')+'">Equipped now</button><button data-side="target" aria-pressed="'+(side==='target')+'">Upgrade plan</button></div><label>Saved silver<input id="gearBudget" type="number" min="0" max="1000000000000000" value="'+b.budget+'"></label><button id="gearCopy">Copy current → upgrade plan</button><button id="gearRefresh">Refresh market</button><button id="gearSaveWindows">Save Windows backup</button><button id="gearRestoreWindows">Restore Windows backup</button></div>'+
      '<div class="gear-progress"><progress max="100" value="'+(summary.buy?Math.min(100,b.budget/summary.buy*100):0)+'"></progress><p>'+esc(message||'Equipment catalog loads only when you open this tab. Prices refresh on demand.')+'</p><button id="gearSweepTop" '+(busy?'disabled':'')+'>Import from BDO · 3-second sweep</button><p id="gearTopStatus" role="status">'+(busy?'Equipment import in progress…':'Open equipment in game, then start your clockwise tooltip sweep.')+'</p></div>'+
      '<div class="gear-layout"><section class="gear-board"><div class="gear-section-title"><h2>'+ (side==='current'?'Equipped now':'Your upgrade plan')+'</h2><span>'+Object.keys(b[side]).length+' / '+slots.length+' slots</span></div><div class="gear-slots">'+slots.map(s=>{const v=b[side][s[0]],inherited=side==='target'&&!v&&b.current[s[0]];return '<button class="gear-slot '+(selected===s[0]?'chosen':'')+' '+(v?'filled':'')+'" data-slot="'+s[0]+'" aria-pressed="'+(selected===s[0])+'"><small>'+esc(s[1])+'</small><span class="gear-glyph" aria-hidden="true">'+(s[2]===20?'◈':s[2]===15?'⬡':s[2]===85?'✦':'◇')+'</span><b>'+esc(v?itemName(v):inherited?'Keep current item':'Choose equipment')+'</b><em>'+esc(v?money(quote(v))+' silver':inherited?'Inherited in cost comparison':'Empty')+'</em></button>';}).join('')+'</div></section>'+
      '<aside class="gear-editor"><div class="gear-section-title"><h2>'+esc(slot[1])+'</h2><span>'+esc(side==='current'?'CURRENT':'TARGET')+'</span></div>'+
      (item?'<div class="gear-selected"><b>'+esc(item.name)+'</b><small>Market ID '+item.id+' · '+marketRegion().toUpperCase()+'</small><label>Enhancement<select id="gearEnhance" '+(!levels.length?'disabled':'')+'>'+(levels.length?levels:[item.enhance]).map(n=>'<option value="'+n+'" '+(n===item.enhance?'selected':'')+'>'+esc(enhancementLabel(n,max))+'</option>').join('')+'</select></label><label>Caphras level · note only<input id="gearCaphras" type="number" min="0" max="20" value="'+item.caphras+'"></label><p>'+money(quote(item))+' silver · '+(q?'quote loaded '+new Date(q.at).toLocaleTimeString():'quote pending')+'</p><button id="gearClear">Clear this slot</button></div>':'<p class="gear-note">Choose equipment from the real market catalog below.</p>')+
      '<label class="gear-search">Find '+esc(slot[1].toLowerCase())+'<input id="gearSearch" type="search" placeholder="Search equipment…" value="'+esc(search)+'" autocomplete="off"></label><div class="gear-results">'+filtered.slice(0,80).map(x=>'<button data-item="'+x.id+'"><b>'+esc(x.name)+'</b><small>#'+x.id+'</small></button>').join('')+'</div><p class="gear-note">'+filtered.length+' matches'+(filtered.length>80?' · refine search to see more':'')+'. All market-listed equipment is included. Untradeable items may be absent.</p></aside></div>'+
      '<section class="gear-import"><div><div class="gear-eyebrow">FROM GAME TO YOUR BUILD</div><h2>Three seconds. One clockwise sweep.</h2><p>Open equipment in BDO. Start a sweep, switch to the game, then move clockwise over each item so its tooltip appears. Review the recognized names and levels before applying.</p><p class="gear-note">Captures start 3 seconds after you click and wait briefly for BDO. About 12 tooltip frames are read afterward; a fast sweep can miss items. Images stay on this PC and are discarded after reading.</p></div><div class="gear-import-actions"><button id="gearSweep" '+(busy?'disabled':'')+'>Start 3-second tooltip sweep</button><label class="gear-file">Read equipment screenshot<input id="gearImage" type="file" accept="image/png,image/jpeg" '+(busy?'disabled':'')+'></label><span id="gearImportStatus" role="status">'+(busy?'Import in progress…':'Uses your paired Windows reader · nothing runs while idle')+'</span></div><div id="gearImportReview" class="gear-review"></div></section>'+
      '<details class="gear-details"><summary>Sheet stats and valuation details</summary><p>Market prices do not contain verified AP / DP stats. Record the sheet values shown in game here; they are never fabricated from prices. Caphras is saved as a planning note and is excluded from valuation. Quotes may group several enhancement levels into one market listing. This is item value and an upgrade shopping budget, not enhancement cost or guaranteed sale proceeds.</p><div class="gear-sheet">'+['ap','aap','dp'].map(k=>'<label>'+k.toUpperCase()+' · entered sheet value<input data-sheet="'+k+'" type="number" min="0" max="2000" value="'+(b.sheet[k]===null?'':b.sheet[k])+'"></label>').join('')+'</div><p>'+summary.missing+' unpriced loadout entries excluded. Target set value: '+money(summary.target)+' silver. '+(summary.missing?'Refresh prices before trusting the totals.':'')+' Stats, bonuses, journals and crystals are not simulated yet.</p></details>';
    bind();renderReview();
  }
  function bind(){
    const on=(id,event,fn)=>document.getElementById(id)?.addEventListener(event,fn);
    on('gearBuild','change',e=>{state.active=e.target.value;persist();render();refreshBuild();});
    for(const [id,key] of [['gearName','name'],['gearCharacter','character']])on(id,'change',e=>{current()[key]=clean(e.target.value);persist();render();});
    on('gearBudget','change',e=>{current().budget=number(e.target.value)||0;persist();render();});
    function create(duplicate){if(state.builds.length>=12){message='Twelve builds saved. Export a backup before adding more.';render();return;}const b=duplicate?JSON.parse(JSON.stringify(current())):sanitizeState(null).builds[0];b.id='build-'+Date.now()+'-'+Math.random().toString(36).slice(2,7);b.name=duplicate?clean(b.name+' copy'):'New build';state.builds.push(b);state.active=b.id;persist();render();}
    on('gearNew','click',()=>create(false));on('gearDuplicate','click',()=>create(true));
    on('gearCopy','click',()=>{current().target=JSON.parse(JSON.stringify(current().current));side='target';persist();render();});
    on('gearExport','click',()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='bdo-vision-gear-builds.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),500);});
    on('gearBackup','change',async e=>{const f=e.target.files[0];if(!f)return;try{if(f.size>300000)throw Error('Backup must be under 300 KB');const input=JSON.parse(await f.text());if(input.version!==1||!Array.isArray(input.builds))throw Error('Not a Gear Studio backup');const loaded=sanitizeState(input);for(const b of loaded.builds){if(state.builds.length>=12)break;b.id='import-'+Date.now()+'-'+Math.random().toString(36).slice(2,7);state.builds.push(b);state.active=b.id;}persist();message='Backup builds added; your existing builds were kept.';render();refreshBuild();}catch(err){message=err.message;render();}});
    on('gearRefresh','click',async()=>{quoteCache.clear();try{await loadCatalog(true);await refreshBuild();}catch(e){message=e.message;}render();});
    on('gearSaveWindows','click',async()=>{try{if(!localBase())throw Error('Open the planner from Vision for a Windows backup');const reply=await fetch(localBase()+'/gear/builds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(state)});const result=await reply.json();if(!reply.ok)throw Error(result.error);message='Saved '+result.builds+' builds in your protected Windows profile. Previous backup retained.';}catch(e){message=e.message;}render();});
    on('gearRestoreWindows','click',async()=>{try{if(!localBase())throw Error('Open the paired planner first');const reply=await fetch(localBase()+'/gear/builds');const result=await reply.json();if(!reply.ok)throw Error(result.error);const restored=sanitizeState(result.data);let count=0;for(const b of restored.builds){if(state.builds.length>=12)break;b.id='restored-'+Date.now()+'-'+Math.random().toString(36).slice(2,7);state.builds.push(b);state.active=b.id;count++;}persist();message=count+' backup builds added. Existing browser builds retained.';refreshBuild();}catch(e){message=e.message;}render();});
    view.querySelectorAll('[data-side]').forEach(n=>n.onclick=()=>{side=n.dataset.side;render();});
    view.querySelectorAll('[data-slot]').forEach(n=>n.onclick=()=>{selected=n.dataset.slot;search='';render();const item=current()[side][selected];if(item)variants(item).catch(e=>{message=e.message;schedule();});});
    view.querySelectorAll('[data-item]').forEach(n=>n.onclick=async()=>{const item=catalog.find(x=>x.id===Number(n.dataset.item));if(!item)return;current()[side][selected]={...item,enhance:0,caphras:0};persist();render();try{await variants(item);}catch(e){message=e.message;schedule();}});
    on('gearSearch','input',e=>{search=e.target.value;clearTimeout(renderTimer);const caret=e.target.selectionStart;renderTimer=setTimeout(()=>{render();const input=document.getElementById('gearSearch');input.focus();input.setSelectionRange(caret,caret);},140);});
    on('gearEnhance','change',e=>{current()[side][selected].enhance=Number(e.target.value);persist();render();});
    on('gearCaphras','change',e=>{current()[side][selected].caphras=number(e.target.value,20)||0;persist();});
    on('gearClear','click',()=>{delete current()[side][selected];persist();render();});
    view.querySelectorAll('[data-sheet]').forEach(n=>n.onchange=()=>{current().sheet[n.dataset.sheet]=n.value===''?null:number(n.value,2000);persist();});
    on('gearImage','change',e=>readScreenshot(e.target.files[0]));on('gearSweep','click',startSweep);on('gearSweepTop','click',startSweep);
  }
  function apiCatalog(){return catalog.map(({id,name,mainCategory,subCategory})=>({id,name,mainCategory,subCategory}));}
  async function prepareImport(){if(busy)throw Error('An import is already running');if(!localBase())throw Error('Open Gear Studio from your paired Windows app for OCR import.');busy=true;importTarget={buildId:current().id,side};render();try{await loadCatalog();}catch(e){busy=false;throw e;}render();}
  function status(text){for(const id of ['gearImportStatus','gearTopStatus']){const el=document.getElementById(id);if(el)el.textContent=text;}}
  async function review(report){
    importReport=report;imports=[];
    for(const candidate of report.candidates||[]){const source=catalog.find(x=>x.id===candidate.id);if(!source)continue;let rows=[];try{rows=await variants(source);}catch(_){}
      const used=new Set(imports.map(x=>x.slot));const slot=slots.find(s=>fits(source,s)&&!used.has(s[0]));imports.push({source,slot:slot?slot[0]:'',level:importEnhancement(candidate.enhancement,rows),rows,observed:candidate.enhancement?.label||'Level unreadable',enabled:true});}
    busy=false;render();status(imports.length+' recognized items. Review slot and enhancement below.');if(currentView==='gear')document.getElementById('gearImportReview')?.scrollIntoView({block:'start'});
  }
  async function readScreenshot(file){if(!file)return;try{await prepareImport();status('Reading screenshot locally…');if(file.size>12000000)throw Error('Use a cropped screenshot under 12 MB');
    const image=await createImageBitmap(file);const scale=Math.min(1,1700/Math.max(image.width,image.height));const canvas=document.createElement('canvas');canvas.width=Math.round(image.width*scale);canvas.height=Math.round(image.height*scale);canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);image.close();
    const response=await fetch(localBase()+'/gear/ocr',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image:canvas.toDataURL('image/jpeg',.92),catalog:apiCatalog()})});const result=await response.json();if(!response.ok)throw Error(result.error||'Import failed');await review(result);
  }catch(e){busy=false;render();status(e.message);}}
  async function startSweep(){try{await prepareImport();status('Switch to BDO now. Move clockwise over your equipment when the 3-second lead-in ends.');
    const response=await fetch(localBase()+'/gear/sweep',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({catalog:apiCatalog()})});const start=await response.json();if(!response.ok)throw Error(start.error||'Could not start sweep');
    const deadline=Date.now()+180000;
    while(Date.now()<deadline){await new Promise(r=>setTimeout(r,750));const reply=await fetch(localBase()+'/gear/sweep?id='+encodeURIComponent(start.id));const job=await reply.json();if(!reply.ok)throw Error(job.error||'Import unavailable');status(job.message||job.stage);if(job.stage==='review'){await review(job.result);return;}if(['error','cancelled'].includes(job.stage))throw Error(job.message||'Import cancelled');}
    throw Error('Import timed out. Your saved gear has not changed.');
  }catch(e){busy=false;render();status(e.message);}}
  function renderReview(){const area=document.getElementById('gearImportReview');if(!area||!importReport)return;
    area.innerHTML='<h3>Review equipment import</h3><p>'+esc(importReport.notice)+'</p>'+(imports.length?imports.map((row,i)=>'<div class="gear-import-row"><label><input type="checkbox" data-accept="'+i+'" '+(row.enabled?'checked':'')+'> '+esc(row.source.name)+'</label><label>Slot<select data-import-slot="'+i+'"><option value="">Select slot</option>'+slots.filter(s=>fits(row.source,s)).map(s=>'<option value="'+s[0]+'" '+(s[0]===row.slot?'selected':'')+'>'+esc(s[1])+'</option>').join('')+'</select></label><label>Enhancement<select data-import-level="'+i+'"><option value="">'+esc(row.observed)+' · choose level</option>'+[...new Set(row.rows.flatMap(r=>Array.from({length:Math.max(0,Math.min(31,r.maxEnhance-r.minEnhance+1))},(_,n)=>r.minEnhance+n)))].sort((a,b)=>a-b).map(n=>'<option value="'+n+'" '+(n===row.level?'selected':'')+'>'+esc(enhancementLabel(n,Math.max(...row.rows.map(r=>r.maxEnhance))))+'</option>').join('')+'</select></label></div>').join('')+'<button id="gearApply">Apply reviewed items to '+esc(side==='current'?'equipped gear':'upgrade plan')+'</button>':'<p>No item names could be resolved. Hover long enough for tooltips to appear, or use a clear tooltip screenshot. Icon-only tiles do not identify gear.</p>')+'<details><summary>OCR text / diagnostics</summary><pre>'+esc(importReport.text||'No readable text')+'</pre></details>';
    area.querySelectorAll('[data-accept]').forEach(n=>n.onchange=()=>imports[Number(n.dataset.accept)].enabled=n.checked);
    area.querySelectorAll('[data-import-slot]').forEach(n=>n.onchange=()=>imports[Number(n.dataset.importSlot)].slot=n.value);
    area.querySelectorAll('[data-import-level]').forEach(n=>n.onchange=()=>imports[Number(n.dataset.importLevel)].level=n.value===''?null:Number(n.value));
    const apply=document.getElementById('gearApply');if(apply){const target=state.builds.find(b=>b.id===importTarget?.buildId);apply.textContent='Apply reviewed items to '+(target?target.name:'original build')+' · '+(importTarget?.side==='target'?'upgrade plan':'equipped gear');apply.onclick=()=>{const accepted=imports.filter(x=>x.enabled),destinations=new Set();if(!target){status('Original build is unavailable. Start a new import.');return;}for(const row of accepted){if(!row.slot||row.level===null){status('Choose a slot and enhancement for each checked item.');return;}if(destinations.has(row.slot)){status('Two checked items use the same slot. Choose distinct slots.');return;}destinations.add(row.slot);}
      for(const row of accepted)target[importTarget.side][row.slot]={...row.source,enhance:row.level,caphras:0};state.active=target.id;side=importTarget.side;persist();message=accepted.length+' reviewed items applied. Existing unselected slots were kept.';imports=[];importReport=null;render();};}
  }
  window.addEventListener('hashchange',()=>{if(location.hash==='#gear')showView('gear');});
  if(location.hash==='#gear')showView('gear');
})();
