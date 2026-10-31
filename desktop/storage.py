"""A persistent user profile shared by installs, with verified SQLite backups."""
import json
import os
import shutil
import sqlite3
import time
import urllib.request
from contextlib import closing
from datetime import datetime
from pathlib import Path


def data_root():
    override=os.environ.get('BDO_VISION_DATA_DIR')
    if override:return Path(override).resolve()
    # Packaged Windows hosts can virtualize LocalAppData differently from a
    # desktop launch. A user-home profile has one physical path in both cases.
    return Path.home()/'.bdo-vision'


def copy_database(source,target):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(str(source))) as original,closing(sqlite3.connect(str(target))) as saved:
        original.backup(saved)
        if saved.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise OSError('History backup could not be verified')


def prepare_storage(legacy):
    root=data_root();root.mkdir(parents=True,exist_ok=True)
    legacy=Path(legacy)
    if not (root/'loot-history.sqlite3').exists() and (legacy/'loot-history.sqlite3').exists():
        copy_database(legacy/'loot-history.sqlite3',root/'loot-history.sqlite3')
    if not (root/'settings.json').exists() and (legacy/'settings.json').exists():
        shutil.copyfile(legacy/'settings.json',root/'settings.json')
    cache=legacy/'market-item-database.json'
    if not (root/cache.name).exists() and cache.exists():shutil.copyfile(cache,root/cache.name)
    return root


def backup_profile(root,label='manual'):
    root=Path(root);folder=root/'backups'/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-'+label)
    folder.mkdir(parents=True,exist_ok=False)
    if (root/'loot-history.sqlite3').exists():copy_database(root/'loot-history.sqlite3',folder/'loot-history.sqlite3')
    if (root/'settings.json').exists():shutil.copyfile(root/'settings.json',folder/'settings.json')
    for name in ('gear-builds.json','gear-builds.previous.json'):
        if (root/name).exists():shutil.copyfile(root/name,folder/name)
    (folder/'README.txt').write_text('Verified BDO Vision history and settings backup. Original data is retained.\n',encoding='utf-8')
    return folder


class InstanceLock:
    """The OS releases this lock even after a crash; no stale PID deletes data."""
    def __init__(self,root):self.path=Path(root)/'instance.lock';self.file=None

    def acquire(self):
        import msvcrt
        self.path.parent.mkdir(parents=True,exist_ok=True)
        handle=open(self.path,'a+b')
        if handle.tell()==0:handle.write(b'0');handle.flush()
        handle.seek(0)
        try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:handle.close();return False
        self.file=handle;return True

    def release(self):
        if self.file:
            import msvcrt
            self.file.seek(0);msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1);self.file.close();self.file=None


def focus_existing(root):
    """Use the authenticated local instance ID, never guess a listening port."""
    try:
        status=json.loads((Path(root)/'runtime-status.json').read_text(encoding='utf-8'))
        base=status['base_url']
        if not base.startswith('http://127.0.0.1:'):return False
        with urllib.request.urlopen(base+'/health',timeout=2) as response:health=json.load(response)
        if health.get('app_id')!='bdo-vision' or Path(health.get('data_path','')).resolve()!=Path(root).resolve():return False
        body=json.dumps({'instance_id':health['instance_id']}).encode()
        request=urllib.request.Request(base+'/show',data=body,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=2) as response:return response.status==200
    except (OSError,ValueError,KeyError):return False
