'use strict';
const assert=require('node:assert/strict'),N=require('../desktop/assets/recipe-network.js'),C=require('../desktop/assets/crafting-engine.js'),recipes=require('../desktop/assets/recipes.json'),spec=require('../desktop/assets/crafting-data.json');
const db=N.catalog(recipes,spec);assert.equal(db.byRecipe.size,recipes.length);assert.equal(N.catalog(recipes,spec),db,'reuse one pair of immutable catalog/spec indexes');
const wine=recipes.find(r=>r.name==='Fruit Wine'),bal=recipes.find(r=>r.name==='Balenos Meal'),ser=recipes.find(r=>r.name==='Serendia Meal'),cheese=recipes.find(r=>r.name==='Cheese'),gratin=recipes.find(r=>r.name==='Cheese Gratin');
assert(N.uses(wine.itemId,recipes,spec).usedBy.some(c=>c.recipe.id===ser.id));assert(!N.targets(wine.itemId,recipes,spec).results.some(t=>t.recipe.id===bal.id),'do not invent a Wine -> Balenos connection');
const cheeseRoute=N.targets(cheese.itemId,recipes,spec).results.find(t=>t.recipe.id===bal.id);assert(cheeseRoute);assert(cheeseRoute.path.some(s=>s.recipeId===gratin.id)||cheeseRoute.path.some(s=>recipes.find(r=>r.id===s.recipeId)?.name==='Meat Croquette'));
assert(N.uses(wine.rare.itemId,recipes,spec).producedBy.some(p=>p.recipe===wine&&p.kind==='rare'));
for(const r of recipes){assert(db.producers.get(r.itemId).some(p=>p.recipe===r&&p.kind==='main'));for(const m of r.mats)assert(db.consumers.get(m.itemId)?.has(r.id),r.name+' input must be reverse indexed');}
const variant={id:'v',itemId:2,name:'Product',mats:[{itemId:10,name:'Ordinary',qty:6,required:6,groupId:1}]},list=[variant],a={groups:{1:[{itemId:10,value:1},{itemId:11,value:3}]}},b={groups:{1:[{itemId:10,value:1},{itemId:12,value:2}]}};
assert.equal(N.uses(11,list,a).usedBy[0].slots[0].quantity,2);assert.equal(N.uses(11,list,b).usedBy.length,0,'group indexes must be keyed by spec as well as recipes');assert(N.targets(11,list,a).results[0].choices['v:0']===11);
const p1={id:'a',itemId:100,name:'A',minProc:1,maxProc:1,mats:[{itemId:101,name:'B',qty:1}]},p2={id:'b',itemId:101,name:'B',minProc:1,maxProc:1,mats:[{itemId:100,name:'A',qty:1}]};assert(N.targets(100,[p1,p2]).results.length<=1,'cycle traversal terminates');
const sourceBefore=JSON.stringify(recipes),ctx={recipes,spec,index:C.indexRecipes(recipes,spec),make:{},quote:()=>({price:100})};
const graph=C.productionGraph(ser,ctx),made={};for(const n of graph.nodes)if(n.kind==='recipe')made[C.key(n.recipe.name)]=true;
const plan=C.plan(ser,100,{}, {...ctx,make:made}),timeline=N.timeline(graph,plan);
assert.equal(timeline.seconds,plan.seconds);assert(timeline.rows.findIndex(s=>s.recipeId===wine.id)<timeline.rows.findIndex(s=>s.recipeId===ser.id));
assert.equal(new Set(timeline.rows.map(r=>r.recipeId)).size,timeline.rows.length);
for(let i=0;i<timeline.rows.length;i++){const r=timeline.rows[i];assert.equal(r.order,i+1);assert.equal(r.end-r.start,r.seconds);if(i)assert.equal(r.start,timeline.rows[i-1].end);}
assert.equal(JSON.stringify(recipes),sourceBefore,'building relationships/timelines must not modify recipe records');
const duplicate={id:'dup',itemId:10,name:'Duplicate inputs',mats:[{itemId:1,name:'Raw',qty:1},{itemId:1,name:'Raw',qty:2}],minProc:1,maxProc:1};
const duplicatePlan=C.plan(duplicate,4,{}, {recipes:[duplicate],quote:()=>({price:1})}),duplicateTime=N.timeline(C.productionGraph(duplicate,{recipes:[duplicate]}),duplicatePlan);
assert.equal(duplicateTime.rows[0].inputs.length,1);assert.equal(duplicateTime.rows[0].inputs[0].quantity,12);assert.equal(duplicateTime.rows[0].inputs[0].qty,3);
console.log('Recipe network: all 990 variants reverse-linked; normal/rare outputs, substitutions, Wine/Meal facts, cached indexes, bounded cycles and sequential timeline passed.');
