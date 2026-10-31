"""Build-time only: pack public item names into an embedded read-only resource."""
from pathlib import Path
import argparse,json,sqlite3,struct
p=argparse.ArgumentParser();p.add_argument('--catalog',required=True,type=Path);p.add_argument('--output',type=Path,default=Path('build/native/items.bin'));args=p.parse_args()
if args.catalog.suffix.lower() in ('.sqlite3','.db'):
 with sqlite3.connect(args.catalog) as db:names=[row[0] for row in db.execute('SELECT DISTINCT name FROM catalog_items ORDER BY name')]
else:
 data=json.loads(args.catalog.read_text(encoding='utf-8'));names=sorted({row['name'] for row in data if isinstance(row,dict) and isinstance(row.get('name'),str)})
def normalize(name):return ''.join(c.lower() for c in name if c.isascii() and c.isalnum())
def fold(c):return 'o' if c in '0og6' else 'i' if c in 'il1j' else 'n' if c in 'mn' else 'u' if c in 'uv' else 's' if c=='5' else c
def fingerprint(s):
 result=0
 for a,b in zip(s,s[1:]):result|=1<<((ord(fold(a))*37+ord(fold(b))*17)%64)
 return result
blob=bytearray();entries=[]
for name in names:
 if not 1<=len(name)<=100:continue
 key=normalize(name)
 if not key:continue
 name_offset=len(blob);blob.extend(name.encode('utf-8')+b'\0');key_offset=len(blob);blob.extend(key.encode('ascii')+b'\0');entries.append((name_offset,key_offset,len(key),fingerprint(key)))
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_bytes(struct.pack('<4sII',b'BVL1',len(entries),12+len(entries)*20)+b''.join(struct.pack('<IIIQ',*e) for e in entries)+blob)
print('Embedded catalog:',len(entries),'names;',args.output.stat().st_size,'bytes')
