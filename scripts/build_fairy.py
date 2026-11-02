"""Integrate a pinned upstream Fairy Codex without editing its saved vault."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]


def build():
    source=(ROOT/'fairycodex-upstream.html').read_text(encoding='utf-8')
    marker='const KEY=\'fairycodex.treasure.v1\';'
    if source.count(marker)!=1:raise ValueError('Fairy Codex treasure adapter anchor changed; review upstream before rebuilding')
    # Expose only catalog identities; the integration never mutates the vault.
    source=source.replace(marker,"window.VisionTreasureCatalog=CATALOG.map(t=>({id:t.id,name:t.name,parts:t.parts.map(p=>({id:p[0],name:p[1]}))}));\n"+marker)
    ribbon='''<section id="vision-link" style="margin:16px;padding:18px;background:#171020;border:1px solid #78538e;border-radius:12px;color:#eee5ff;font:14px/1.6 system-ui">
<nav><a href="/planner#craft" style="color:#d6b2ff">← Vision Planner</a> · <a href="/planner#gear" style="color:#d6b2ff">Gear Studio</a></nav>
<h2>Vision × Fairy Codex V36.1</h2>
<p>One platform: fairy planning, treasure research and your locally recorded loot. Existing Fairy Codex progress can be imported using its backup tools; browser storage from another site is separate.</p>
<label><input id="vision-connect" type="checkbox"> Connect recorded loot from this Windows app</label>
<button id="vision-refresh" type="button">Refresh loot</button>
<p id="vision-loot-state" role="status">Not connected. Enable optional loot sharing in Vision, then connect here.</p>
<p>Recorded drops are observations, not current inventory or automatic treasure ownership. Exact catalog-name matches are highlighted; unidentified pieces stay unresolved. No additional OCR runs.</p>
<details><summary>Recorded loot and treasure matches</summary><div style="max-height:360px;overflow:auto"><table style="width:100%;text-align:left"><thead><tr><th>Recorded item</th><th>Units</th><th>Treasure reference</th></tr></thead><tbody id="vision-loot-rows"></tbody></table></div></details>
</section>'''
    source=source.replace('<body>', '<body>'+ribbon,1)
    if 'id="vision-link"' not in source:raise ValueError('Missing Fairy body integration')
    adapter=(ROOT/'desktop/assets/fairy-vision.js').read_text(encoding='utf-8')
    source=source.replace('</body>','<script>\n'+adapter+'\n</script></body>',1)
    (ROOT/'fairycodex.html').write_text(source,encoding='utf-8')
    print('Fairy Codex V36.1 integrated; upstream SHA256',hashlib.sha256((ROOT/'fairycodex-upstream.html').read_bytes()).hexdigest())


if __name__=='__main__':build()
