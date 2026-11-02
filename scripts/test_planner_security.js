// Exercise actual rendering functions with hostile item text, without a browser.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(require('path').join(__dirname,'../bdo-market-intelligence.html'),'utf8');
function body(name){
 const start=source.indexOf('function '+name+'(');assert(start>=0,name);
 const next=source.indexOf('\n    function ',start+1);
 return source.slice(start,next<0?source.indexOf('\nfunction ',start+1):next);
}
const escaped=source.match(/function visionEscape\(value\)\{[^\n]+/)[0];
const elements=new Map(),created=[];
function element(){return {innerHTML:'',textContent:'',classList:{remove(){},add(){}},scrollIntoView(){},appendChild(){},offsetWidth:0};}
const context={document:{getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);},createElement(){const node=element();created.push(node);return node;}},
 fmt:String,stockClass:()=>'',changeHtml:()=>'',updateHeroStats(){},CATEGORIES:{},activeCat:0,setTimeout(){}};
vm.createContext(context);
vm.runInContext(escaped+'\n'+['renderPopular','renderListings','renderHotSidebar','toast'].map(body).join('\n'),context);
const hostile='"><img src=x onerror="globalThis.injected=true"> & loot';
context.item={name:hostile,price:123,stock:1,trades:1,changeDir:0};
context.getFiltered=()=>[context.item];
vm.runInContext('renderPopular([item]);renderListings();renderHotSidebar([item]);toast(item.name,item.name,false)',context);
for(const id of ['popularGrid','listingsBody','hotList']){
 const rendered=elements.get(id).innerHTML;
 assert(!rendered.includes('<img'),id+' allows an element injection');
 assert(rendered.includes('&lt;img'),id+' does not preserve escaped text');
 assert(rendered.includes('&quot;'),id+' does not escape attribute quotes');
}
assert.strictEqual(context.injected,undefined);
assert(created[0].innerHTML.includes('&lt;img')&&!created[0].innerHTML.includes('<img'),'toast allows markup injection');
vm.runInContext(body('visionGuildLastSeenHTML'),context);
context.questTimer={guildQuestLastSeen:{current:49,target:600,last_at:100,objective:hostile}};
vm.runInContext('guildMarkup=visionGuildLastSeenHTML(questTimer)',context);
assert(context.guildMarkup.includes('Last seen 49 / 600'));
assert(context.guildMarkup.includes('&lt;img')&&!context.guildMarkup.includes('<img'));
context.questTimer={guildQuestLastSeen:{current:599,target:600,last_at:100,complete:true,completion_at:110,objective:hostile}};
vm.runInContext('guildMarkup=visionGuildLastSeenHTML(questTimer)',context);
assert(context.guildMarkup.includes('Guild quest: Complete'));
assert(context.guildMarkup.includes('last counter 599 / 600')&&!context.guildMarkup.includes('600 / 600'));
assert(context.guildMarkup.includes('&lt;img')&&!context.guildMarkup.includes('<img'));
context.questTimer={guildQuestLastSeen:{current:null,target:null,last_at:null,complete:true,completion_at:110}};
vm.runInContext('guildMarkup=visionGuildLastSeenHTML(questTimer)',context);
assert(context.guildMarkup.includes('Guild quest: Complete')&&!context.guildMarkup.includes('0 / 0'));
console.log('Planner security: market names render as text in popular, listings, sidebar and toast functions.');
