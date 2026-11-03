/* Canonical read-only recipe relationships. No prices, OCR, timers or storage. */
(function(root){
'use strict';
const EMPTY={},cache=new WeakMap(),nameKey=v=>String(v||'').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
function catalog(recipes,spec=EMPTY){
 let versions=cache.get(recipes);if(!versions){versions=new WeakMap();cache.set(recipes,versions);}if(versions.has(spec))return versions.get(spec);
 const byRecipe=new Map(),byItem=new Map(),byName=new Map(),producers=new Map(),consumers=new Map();
 const push=(map,id,value)=>{if(!map.has(id))map.set(id,[]);map.get(id).push(value);};
 for(const recipe of recipes){
  if(recipe.id)byRecipe.set(recipe.id,recipe);push(byName,nameKey(recipe.name),recipe);
  if(Number.isInteger(recipe.itemId)&&recipe.itemId>0){push(byItem,recipe.itemId,recipe);push(producers,recipe.itemId,{recipe,kind:'main'});}
  if(Number.isInteger(recipe.rare?.itemId))push(producers,recipe.rare.itemId,{recipe,kind:'rare'});
  for(const [index,m] of (recipe.mats||[]).entries()){
   const options=m.groupId&&spec.groups?.[m.groupId]?.length?spec.groups[m.groupId]:[{itemId:m.itemId,value:m.value||1}];
   for(const option of options){if(!Number.isInteger(option.itemId)||!(option.value>0))continue;
    if(!consumers.has(option.itemId))consumers.set(option.itemId,new Map());const rows=consumers.get(option.itemId),row=rows.get(recipe.id)||{recipe,slots:[]};
    if(!row.slots.some(s=>s.index===index))row.slots.push({index,quantity:m.groupId?Math.ceil((m.required??m.qty)/option.value):m.qty,groupId:m.groupId||null,value:option.value,alternative:option.itemId!==m.itemId});rows.set(recipe.id,row);
   }
  }
 }
 const result={schema:'bdo-vision/recipe-network-v1',recipes,spec,byRecipe,byItem,byName,producers,consumers};versions.set(spec,result);return result;
}
function uses(itemId,recipes,spec=EMPTY){
 const db=catalog(recipes,spec),id=Number(itemId);return {itemId:id,producedBy:db.producers.get(id)||[],usedBy:[...(db.consumers.get(id)?.values()||[])],intermediate:db.producers.has(id)&&db.consumers.has(id)};
}
function targets(itemId,recipes,spec=EMPTY,options={}){
 const db=catalog(recipes,spec),source=Number(itemId),maxDepth=Math.min(12,Math.max(1,Number(options.depth)||8)),limit=120,results=[],seenRecipes=new Set(),expanded=new Set([source]);
 const queue=[{itemId:source,path:[],choices:{},seen:new Set([source])}];let truncated=false;
 for(let i=0;i<queue.length;i++){
  const state=queue[i];if(state.path.length>=maxDepth){if(db.consumers.has(state.itemId))truncated=true;continue;}
  const next=[...(db.consumers.get(state.itemId)?.values()||[])].sort((a,b)=>a.recipe.name.localeCompare(b.recipe.name));
  for(const row of next){const r=row.recipe;if(state.seen.has(r.itemId))continue;if(results.length>=limit){truncated=true;break;}
   const choices={...state.choices};for(const slot of row.slots)choices[r.id+':'+slot.index]=state.itemId;
   const path=[...state.path,{recipeId:r.id,inputId:state.itemId,perBatch:row.slots.reduce((n,s)=>n+s.quantity,0)}];
   if(!seenRecipes.has(r.id)){seenRecipes.add(r.id);results.push({recipe:r,path,choices,distance:path.length});}
   if(!expanded.has(r.itemId)){expanded.add(r.itemId);queue.push({itemId:r.itemId,path,choices,seen:new Set([...state.seen,r.itemId])});}
  }
 }
 return {results,truncated};
}
function timeline(graph,plan){
 const grouped=new Map();for(const s of plan.steps){let row=grouped.get(s.recipeId);if(!row){row={recipeId:s.recipeId,name:s.name,type:s.type,batches:0,seconds:0,expected:0,inputs:new Map()};grouped.set(s.recipeId,row);}
  row.batches+=s.batches;row.seconds+=s.seconds;row.expected+=s.expected;for(const m of s.inputs){const old=row.inputs.get(m.itemId);row.inputs.set(m.itemId,{...m,quantity:(old?.quantity||0)+m.quantity});}
 }
 let elapsed=0;const rows=[];for(const id of graph.steps){const row=grouped.get(id);if(!row)continue;rows.push({...row,inputs:[...row.inputs.values()].map(m=>({...m,qty:m.quantity/row.batches})),start:elapsed,end:elapsed+row.seconds,order:rows.length+1});elapsed+=row.seconds;}
 return {rows,seconds:elapsed,warnings:[...graph.warnings,...plan.warnings],estimated:true};
}
root.VisionRecipes={catalog,uses,targets,timeline};if(typeof module!=='undefined'&&module.exports)module.exports=root.VisionRecipes;
})(typeof globalThis!=='undefined'?globalThis:this);
