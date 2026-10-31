"""Explicit Windows backup of browser gear builds; separate from loot history."""
from pathlib import Path
import json,os,shutil,uuid
from datetime import datetime,timezone


def validate(data):
    if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('builds'),list) or not 1<=len(data['builds'])<=12:raise ValueError('Invalid gear backup')
    if len(json.dumps(data))>300000:raise ValueError('Gear backup too large')
    for build in data['builds']:
        if not isinstance(build,dict) or not isinstance(build.get('id'),str) or len(build['id'])>150:raise ValueError('Invalid build')
        for side in ('current','target'):
            if not isinstance(build.get(side),dict) or len(build[side])>24:raise ValueError('Invalid loadout')
            for item in build[side].values():
                if not isinstance(item,dict) or type(item.get('id')) is not int or not 0<item['id']<10000000 or not isinstance(item.get('name'),str) or len(item['name'])>150:raise ValueError('Invalid item')
                if type(item.get('enhance')) is not int or not 0<=item['enhance']<=30:raise ValueError('Invalid enhancement')
    return data


def save(root,data):
    validate(data);root=Path(root);root.mkdir(parents=True,exist_ok=True)
    target=root/'gear-builds.json';temporary=root/('gear-builds-'+uuid.uuid4().hex+'.tmp')
    payload={'saved_at':datetime.now(timezone.utc).isoformat(),'data':data}
    try:
        temporary.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        if target.exists():shutil.copyfile(target,root/'gear-builds.previous.json')
        os.replace(temporary,target)
    finally:
        if temporary.exists():temporary.unlink()
    return {'ok':True,'saved_at':payload['saved_at'],'builds':len(data['builds'])}


def load(root):
    target=Path(root)/'gear-builds.json'
    if not target.exists():return None
    payload=json.loads(target.read_text(encoding='utf-8'));validate(payload['data']);return payload
