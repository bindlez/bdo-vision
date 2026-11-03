/* Exercise the actual shipped owned blocks. DOM fixture, not visual browser QA. */
'use strict';
const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const nodes=new Map();
class Element{
 constructor(){this.dataset={};this.style={};this.value='';this.checked=false;this.open=false;this.children=[];this.controls=[];}
 set innerHTML(value){this.html=value;this.controls=[];for(const match of value.matchAll(/<(input|select|button|details|div|section|p)\b([^>]*)>/g)){const n=new Element(),attrs=match[2];n.checked=/\bchecked\b/.test(attrs);n.open=/\bopen\b/.test(attrs);for(const a of attrs.matchAll(/([\w-]+)="([^"]*)"/g)){if(a[1].startsWith('data-'))n.dataset[a[1].slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=a[2];else n[a[1]]=a[2];}if(match[1]==='select'){const options=value.slice(match.index+match[0].length,value.indexOf('</select>',match.index));n.value=(options.match(/<option value="([^"]*)" selected/)||options.match(/<option value="([^"]*)"/))?.[1]||'';}if(n.id)nodes.set(n.id,n);this.controls.push(n);}}
 get innerHTML(){return this.html||'';}
 querySelectorAll(selector){if(selector==='details[open]')return this.controls.filter(n=>n.dataset.section&&n.open);if(selector==='details')return this.controls.filter(n=>n.dataset.section);const attr=selector.match(/^\[data-([\w-]+)\]$/);if(attr){const k=attr[1].replace(/-([a-z])/g,(_,c)=>c.toUpperCase());return this.controls.filter(n=>Object.hasOwn(n.dataset,k));}return [];}
 insertBefore(){}querySelector(){return null;}focus(){}setSelectionRange(){}matches(){return false;}
}
for(const id of ['craftDetail','recipeList'])nodes.set(id,new Element());
const recipes=JSON.parse(fs.readFileSync('desktop/assets/recipes.json','utf8')),spec=JSON.parse(fs.readFileSync('desktop/assets/crafting-data.json','utf8')),snapshot=JSON.parse(fs.readFileSync('desktop/assets/demo-market-snapshot.json','utf8'));
let started=null,download=null;const context={console,Map,Set,URL,AbortSignal,structuredClone,RECIPES:recipes,VISION_CRAFT_DATA:spec,region:'na',recipeTab:'alchemy',lastCraftAmount:100,selectedRecipe:recipes.find(r=>r.itemId===678),location:{protocol:'file:',hostname:''},bridgeSelectedOrigin:null,visionMarketById:{},visionMarketByName:{},visionMarketQuoteDetails:{},visionEscape:v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),visionName:n=>n.toLowerCase(),localStorage:{getItem:()=>null,setItem(){}},saveState(){},toast(){},fmtTime:n=>n.toFixed(1)+'s',setTimeout,clearTimeout,document:{getElementById:id=>nodes.get(id)||null,createElement:()=>new Element(),activeElement:new Element(),querySelectorAll:()=>[]},startCraft:(r,n,opts)=>{started={r,n,opts};},intelDownload:(...args)=>{download=args;},openModal(){},closeModal(){}};
context.window=context;for(const q of snapshot.items){context.visionMarketById['na:'+q.id]=q.price;context.visionMarketQuoteDetails['na:'+q.id]=q;}
vm.createContext(context);const html=fs.readFileSync('bdo-market-intelligence.html','utf8');
for(const marker of ['CRAFTING_ENGINE_JS','CRAFTING_STUDIO_JS','RECIPE_BROWSER_JS']){const script=html.split('/* OWNED '+marker+' START */')[1]?.split('/* OWNED '+marker+' END */')[0];assert(script,marker);vm.runInContext(script,context);}
nodes.set('imperialQuick',new Element());
context.craftStudioRender(context.selectedRecipe,100);context.renderRecipeList();
assert(nodes.get('imperialQuick').innerHTML.includes('BEST TO BUY & PACK'));
assert(nodes.get('imperialQuick').innerHTML.includes('BEST TO CRAFT & PACK'));
assert(nodes.get('imperialQuick').innerHTML.includes('BEST TO BUY & PACK · IN STOCK'));
assert(nodes.get('imperialQuick').innerHTML.includes('BEST TO CRAFT & PACK · IN STOCK'));
assert(nodes.get('imperialQuick').innerHTML.includes('Turn-in silver'));
nodes.get('imperialGuruOnly').onchange({target:{checked:true}});assert(context.imperialSettings.guruOnly);
nodes.get('imperialGuruOnly').onchange({target:{checked:false}});assert(!context.imperialSettings.guruOnly);
assert(!nodes.get('imperialAnalysis').innerHTML);
const oldQuote=context.craftStudioQuote;context.craftStudioQuote=()=>({price:100,stock:100000});context.craftImperialRender();
nodes.get('imperialAdvanced').ontoggle({target:{open:true}});
assert(nodes.get('imperialAnalysis').innerHTML.includes('role="img"'));assert(nodes.get('imperialAnalysis').innerHTML.includes('Ingredient'));
nodes.get('imperialCP').onchange({target:{value:'491'}});assert.equal(context.imperialSettings.cp,491);
assert(nodes.get('imperialQuick').innerHTML.includes('245 boxes/day maximum'));
assert(nodes.get('imperialQuick').innerHTML.includes('Daily craft profit'));
const daily=context.VisionCraft.imperialRanks(recipes,spec,context.craftStudioQuote,{boxes:245}).cooking.buy.sort((a,b)=>b.profit-a.profit)[0];
assert(nodes.get('imperialQuick').innerHTML.includes(context.craftStudioMoney(daily.profit)+' potential daily profit'));
nodes.get('imperialCP').onchange({target:{value:'0'}});assert(!nodes.get('imperialQuick').innerHTML.includes('potential daily profit'));
context.craftStudioQuote=oldQuote;context.craftImperialRender();
assert(!nodes.get('imperialQuick').innerHTML.includes('<select'));
assert.equal(nodes.get('imperialQuick').controls.filter(n=>n.id==='imperialMastery').length,1);
nodes.get('imperialMastery').onchange({target:{value:'1500'}});assert.equal(context.imperialSettings.mastery.cooking,1500);
nodes.get('imperialSortCraft').onclick();assert.equal(context.imperialSettings.sort,'craft');
nodes.get('imperialAlchemy').onclick();assert.equal(context.imperialSettings.type,'alchemy');
nodes.get('imperialMastery').onchange({target:{value:'1200'}});assert.equal(context.imperialSettings.mastery.alchemy,1200);
nodes.get('imperialCooking').onclick();assert.equal(context.imperialSettings.mastery.cooking,1500);
assert(nodes.get('craftDetail').innerHTML.includes('EXPECTED NET PROFIT'));assert(nodes.get('craftDetail').innerHTML.includes('choose substitutions'));
nodes.get('studioTarget').onchange({target:{value:'1000'}});assert.equal(context.lastCraftAmount,400);
nodes.get('studioQueue').onclick();assert.equal(context.craftStudioState.queue.length,1);assert.equal(context.craftStudioState.queue[0].amount,400);
nodes.get('studioExport').onclick();assert(download[0].endsWith('.txt'));assert(download[1].includes('Expected plan'));
nodes.get('btnStartCraft').onclick();assert.equal(started.n,400);assert.equal(started.opts.craftPlan.itemId,678);assert(started.opts.craftPlan.materials.every(m=>m.itemId>0));
nodes.get('studioRing').checked=true;nodes.get('studioFame').value='1.5';nodes.get('studioTax').onclick();assert(Math.abs(Number(nodes.get('studioRetention').value)-88.725)<1e-8);
nodes.get('studioFavorite').onclick();assert(context.craftStudioState.favorites.includes(context.selectedRecipe.id));
context.recipeTab='processing';context.renderRecipeList();assert(nodes.get('recipeList').innerHTML.includes('746 matching'));
context.recipeSearch='flax';context.renderRecipeList();assert(nodes.get('recipeList').innerHTML.includes('Flax Fabric'));
context.craftStudioRender({...context.selectedRecipe,name:'<img src=x onerror=alert(1)>'},1);assert(nodes.get('craftDetail').innerHTML.includes('&lt;img'));assert(!nodes.get('craftDetail').innerHTML.includes('<img src=x'));
console.log('Shipped Crafting UI: rendering, target conversion, queue, export, timer linkage, tax, favorites, processing search and escaping passed.');
