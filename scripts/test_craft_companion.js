'use strict';const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const C=require('../desktop/assets/crafting-engine.js'),R=require('../desktop/assets/recipe-network.js');
const recipes=JSON.parse(fs.readFileSync('desktop/assets/recipes.json','utf8')),spec=JSON.parse(fs.readFileSync('desktop/assets/crafting-data.json','utf8'));
const index=C.indexRecipes(recipes,spec),cfg=r=>C.configure(r,{retention:84.5,mastery:1000},spec);
const ctx={VisionCraft:C,RECIPES:recipes,VISION_CRAFT_DATA:spec,craftRecipeIndex:index,craftStudioConfig:cfg,craftStudioContext:()=>({spec,recipes,index,quote:()=>({price:100}),configFor:cfg}),document:{getElementById:()=>null},console};ctx.window=ctx;vm.createContext(ctx);vm.runInContext(fs.readFileSync('desktop/assets/crafting-loot-view.js','utf8'),ctx);
const recipe=recipes.find(r=>r.id==='recipe:820831:8dd94cf6d723');assert(recipe);
const q={recipe:recipe.id,maximum:100000,current:0,reserve:0,tool:1000,seconds:1,limit:'hybrid',amounts:{}};
let result=ctx.visionCraftPanelCalculate(q);assert.equal(result.maxCrafts,1000);assert.equal(result.batches,1000);assert.equal(result.seconds,1000);assert(result.fits);
const first=result.rows[0],second=result.rows[1];q.anchor=first.id;q.amounts={[first.id]:first.ratio*1400};result=ctx.visionCraftPanelCalculate(q);assert.equal(result.batches,1400);assert(!result.fits);assert.equal(result.rows[1].quantity,second.ratio*1400);
q.independent=true;q.amounts={[first.id]:first.ratio*100,[second.id]:second.ratio*60};result=ctx.visionCraftPanelCalculate(q);assert.equal(result.batches,60);assert.equal(result.rows[0].leftover,first.ratio*40);assert.equal(result.seconds,60);
q.amounts[first.id]='broken';assert.throws(()=>ctx.visionCraftPanelCalculate(q));q.amounts[first.id]=1.5;assert.throws(()=>ctx.visionCraftPanelCalculate(q));
q.independent=false;q.anchor=null;q.maximum=null;assert.throws(()=>ctx.visionCraftPanelCalculate(q));q.maximum=100000;q.tool=null;assert.throws(()=>ctx.visionCraftPanelCalculate(q));
q.limit='ingredients';assert(ctx.visionCraftPanelCalculate(q).maxCrafts>1000);
const html=fs.readFileSync('fairycodex.html','utf8'),a=html.indexOf('const CATALOG='),b=html.indexOf('\n];',a)+3,fc={};vm.createContext(fc);vm.runInContext(html.slice(a,b)+';globalThis.catalog=CATALOG;',fc);assert.deepEqual(JSON.parse(JSON.stringify(fc.catalog)),JSON.parse(fs.readFileSync('desktop/assets/fairy-catalog.json','utf8')));
const shipped=fs.readFileSync('bdo-market-intelligence.html','utf8');assert(shipped.includes('function visionCraftPanelCalculate'));
console.log('Craft companion: shared model, ratios, independent limits, native cadence, missing inputs and Fairy catalog parity passed.');

(async()=>{
 const replies=[];ctx.bridgeSelectedOrigin='http://127.0.0.1';ctx.AbortSignal=AbortSignal;ctx.activeTimers=[];let starts=0;ctx.saveState=()=>{};
 ctx.startCraft=(r,n)=>{starts++;ctx.activeTimers.unshift({recipeId:r.id,status:'running',amount:n});};
 ctx.fetch=async(url,opts)=>{replies.push(JSON.parse(opts.body));return {ok:true};};
 const request={recipe:recipe.id,maximum:1000,current:0,reserve:0,tool:100,seconds:1,limit:'hybrid',amounts:{},start:true,id:'one-shot',created:Date.now()/1000};
 await ctx.visionCraftPanelReply({instance_id:'test',craft_panel_request:request});assert.equal(starts,1);assert(replies.at(-1).result.timerStarted);
 ctx.visionPanelHandled=null;await ctx.visionCraftPanelReply({instance_id:'test',craft_panel_request:request});assert.equal(starts,1,'retry must not start another timer');
 await ctx.visionCraftPanelReply({instance_id:'test',craft_panel_request:{...request,id:'expired',created:1}});assert.equal(starts,1);assert(replies.at(-1).result.error.includes('expired'));
 console.log('Companion timer: explicit start, retry deduplication and expired-action rejection passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
