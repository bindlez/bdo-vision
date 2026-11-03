'use strict';
const assert=require('node:assert/strict'),C=require('../desktop/assets/crafting-engine.js');
const meal={id:'meal',itemId:1,name:'Meal',type:'cooking',minProc:2,maxProc:2,mats:[{itemId:3,name:'Grain',qty:5}]};
const box={id:'box',itemId:10,name:'Box',type:'processing',method:'imperial_cooking',minProc:1,maxProc:1,mats:[{itemId:1,name:'Meal',qty:18}]};
const other={...box,id:'box2',mats:[{itemId:2,name:'Other',qty:10}]};
const spec={items:{10:{imperialBase:100}},mastery:{cooking:[{masteryLevel:0,imperialBonus:0}]}};
const recipes=[meal,box,other],quote=(n,id)=>({price:{1:10,2:15,3:2}[id],stock:0});
let r=C.imperialRanks(recipes,spec,quote,{boxes:2});
assert.equal(r.cooking.buy[0].name,'Other'); // cheapest unit price is NOT cheapest box
assert.equal(r.cooking.buy[0].cost,300);assert.equal(r.cooking.buy[1].cost,360);
assert.equal(r.cooking.buy[0].profit,200);assert.equal(r.cooking.buy[0].stock,0);
assert.equal(r.cooking.craft[0].runs,18);assert.equal(r.cooking.craft[0].cost,180);
r=C.imperialRanks(recipes,spec,()=>null);assert.equal(r.cooking.buy[0].cost,null);assert.equal(r.cooking.craft[0].cost,null);
assert.equal(C.imperialRanks(recipes,spec,quote,{tiers:{cooking:99}}).cooking.buy.length,0);
const rare={...meal,rare:{itemId:2,minProc:1,maxProc:1}};
r=C.imperialRanks([rare,other],spec,quote);assert.equal(r.cooking.craft[0].runs,50);assert.equal(r.cooking.craft[0].cost,500);
const fs=require('node:fs'),real=JSON.parse(fs.readFileSync('desktop/assets/recipes.json')),data=JSON.parse(fs.readFileSync('desktop/assets/crafting-data.json'));
const start=performance.now();r=C.imperialRanks(real,data,()=>({price:100}),{boxes:245,tiers:{cooking:9856,alchemy:9871}});
assert(r.cooking.buy.length>0&&r.alchemy.buy.length>0);assert(r.cooking.craft.some(x=>x.cost>0));
for(const type of ['cooking','alchemy'])for(const mode of ['buy','craft']){let known=r[type][mode].filter(x=>x.cost!==null);assert(known.every((x,i)=>!i||x.cost>=known[i-1].cost));}
console.log('Imperial: box-normalized buying, whole crafting batches, rare output, missing prices, tiers and full catalog rankings passed in '+(performance.now()-start).toFixed(1)+' ms.');
