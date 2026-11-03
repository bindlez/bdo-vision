/* Target-first CP view. No I/O, timers, dependencies or ledger writes. */
(function(root){
'use strict';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>v==null?'Unpriced':Math.round(v).toLocaleString();
const colors={catalyst:'#c6a2ff',witch:'#66d8b1',leaf:'#f1bd6d',missing:'#5b5267'};
function lines(plan){
 const w=500,h=220,left=64,right=18,top=18,bottom=35,max=Math.max(1,...plan.lines.flatMap(s=>s.points.map(p=>p.items)));
 const xx=cp=>left+(cp-plan.cp)/Math.max(1,plan.target-plan.cp)*(w-left-right),yy=n=>h-bottom-n/max*(h-top-bottom);
 let svg='<svg viewBox="0 0 500 220" role="img" aria-label="Byproducts required to reach each CP target"><title>Required item quantities at each CP target, one line per byproduct</title>';
 for(let i=0;i<=4;i++){let n=max*i/4;svg+='<line x1="'+left+'" x2="'+(w-right)+'" y1="'+yy(n)+'" y2="'+yy(n)+'" stroke="#3c3347"/><text x="'+(left-7)+'" y="'+(yy(n)+4)+'" text-anchor="end" fill="#c8bdd5" font-size="10">'+fmt(n)+'</text>';}
 for(const s of plan.lines)svg+='<polyline fill="none" stroke="'+colors[s.key]+'" stroke-width="'+(s.key==='catalyst'?4:2)+'" '+(s.key==='witch'?'stroke-dasharray="5 5"':'')+' points="'+s.points.map(p=>xx(p.cp)+','+yy(p.items)).join(' ')+'"><title>'+esc(s.name)+' · '+fmt(s.points.at(-1).items)+' items to target</title></polyline>';
 return svg+'<text x="'+left+'" y="212" fill="#c8bdd5" font-size="11">'+plan.cp+' CP</text><text x="482" y="212" text-anchor="end" fill="#c8bdd5" font-size="11">'+plan.target+' CP</text></svg>';
}
function pie(plan){
 const total=plan.exchangeXp,rows=plan.owned.allocation.map(p=>({key:p.key,name:p.name,xp:p.ownedXp,items:p.batches*p.batch}));
 rows.push({key:'missing',name:'EXP still missing from owned complete bundles',xp:plan.owned.missingXp});
 if(!total)return '<p>Target already reached. No exchanges required.</p>';
 let offset=0,svg='<svg viewBox="0 0 240 220" role="img" aria-label="Owned byproduct contribution to target exchange EXP"><title>Owned EXP allocation and missing EXP for the target</title>';
 for(const r of rows){const amount=r.xp/total*100;if(amount){svg+='<circle cx="120" cy="100" r="65" pathLength="100" fill="none" stroke="'+colors[r.key]+'" stroke-width="34" stroke-dasharray="'+amount+' '+(100-amount)+'" stroke-dashoffset="'+(-offset)+'" transform="rotate(-90 120 100)"><title>'+esc(r.name)+': '+amount.toFixed(1)+'%, '+fmt(r.xp)+' EXP</title></circle>';offset+=amount;}}
 svg+='<text x="120" y="96" text-anchor="middle" fill="#eee3fa" font-size="24">'+(plan.owned.ownedXp/total*100).toFixed(1)+'%</text><text x="120" y="116" text-anchor="middle" fill="#c8bdd5" font-size="11">covered by owned bundles</text></svg>';
 return svg+rows.map(r=>'<p class="cp-target-legend"><i style="background:'+colors[r.key]+'"></i>'+esc(r.name)+' · '+fmt(r.xp)+' EXP ('+(r.xp/total*100).toFixed(1)+'%)</p>').join('');
}
function allocation(route){
 return '<p>'+(route.reachesTarget?'Reaches '+route.result.cp+' CP':'Reaches '+route.result.cp+' CP; '+fmt(route.missingBatches)+' exchanges still missing')+' · '+(route.ownedOnly?'Uses owned items only':'Additional items required')+' · '+fmt(route.opportunityCost)+' silver opportunity cost</p><div class="cp-table-wrap"><table><thead><tr><th>Byproduct</th><th>Turn in</th><th>Bundles</th><th>Additional needed</th><th>Owned left</th><th>EXP</th></tr></thead><tbody>'+route.allocation.map(p=>'<tr><td>'+esc(p.name)+'</td><td>'+fmt(p.items)+'</td><td>'+fmt(p.batches)+'</td><td>'+fmt(p.shortage)+'</td><td>'+fmt(p.leftover)+'</td><td>'+fmt(p.xp)+'</td></tr>').join('')+'</tbody></table></div>';
}
function markup(plan){
 return '<section class="cp-card cp-target"><h2>Reach my target CP</h2><p>Start with the CP you want. Here is exactly what to turn in, using one byproduct or a combination.</p><label class="cp-target-picker">I want <input data-cp="target" type="number" min="0" max="600" value="'+plan.target+'"> CP</label><p><b>'+fmt(plan.requiredXp)+' EXP needed · '+fmt(plan.requiredBatches)+' complete exchanges</b> · from '+plan.cp+' CP + '+plan.percent+'%</p><div class="cp-table-wrap"><table><thead><tr><th>Use this byproduct alone</th><th>Total required</th><th>You own</th><th>Additional needed</th><th>Silver given up</th></tr></thead><tbody>'+plan.singles.map(p=>{const a=p.allocation.find(r=>r.key===p.key);return '<tr><td>'+esc(a.name)+'</td><td><b>'+fmt(a.items)+'</b></td><td>'+fmt(a.owned)+'</td><td>'+fmt(a.shortage)+'</td><td>'+fmt(p.opportunityCost)+'</td></tr>';}).join('')+'</tbody></table></div><h3>Combine byproducts</h3><details open><summary>'+esc(plan.owned.label)+'</summary>'+allocation(plan.owned)+'</details><details><summary>'+esc(plan.completion.label)+'</summary>'+allocation(plan.completion)+'<p>Additional-item type is the lowest quoted opportunity cost among priced options; unpriced alternatives may change that choice. This assumes you obtain the displayed shortage, not that byproducts can be bought on the market.</p></details><details><summary>'+esc(plan.balanced.label)+'</summary>'+allocation(plan.balanced)+'<p>Equal shares of contribution EXP, rounded to complete exchanges. This is a comparison, not a cost-minimum claim.</p></details><div class="cp-chart-grid"><section><h3>Required items by target CP</h3>'+lines(plan)+'<p>'+plan.lines.map(s=>'<span class="cp-target-legend"><i style="background:'+colors[s.key]+'"></i>'+esc(s.name)+'</span>').join(' ')+'</p><small>Catalyst and Delicacy overlap because both exchange 10 items for 900 EXP; the dashed line shows that overlap. Leaf requires 20 items.</small></section><section><h3>What your owned combination covers</h3>'+pie(plan)+'</section></div><p class="cp-status">'+fmt(plan.overshootXp)+' EXP above the exact target after bundle rounding. Full target plan ends at '+plan.finish.cp+' CP'+(plan.finish.percent==null?' (curve limit)': ' + '+plan.finish.percent.toFixed(2)+'%')+'. Missing prices do not hide quantities. No future production, purchases or quest rewards are invented. The current EXP curve is modeled through 600 CP.</p></section>';
}
root.VisionCPTarget={markup};
})(typeof globalThis!=='undefined'?globalThis:this);
