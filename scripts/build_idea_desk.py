"""Bundle the standalone offline sideapp. No dependencies or Vision runtime edits."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=root/'sideapps/idea-desk'
html=(source/'index.html').read_text(encoding='utf-8')
for marker,name in [('STYLE','style.css'),('CORE','core.js'),('APP','app.js')]:
    html=html.replace('/* '+marker+' */',(source/name).read_text(encoding='utf-8'))
target=root/'demo/vision-idea-desk.html'
target.write_text(html,encoding='utf-8')
print(target)
