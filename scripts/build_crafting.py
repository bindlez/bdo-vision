"""Embed owned crafting assets. Generated HTML is never a second source of truth."""
from pathlib import Path
import re
import json

ROOT = Path(__file__).resolve().parents[1]


def json_script(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':')).replace(chr(60),chr(92)+'u003c')


def build():
    target = ROOT / 'bdo-market-intelligence.html'
    html = target.read_text(encoding='utf-8')
    for name in ('crafting-engine.js', 'crafting-studio.js', 'vision-timers.js',
                 'crafting-loot-view.js', 'crafting-studio.css', 'recipe-browser.js'):
        marker = name.upper().replace('.', '_').replace('-', '_')
        start, end = f'/* OWNED {marker} START */', f'/* OWNED {marker} END */'
        assert html.count(start) == html.count(end) == 1, name
        source = (ROOT / 'desktop/assets' / name).read_text(encoding='utf-8-sig').strip()
        a, b = html.index(start), html.index(end)
        html = html[:a] + start + '\n' + source + '\n' + html[b:]
    recipes = json_script(json.loads((ROOT / 'desktop/assets/recipes.json').read_text(encoding='utf-8')))
    html, count = re.subn(r'    const RECIPES = .*?;\n', lambda _: '    const RECIPES = '+recipes+';\n', html, count=1)
    assert count == 1
    data = json_script(json.loads((ROOT / 'desktop/assets/crafting-data.json').read_text(encoding='utf-8')))
    start, end = '/* CRAFT DATA START */', '/* CRAFT DATA END */'
    block = start+'\nconst VISION_CRAFT_DATA = '+data+';\n'+end
    if start in html:
        a, b = html.index(start), html.index(end)+len(end)
        html = html[:a]+block+html[b:]
    else:
        html = html.replace('    /* Virtual recipe for durability-based timer */', block+'\n    /* Virtual recipe for durability-based timer */',1)
    target.write_text(html, encoding='utf-8')
    print('Crafting assets and recipe data synchronized')


if __name__ == '__main__':
    build()
