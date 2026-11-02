"""Embed the owned Big Drops assets in the real shipped planner."""
from pathlib import Path
root=Path(__file__).resolve().parents[1];target=root/'bdo-market-intelligence.html'
html=target.read_text(encoding='utf-8')
for kind,extension in (('CSS','css'),('JS','js')):
    start='/* VISION BIG DROPS '+kind+' START */';end='/* VISION BIG DROPS '+kind+' END */'
    content=start+'\n'+(root/f'desktop/assets/big-drops.{extension}').read_text(encoding='utf-8')+'\n'+end
    if start in html:
        a=html.index(start);b=html.index(end,a)+len(end);html=html[:a]+content+html[b:]
    else:
        anchor='</style>' if kind=='CSS' else 'var visionGrindReading=null'
        assert anchor in html;html=html.replace(anchor,content+'\n'+anchor,1)
if 'id="visionBigDrops"' not in html:
    anchor='          <section class="card vision-pursuit">';assert anchor in html
    html=html.replace(anchor,'          <section id="visionBigDrops" aria-label="Big Drops trophy room"></section>\n'+anchor,1)
anchor='  visionGrindReading=reading;var data=reading&&reading.crafting_loot;'
assert anchor in html
if 'renderVisionBigDrops(data&&data.big_drops);' not in html:html=html.replace(anchor,anchor+'\n  renderVisionBigDrops(data&&data.big_drops);',1)
target.write_text(html,encoding='utf-8');print('Big Drops embedded in shipped planner')
