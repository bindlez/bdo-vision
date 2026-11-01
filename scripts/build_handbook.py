"""Build a dependency-free offline documentation site and line-linked source atlas.

Only explicit project source/documentation directories are read. No profiles,
captures, build reports, environment files or user data are included.
"""
import argparse
import ast
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build' / 'developer-handbook'
CODE_EXT = {'.py', '.js', '.css', '.html', '.hpp', '.cpp', '.cmd', '.bat', '.yml'}


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.casefold()).strip('-')


def key(path):
    return str(path.relative_to(ROOT)).replace('\\', '/')


def page_name(path):
    relative = key(path)
    return ('code-' if path.suffix != '.md' else 'guide-') + slug(relative) + '-' + hashlib.sha256(relative.encode()).hexdigest()[:8] + '.html'


def source_files():
    paths = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in CODE_EXT]
    for name in ('desktop', 'scripts', 'tests', 'native', '.github/workflows'):
        paths += [p for p in (ROOT / name).rglob('*') if p.is_file() and p.suffix in CODE_EXT and '__pycache__' not in p.parts]
    return sorted(set(paths))


def symbols(path, text):
    if path.suffix != '.py':
        return [(m[1] or m[2], text[:m.start()].count('\n') + 1) for m in re.finditer(r'(?:function\s+([\w$]+)\s*\(|class\s+([\w$]+))', text)]
    tree = ast.parse(text)
    found = []
    def visit(nodes, prefix=''):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + node.name
                found.append((name, node.lineno))
                if isinstance(node, ast.ClassDef):
                    visit(node.body, name + '.')
    visit(tree.body)
    return found


def build(check=False):
    OUT.mkdir(parents=True, exist_ok=True)
    docs = sorted(set([ROOT / 'README.md', ROOT / 'CHANGELOG.md', ROOT / 'AGENTS.md', *(ROOT / 'docs').rglob('*.md'), ROOT / 'native' / 'README.md']))
    code = source_files()
    pages = {p.resolve(): page_name(p) for p in docs + code}
    search = []
    titles = {}
    for path in docs:
        match = re.search(r'^# (.+)', path.read_text(encoding='utf-8'), re.M)
        titles[path] = match[1] if match else path.stem
    nav = ''.join('<a href="' + pages[p.resolve()] + '">' + html.escape(titles[p]) + '</a>' for p in docs if 'handbook' in p.parts)
    legacy = ''.join('<a href="' + pages[p.resolve()] + '">' + html.escape(titles[p]) + '</a>' for p in docs if 'handbook' not in p.parts)
    sidebar = '<a class="brand" href="index.html">VISION <span>DEVELOPER HANDBOOK</span></a><a href="atlas.html">Code atlas & symbols</a><a href="contracts.html">Generated contracts</a>' + nav + '<details><summary>Release history & specialist guides</summary>' + legacy + '</details>'

    def shell(title, content, subtitle=''):
        return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'self\'; script-src \'self\'; img-src \'self\' data:; connect-src \'none\'; base-uri \'none\'"><title>' + html.escape(title) + ' · Vision Handbook</title><link rel="stylesheet" href="style.css"></head><body><a class="skip" href="#content">Skip to content</a><aside>' + sidebar + '</aside><div class="workspace"><header><label for="search">Search the handbook and code symbols</label><input id="search" type="search" placeholder="Try: durability, loot, backup, GearStore…" autocomplete="off"><div id="results" role="status" aria-live="polite"></div></header><main id="content"><div class="eyebrow">BDO VISION · ' + html.escape((ROOT/'VERSION').read_text().strip()) + '</div>' + ('<p class="subtitle">'+html.escape(subtitle)+'</p>' if subtitle else '') + content + '</main><footer>Offline · no analytics · no game access · generated from this source checkout</footer></div><script src="search-data.js"></script><script src="search.js"></script></body></html>'

    def link(target, current):
        if target.startswith(('https://', 'http://', 'mailto:')):
            return target
        parsed = urlsplit(target)
        if not parsed.path:
            return '#' + parsed.fragment
        resolved = (current.parent / unquote(parsed.path)).resolve()
        result = pages.get(resolved)
        if result:
            return result + ('#' + parsed.fragment if parsed.fragment else '')
        # Historical documents sometimes name artifacts outside the source tree.
        # They remain visible text rather than broken offline links.
        return None

    def inline(text, current):
        pattern = r'(`[^`]+`|\[[^\]]+\]\([^\s)]+\)|\*\*[^*]+\*\*)'
        parts = re.split(pattern, text)
        result = []
        for part in parts:
            if part.startswith('`') and part.endswith('`'):
                result.append('<code>' + html.escape(part[1:-1]) + '</code>')
            elif part.startswith('**') and part.endswith('**'):
                result.append('<strong>' + html.escape(part[2:-2]) + '</strong>')
            elif re.fullmatch(r'\[[^\]]+\]\([^\s)]+\)', part):
                label, target = re.fullmatch(r'\[([^\]]+)\]\(([^\s)]+)\)', part).groups()
                href = link(target, current)
                result.append('<a href="'+html.escape(href, quote=True)+'">'+html.escape(label)+'</a>' if href else html.escape(label)+' <small>(artifact/reference path: '+html.escape(target)+')</small>')
            else:
                result.append(html.escape(part))
        return ''.join(result)

    def markdown(text, current):
        result = []; lines = text.splitlines(); index = 0; toc = []; seen = {}
        while index < len(lines):
            line = lines[index]; index += 1
            if line.startswith('```'):
                block = []
                while index < len(lines) and not lines[index].startswith('```'):
                    block.append(lines[index]); index += 1
                index += 1
                result.append('<pre><code>'+html.escape('\n'.join(block))+'</code></pre>'); continue
            heading = re.match(r'^(#{1,6})\s+(.+)', line)
            if heading:
                level, label = len(heading[1]), heading[2]; anchor = slug(label)
                count = seen.get(anchor, 0); seen[anchor] = count + 1
                if count: anchor += '-' + str(count)
                result.append(f'<h{level} id="{anchor}">'+inline(label,current)+f'<a class="anchor" href="#{anchor}" aria-label="Link to section">#</a></h{level}>')
                if level in (2,3): toc.append('<a href="#'+anchor+'">'+html.escape(label)+'</a>')
            elif not line.strip():
                continue
            elif line.startswith('|'):
                rows = [line]
                while index < len(lines) and lines[index].startswith('|'):
                    rows.append(lines[index]); index += 1
                table = []
                for n,row in enumerate(rows):
                    cells = row.strip('|').split('|')
                    if all(re.fullmatch(r'\s*:?-+:?\s*',c) for c in cells):continue
                    tag = 'th' if n == 0 else 'td'
                    table.append('<tr>'+''.join('<'+tag+'>'+inline(c.strip(),current)+'</'+tag+'>' for c in cells)+'</tr>')
                result.append('<div class="table"><table>'+''.join(table)+'</table></div>')
            elif re.match(r'^\s*(?:[-*]|\d+\.)\s', line):
                items = [line]
                while index < len(lines) and re.match(r'^\s*(?:[-*]|\d+\.)\s',lines[index]):
                    items.append(lines[index]); index += 1
                result.append('<ul>'+''.join('<li>'+inline(re.sub(r'^\s*(?:[-*]|\d+\.)\s','',item),current)+'</li>' for item in items)+'</ul>')
            else:
                paragraph = [line]
                while index < len(lines) and lines[index].strip() and not re.match(r'^(?:#|```|\||[-*] |\d+\. )',lines[index]):
                    paragraph.append(lines[index]); index += 1
                result.append('<p>'+inline(' '.join(paragraph),current)+'</p>')
        return ('<details class="toc" open><summary>On this page</summary>'+''.join(toc)+'</details>' if toc else '')+''.join(result)

    inventory = []; tables = []; routes = set(); settings = {}
    imports = {}
    for path in code:
        imports[path] = set()
        if path.suffix != '.py':continue
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            names = [node.module] if isinstance(node,ast.ImportFrom) and node.module else [alias.name for alias in node.names] if isinstance(node,ast.Import) else []
            for name in names:
                relative = Path(*name.split('.')).with_suffix('.py')
                candidates = [path.parent/relative,ROOT/'desktop'/relative,ROOT/relative]
                target = next((p for p in candidates if p in code),None)
                if target and target != path:imports[path].add(target)
    for path in code:
        text = path.read_text(encoding='utf-8-sig'); name = key(path); entries = symbols(path,text)
        inventory.append({'path':name,'lines':len(text.splitlines()),'bytes':len(text.encode()),'imports':sorted(key(p) for p in imports[path]),'symbols':[{'name':n,'line':line} for n,line in entries]})
        description = ''
        if path.suffix == '.py':
            tree = ast.parse(text); description = ast.get_docstring(tree) or ''
            for node in ast.walk(tree):
                if isinstance(node,ast.Constant) and isinstance(node.value,str) and re.match(r'CREATE (?:TABLE|INDEX)',node.value,re.I):
                    tables.append((name,node.lineno,node.value))
            for match in re.finditer(r'\b(?:settings|cfg|config)\.get\([\'"]([^\'"]+)[\'"]',text):
                settings.setdefault(match[1],set()).add(name)
        if name == 'desktop/planner_bridge.py':
            routes.update(re.findall(r'[\'"](/[-a-zA-Z0-9/]+)[\'"]',text))
        content = '<h1>'+html.escape(name)+'</h1><p>'+html.escape(description)+'</p><p>'+str(len(text.splitlines()))+' lines · '+str(len(text.encode()))+' bytes · read-only snapshot; edit the source file in your checkout.</p>'
        users = sorted(p for p in code if path in imports[p])
        for label,related in [('Imports project modules',sorted(imports[path])),('Imported by',users)]:
            if related:content += '<p><strong>'+label+':</strong> '+', '.join('<a href="'+pages[p.resolve()]+'">'+html.escape(key(p))+'</a>' for p in related)+'</p>'
        content += '<details class="toc"><summary>Symbols ('+str(len(entries))+')</summary>'+''.join('<a href="#L'+str(line)+'">'+html.escape(n)+'</a>' for n,line in entries)+'</details>'
        content += '<div class="source"><pre>'+''.join('<span id="L'+str(i)+'"><a class="line" href="#L'+str(i)+'">'+str(i)+'</a>'+html.escape(line)+'\n</span>' for i,line in enumerate(text.splitlines(),1))+'</pre></div>'
        (OUT/pages[path.resolve()]).write_text(shell(name,content),encoding='utf-8')
        search.append({'title':name,'url':pages[path.resolve()],'body':description+' '+ ' '.join(n for n,_ in entries)})
        search.extend({'title':name+' → '+n,'url':pages[path.resolve()]+'#L'+str(line),'body':n} for n,line in entries)

    for path in docs:
        text = path.read_text(encoding='utf-8')
        (OUT/pages[path.resolve()]).write_text(shell(titles[path],markdown(text,path)),encoding='utf-8')
        search.append({'title':titles[path],'url':pages[path.resolve()],'body':text})

    atlas = '<h1>Code atlas</h1><p>Every production module, script, test, native experiment and workflow is linked to a line-numbered source snapshot. JSON catalogs and generated binaries are deliberately excluded.</p>'
    atlas += '<table><tr><th>File</th><th>Lines</th><th>Symbols</th></tr>'+''.join('<tr><td><a href="'+pages[(ROOT/row['path']).resolve()]+'">'+html.escape(row['path'])+'</a></td><td>'+str(row['lines'])+'</td><td>'+str(len(row['symbols']))+'</td></tr>' for row in inventory)+'</table>'
    (OUT/'atlas.html').write_text(shell('Code atlas',atlas),encoding='utf-8')
    contracts = '<h1>Generated contracts</h1><p>These are literal references extracted from the checked-out source, not a claim that all dynamic settings or schema migrations can be inferred statically. Follow each source link for validation and default behavior.</p><h2 id="routes">Bridge route names</h2><p>'+', '.join('<code>'+html.escape(route)+'</code>' for route in sorted(routes))+'</p><h2 id="settings">Settings keys read by literal lookup</h2><table><tr><th>Key</th><th>Source</th></tr>'
    for setting,paths in sorted(settings.items()):
        contracts += '<tr><td><code>'+html.escape(setting)+'</code></td><td>'+', '.join('<a href="'+pages[(ROOT/p).resolve()]+'">'+html.escape(p)+'</a>' for p in sorted(paths))+'</td></tr>'
    contracts += '</table><h2 id="schema">SQLite declarations</h2>'
    for name,line,sql in tables:
        contracts += '<p><a href="'+pages[(ROOT/name).resolve()]+'#L'+str(line)+'">'+html.escape(name)+':'+str(line)+'</a></p><pre><code>'+html.escape(sql)+'</code></pre>'
    contracts += '<h2 id="catalogs">Bundled JSON asset shapes</h2><p>Only repository assets are summarized here. These are bundled data, not live market quotes; examples are structural samples and do not establish recipe completeness or current prices.</p>'
    for path in sorted((ROOT/'desktop/assets').glob('*.json')):
        raw=path.read_bytes();data=json.loads(raw)
        sample=data[:2] if isinstance(data,list) else {k:(v[:1] if isinstance(v,list) else v) for k,v in list(data.items())[:8]} if isinstance(data,dict) else data
        contracts += '<h3>'+html.escape(key(path))+'</h3><p>'+str(len(raw))+' bytes · top-level '+type(data).__name__+' · '+str(len(data) if isinstance(data,(dict,list)) else 1)+' entries · SHA-256 '+hashlib.sha256(raw).hexdigest()+'</p><pre><code>'+html.escape(json.dumps(sample,indent=2,ensure_ascii=False)[:4000])+'</code></pre>'
    (OUT/'contracts.html').write_text(shell('Generated contracts',contracts),encoding='utf-8')
    cards = ''.join('<a class="card" href="'+pages[p.resolve()]+'"><strong>'+html.escape(titles[p])+'</strong><span>'+html.escape(key(p))+'</span></a>' for p in docs if 'handbook' in p.parts)
    version = (ROOT/'VERSION').read_text().strip()
    revision = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
    dirty = bool(subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True).stdout.strip())
    intro = '<h1>Make Vision your own.</h1><p class="lead">The complete developer field guide: understand the app, change it safely, and ship a version you can trust.</p><div class="metrics"><span>'+str(len(inventory))+' source files</span><span>'+str(sum(len(r['symbols']) for r in inventory))+' indexed symbols</span><span>'+str(len(docs))+' guides</span><span>Zero website dependencies</span></div><p>Version '+html.escape(version)+' · source '+html.escape(revision[:12])+(' · working changes included' if dirty else ' · committed checkout')+'. This is documentation and source reference, not a live game dashboard.</p><div class="cards">'+cards+'</div>'
    (OUT/'index.html').write_text(shell('Developer Handbook',intro),encoding='utf-8')
    (OUT/'inventory.json').write_text(json.dumps({'version':version,'commit':revision,'uncommitted_source':dirty,'files':inventory},indent=2),encoding='utf-8')
    safe_json = json.dumps(search,ensure_ascii=True).replace('<','\\u003c')
    (OUT/'search-data.js').write_text('window.VISION_DOCS='+safe_json+';',encoding='utf-8')
    (OUT/'search.js').write_text("""'use strict';
const input=document.getElementById('search'),out=document.getElementById('results');
input.addEventListener('input',()=>{out.replaceChildren();const q=input.value.trim().toLowerCase();if(q.length<2)return;
const terms=q.split(/\\s+/);const rows=window.VISION_DOCS.map(r=>({r,t:r.title.toLowerCase(),b:r.body.toLowerCase()})).filter(x=>terms.every(t=>(x.t+' '+x.b).includes(t))).sort((a,b)=>Number(b.t.includes(q))-Number(a.t.includes(q))).slice(0,18);
if(!rows.length){out.textContent='No matches. Try a module or feature name.';return;}for(const {r} of rows){const a=document.createElement('a');a.href=r.url;a.textContent=r.title;out.append(a);}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){input.value='';out.replaceChildren();input.blur();}if(e.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();input.focus();}});
""",encoding='utf-8')
    (OUT/'style.css').write_text(STYLE,encoding='utf-8')
    validate_links(OUT)
    print(f'Handbook: {OUT / "index.html"}')
    print(f'{len(docs)} guides; {len(code)} source pages; {len(search)} search entries; local links verified')
    return inventory


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ids=set()
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.add(attrs['id'])
        if tag in ('a','link','script'):
            value=attrs.get('href') or attrs.get('src')
            if value:self.links.append(value)


def validate_links(folder):
    parsed={}
    for path in folder.glob('*.html'):
        parser=Links();parser.feed(path.read_text(encoding='utf-8'));parsed[path.resolve()]=parser
    errors=[]
    for path,parser in parsed.items():
        for value in parser.links:
            url=urlsplit(value)
            if url.scheme or url.netloc:continue
            target=(path.parent/unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(folder.resolve()):errors.append(f'{path.name}: outside site {value}');continue
            if not target.is_file():errors.append(f'{path.name}: missing {value}')
            elif url.fragment and target in parsed and unquote(url.fragment) not in parsed[target].ids:
                errors.append(f'{path.name}: missing section {value}')
    if errors:raise ValueError('\n'.join(errors[:30]))


STYLE = '''
:root{color-scheme:dark;--bg:#0b0a10;--panel:#15121e;--text:#eeeaf7;--muted:#b1a8c7;--accent:#c9a7ff;--line:#30283f}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.75 "Segoe UI",system-ui,sans-serif}a{color:var(--accent);text-underline-offset:4px}a:hover{color:#fff}a:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:4px}aside{position:fixed;inset:0 auto 0 0;width:290px;padding:30px 20px;background:#100e17;border-right:1px solid var(--line);overflow:auto}aside a{display:block;color:var(--muted);font-size:13px;line-height:1.5;padding:8px 10px;text-decoration:none;border-radius:7px}aside a:hover{background:#241a35}aside .brand{font-weight:750;color:#fff;font-size:24px;letter-spacing:.08em;margin-bottom:25px}.brand span{display:block;color:var(--accent);font-size:10px;letter-spacing:.17em}.workspace{margin-left:290px}header{position:sticky;top:0;padding:16px 4vw;background:#0b0a10f5;border-bottom:1px solid var(--line);z-index:2}header label{display:block;font-size:11px;letter-spacing:.08em;color:var(--muted);margin-bottom:5px}input{background:var(--panel);border:1px solid #49375f;border-radius:9px;color:var(--text);padding:12px 16px;width:min(100%,760px);font:inherit;font-size:14px}#results:empty{display:none}#results{position:absolute;max-height:65vh;overflow:auto;background:#1c1528;border:1px solid #57436e;box-shadow:0 15px 60px #0009;width:min(760px,85%);border-radius:9px;padding:10px}#results a{display:block;padding:9px 12px;text-decoration:none;line-height:1.4;font-size:14px}#results a:hover{background:#352345}main{max-width:1160px;margin:auto;padding:48px 4vw 70px}h1{font-size:clamp(30px,4vw,52px);line-height:1.15;letter-spacing:-.035em;margin:18px 0 28px;overflow-wrap:anywhere}h2{font-size:26px;line-height:1.4;margin-top:50px;border-top:1px solid var(--line);padding-top:22px}h3{font-size:20px;margin-top:32px}p,li{color:#d3cce1}p{max-width:90ch}strong{color:#faf6ff}.lead{font-size:21px;color:#bfb1d4;max-width:65ch}.eyebrow{font-size:11px;color:var(--accent);letter-spacing:.16em;font-weight:700}.metrics{display:flex;flex-wrap:wrap;gap:9px;margin:28px 0}.metrics span{border:1px solid #473354;background:#1d1528;border-radius:20px;padding:5px 12px;font-size:12px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:35px}.card{display:flex;flex-direction:column;gap:10px;padding:23px;background:linear-gradient(140deg,#1d162a,#121019);border:1px solid #3e2f51;border-radius:12px;text-decoration:none;transition:border-color .15s}.card:hover{border-color:var(--accent)}.card strong{font-size:17px;line-height:1.4}.card span{font-size:11px;color:var(--muted)}code{background:#21182e;color:#e2cfff;border-radius:4px;padding:2px 5px;font:13px/1.6 Consolas,monospace;overflow-wrap:anywhere}pre{background:#14101d;border:1px solid #352740;padding:20px;border-radius:9px;overflow:auto;font:13px/1.65 Consolas,monospace}pre code{background:none;padding:0;color:#e3dbed;white-space:pre;overflow-wrap:normal}table{border-collapse:collapse;width:100%;font-size:13px;margin:20px 0}th,td{text-align:left;padding:12px;border-bottom:1px solid var(--line);vertical-align:top}th{color:#ead9ff;background:#1b1425}td{overflow-wrap:anywhere}.table{overflow:auto}.toc{border:1px solid var(--line);background:#15111d;padding:14px 18px;border-radius:9px;margin:25px 0}.toc a{display:block;font-size:13px;padding:3px 0}summary{cursor:pointer;color:var(--muted);font-size:13px}aside details{margin-top:18px}.anchor{font-size:14px;text-decoration:none;margin-left:12px;opacity:.5}footer{border-top:1px solid var(--line);padding:20px 4vw;color:var(--muted);font-size:11px}.source pre{padding:16px 0;max-height:none}.source span{display:block;white-space:pre;min-height:1.65em}.source span:target{background:#3a274e}.line{display:inline-block;width:64px;color:#a590bc;text-align:right;padding-right:18px;text-decoration:none;user-select:none}.source span:not(:target):hover{background:#1d1728}.skip{position:fixed;left:320px;top:-100px;padding:10px;background:#32213e;z-index:5}.skip:focus{top:8px}h1,h2,h3,span[id]{scroll-margin-top:120px}@media(max-width:900px){aside{position:static;width:auto;max-height:260px;border-bottom:1px solid var(--line)}aside .brand{margin-bottom:10px}aside>a:not(.brand){display:inline-block}.workspace{margin:0}header{position:relative}main{padding:28px 20px}.skip{left:15px}}@media print{aside,header,footer,.toc{display:none}.workspace{margin:0}body{background:white;color:black}p,li,strong,h1,h2,h3{color:black}main{padding:0;max-width:none}a{color:#50306b}.cards{display:block}.card{break-inside:avoid;margin:10px 0;background:white}}
'''


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Build and validate every local file and section link')
    build(parser.parse_args().check)
