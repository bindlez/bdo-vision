'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{
 constructor(){this.children=new Map();this.hidden=false;this.open=false;}
 querySelector(key){if(!this.children.has(key))this.children.set(key,new Node());return this.children.get(key);}
 prepend(n){nodes.set(n.id,n);}
}
const nodes=new Map(),panel=new Node(),context={console,document:{getElementById:id=>nodes.get(id),createElement:()=>new Node()},region:'na',RECIPES:[],craftStudioGraph:()=>'<svg>actual series</svg>',craftStudioPie:()=>'<svg>priced breakdown</svg>'};
vm.createContext(context);vm.runInContext(fs.readFileSync('desktop/assets/crafting-loot-view.js','utf8'),context);
context.renderVisionAutomaticCraft(panel,null);assert.equal(nodes.size,0);
const payload={detected:true,recipe:'<img src=x>',kind:'alchemy',status:'Capture paused',recordedValue:123,recordedPerHour:456,units:4,nextGoal:100,unpriced:[],scannedActions:3000,model:{perHour:500,toolValue:999,mastery:0,retention:84.5},items:[{item:'Elixir',value:123}],points:[[0,0],[60,123]]};
context.renderVisionAutomaticCraft(panel,payload,{guild_status:{complete:true,available:false}});const card=nodes.get('visionAutomaticCraft');assert.equal(card.querySelector('[data-auto-title]').textContent,'<img src=x> · alchemy');assert.equal(card.querySelector('[data-auto-rate]').textContent,'456');assert.equal(card.querySelector('[data-auto-tool]').textContent,'999');assert(!card.querySelector('[data-auto-graphs]').innerHTML);
assert(card.querySelector('[data-auto-guild]').textContent.includes('complete'));assert(card.querySelector('[data-auto-end]').textContent);
card.querySelector('details').open=true;card.querySelector('details').ontoggle();assert(card.querySelector('[data-auto-graphs]').innerHTML.includes('actual series'));assert(card.querySelector('[data-auto-details]').textContent.includes('10 observed seconds'));
context.renderVisionAutomaticCraft(panel,null);assert(card.hidden);
console.log('Automatic craft: no manual recipe, displayed rates/tool projection, paused status, text-safe names and lazy charts passed');

let opened=null,workspace=null;context.RECIPES=[{id:'wine',name:'Fruit Wine',type:'cooking'}];context.selectRecipe=id=>{opened=id;};context.craftWorkflowSet=mode=>{workspace=mode;};
context.renderVisionAutomaticCraft(panel,{...payload,recipe:'Fruit Wine',kind:'cooking'});assert(!card.querySelector('[data-auto-map]').disabled);card.querySelector('[data-auto-map]').onclick();assert.equal(opened,'wine');assert.equal(workspace,'planner');

// Fresh connection packets do not turn missing OCR into a verified tool or quest.
let status=context.visionCraftStatusModel({companion:{updated_at:100,has_reading:false}},100);
assert.equal(status.tool,'WAITING FOR TOOL');assert.equal(status.loot,'LOOT SHARING OFF');
status=context.visionCraftStatusModel({companion:{updated_at:100,observed_at:90,has_reading:true,remaining:382,seconds:1,running:true,name:'Alchemy tool'},guild_status:{available:true,last_at:99,current:101,target:600},crafting_loot:{available:true,health:{holes:1,uncertain:2},auto_craft:{detected:true,recipe:'Fruit Wine',status:'Measured'}}},101);
assert.equal(status.timer,382);assert.equal(status.tool,'COUNTDOWN ESTIMATE');assert.equal(status.guild,'101 / 600');assert(status.lootNote.includes('unreadable'));assert(status.lootNote.includes('overlap lost'));assert.equal(status.craft,'Fruit Wine');
status=context.visionCraftStatusModel({companion:{updated_at:100,has_reading:true,remaining:382,seconds:1,running:true},guild_status:{complete:true,available:false,completion_seen_at:1}},200);
assert.equal(status.tool,'WAITING FOR TOOL');assert(status.guild.startsWith('Last seen complete'));
console.log('Craft status: tool estimates, capture gaps, optional sharing and stale quest distinctions passed');

status=context.visionCraftStatusModel({guild_status:{available:false,last_at:1,current:501,target:600}},200);assert.equal(status.guild,'501 / 600 / last seen');

context.renderVisionAutomaticCraft(panel,payload,{companion:{updated_at:Date.now()/1000,has_reading:true,remaining:382,seconds:1,running:true}});assert(card.querySelector('[data-auto-end]').textContent.startsWith('0:06:22'));// Actual countdown, not only a status label.
