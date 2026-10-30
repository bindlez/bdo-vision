"""Check the bundled planner's actual inline JavaScript without live game data."""
from pathlib import Path
import re,subprocess
root=Path(__file__).resolve().parents[1]
folder=root/'build';folder.mkdir(exist_ok=True)
for source_path in [root/'bdo-market-intelligence.html',*sorted((root/'demo').glob('*.html'))]:
    source=source_path.read_text(encoding='utf-8')
    target=folder/(source_path.stem+'-inline.js')
    target.write_text('\n'.join(re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',source,re.S)),encoding='utf-8')
    subprocess.run(['node','--check',str(target)],check=True)
    print(source_path.name+' JavaScript syntax passed')
