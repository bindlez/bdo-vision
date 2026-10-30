"""Check the bundled planner's actual inline JavaScript without live game data."""
from pathlib import Path
import re,subprocess
root=Path(__file__).resolve().parents[1]
folder=root/'build';folder.mkdir(exist_ok=True)
source=(root/'bdo-market-intelligence.html').read_text(encoding='utf-8')
target=folder/'planner-inline.js'
target.write_text('\n'.join(re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',source,re.S)),encoding='utf-8')
subprocess.run(['node','--check',str(target)],check=True)
print('Bundled planner JavaScript syntax passed')
