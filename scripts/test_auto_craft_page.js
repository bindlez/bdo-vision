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
context.renderVisionAutomaticCraft(panel,payload);const card=nodes.get('visionAutomaticCraft');assert.equal(card.querySelector('[data-auto-title]').textContent,'<img src=x> · alchemy');assert.equal(card.querySelector('[data-auto-rate]').textContent,'456');assert.equal(card.querySelector('[data-auto-tool]').textContent,'999');assert(!card.querySelector('[data-auto-graphs]').innerHTML);
card.querySelector('details').open=true;card.querySelector('details').ontoggle();assert(card.querySelector('[data-auto-graphs]').innerHTML.includes('actual series'));assert(card.querySelector('[data-auto-details]').textContent.includes('60 observed seconds'));
context.renderVisionAutomaticCraft(panel,null);assert(card.hidden);
console.log('Automatic craft: no manual recipe, displayed rates/tool projection, paused status, text-safe names and lazy charts passed');
