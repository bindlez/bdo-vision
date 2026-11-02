"""Render the canonical Markdown paper as an accessible standalone static site."""
from pathlib import Path
import html
import re

ROOT=Path(__file__).resolve().parents[1]


def inline(value):
    parts=re.split(r'(\[[^\]]+\]\(https?://[^\s)]+\)|`[^`]+`|\*\*[^*]+\*\*)',value)
    output=[]
    for part in parts:
        match=re.fullmatch(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',part)
        if match:output.append('<a href="'+html.escape(match[2],quote=True)+'">'+html.escape(match[1])+'</a>')
        elif part.startswith('**') and part.endswith('**'):output.append('<strong>'+html.escape(part[2:-2])+'</strong>')
        elif part.startswith('`') and part.endswith('`'):output.append('<code>'+html.escape(part[1:-1])+'</code>')
        else:output.append(html.escape(part))
    return ''.join(output)


def build():
    source=(ROOT/'docs/PROJECT-PAPER.md').read_text(encoding='utf-8')
    sections=[];toc=[];paragraph=[];in_list=False
    def flush():
        if paragraph:sections.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
    for line in source.splitlines()+['']:
        heading=re.match(r'^(#{1,3}) (.+)',line)
        if not line.strip() or heading or line.startswith('- '):flush()
        if in_list and not line.startswith('- '):sections.append('</ul>');in_list=False
        if heading:
            level=len(heading[1]);label=heading[2];anchor=re.sub(r'[^a-z0-9]+','-',label.lower()).strip('-')
            sections.append(f'<h{level} id="{anchor}">'+inline(label)+f'</h{level}>')
            if level==2:toc.append('<a href="#'+anchor+'">'+html.escape(label)+'</a>')
        elif line.startswith('- '):
            if not in_list:sections.append('<ul>');in_list=True
            sections.append('<li>'+inline(line[2:])+'</li>')
        elif line.strip():paragraph.append(line.strip())
    style=""":root{color-scheme:dark;font-family:system-ui,'Segoe UI',sans-serif;background:#0d0a14;color:#e7def0}*{box-sizing:border-box}body{margin:0}a{color:#cba8fc;text-underline-offset:3px}a:focus-visible{outline:2px solid #e3c7ff;outline-offset:4px}.skip{position:absolute;left:10px;top:-50px}.skip:focus{top:10px}aside{position:fixed;inset:0 auto 0 0;width:255px;overflow:auto;padding:32px 22px;border-right:1px solid #352641;background:#130f1d}aside strong{display:block;font-size:13px;letter-spacing:.12em;color:#d3b5fa;margin-bottom:8px}aside p{font-size:12px;line-height:1.6;color:#b2a2c2}nav a{display:block;text-decoration:none;font-size:12px;line-height:1.55;padding:7px 0;color:#bbadcb}nav a:hover{color:#ead8ff}main{max-width:1060px;margin-left:255px;padding:50px 70px 80px}header{border-bottom:1px solid #3b2c4b;padding-bottom:20px;margin-bottom:28px}.kicker{font-size:11px;letter-spacing:.16em;color:#ba96e8}h1{font-size:clamp(30px,4vw,47px);line-height:1.15;letter-spacing:-.04em;font-weight:650;margin:24px 0}h2{font-size:23px;line-height:1.3;margin:48px 0 20px;scroll-margin-top:24px}h3{font-size:19px}p,li{font-size:16px;line-height:1.8;color:#d1c6dc}strong{color:#f0e3fc}li{margin:10px 0}code{font-size:13px;color:#d7baf8;background:#24182f;padding:2px 5px;border-radius:4px}.actions{display:flex;gap:16px;flex-wrap:wrap;font-size:12px}.note{border:1px solid #5c416e;background:#21162c;border-radius:8px;padding:15px;font-size:13px;line-height:1.7;color:#cbb6de}footer{font-size:12px;color:#ac9abb;border-top:1px solid #392847;margin-top:50px;padding-top:22px}@media(max-width:900px){aside{position:static;width:auto;border-bottom:1px solid #352641}aside nav{display:none}main{margin:0;padding:28px 22px 60px}h2{font-size:21px}p,li{font-size:15px}}@media print{aside,.actions{display:none}main{margin:0;padding:0;max-width:none}body{background:white;color:black}p,li,strong,h1,h2,a{color:black}}"""
    document='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'"><title>Learning to Build a Companion · BDO Vision</title><style>'+style+'</style></head><body><a class="skip" href="#paper">Skip to paper</a><aside><strong>VISION / FIELD NOTES</strong><p>A living engineering paper.<br>Fictional narrator. Actual scoped evidence.</p><nav aria-label="Paper contents">'+''.join(toc)+'</nav></aside><main id="paper"><header><span class="kicker">PROJECT PAPER · NOVEMBER 2026</span><p class="note">Written in an explicitly fictional first-person learning-human voice. Measurements and architecture are grounded in project notes; no claim of peer review or universal accuracy.</p><div class="actions"><a href="bdo-vision-project-paper.md" download>Editable Markdown</a><a href="bdo-vision-crafting-demo.html">Try Crafting Studio</a><a href="bdo-vision-cp-demo.html">Explore CP Intelligence</a><a href="https://github.com/bindlez/bdo-vision/tree/gear-planner">Source & handbook</a></div></header>'+''.join(sections)+'<footer>Local-first engineering · no analytics, JavaScript, fonts, tracking pixels, game access or network requests in this paper.</footer></main></body></html>'
    target=ROOT/'demo/bdo-vision-project-paper.html';target.write_text(document,encoding='utf-8')
    (ROOT/'demo/bdo-vision-project-paper.md').write_text(source,encoding='utf-8')
    assert len(re.findall(r' id="',document))==len(set(re.findall(r' id="([^"]+)"',document)))
    print('Project paper built:',len(source.split()),'words;',len(toc),'linked sections')


if __name__=='__main__':build()
