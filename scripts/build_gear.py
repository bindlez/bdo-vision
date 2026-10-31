"""Embed Gear Studio so the existing planner remains a single HTML file."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'bdo-market-intelligence.html'
source=path.read_text(encoding='utf-8')
start='<!-- VISION GEAR STUDIO START -->';end='<!-- VISION GEAR STUDIO END -->'
block=start+'\n<style>\n'+(root/'desktop/assets/gear-planner.css').read_text(encoding='utf-8')+'\n</style>\n<script>\n'+(root/'desktop/assets/gear-planner.js').read_text(encoding='utf-8')+'\n</script>\n'+end
if start in source:
    before,tail=source.split(start,1);_,after=tail.split(end,1);source=before+block+after
else:source=source.replace('</body>',block+'\n</body>')
path.write_text(source,encoding='utf-8')
print('Gear Studio embedded in the existing planner')
