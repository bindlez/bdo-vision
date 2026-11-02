"""Package an explicit source allowlist and generated art, never a user profile."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tempfile,zipfile
from generate_assets import generate

root=Path(__file__).resolve().parents[1]
version=(root/'VERSION').read_text().strip()
out=root/'dist';out.mkdir(exist_ok=True)
allowed=[]
for name in ('VERSION','README.md','RELEASE_NOTES.md','requirements.txt','requirements-dev.txt',
             'requirements-optional-tray.txt','RUN.bat','INSTALL.bat','INSTALL-TRAY-SUPPORT.bat',
             'BUILD-EXE.bat','install_local.py','bdo-market-intelligence.html','fairycodex.html','fairycodex-upstream.html','.gitignore','.gitattributes',
             'dev.py','AGENTS.md','DEVELOPER-HANDBOOK.bat','CHANGELOG.md'):
    path=root/name
    if path.is_file():allowed.append(path)
for directory,pattern in [('desktop','*.py'),('desktop','*.bat'),('desktop/assets','*.json'),
                          ('desktop/assets','*.js'),('desktop/assets','*.css'),('tests','*.py'),('scripts','*.py'),('scripts','*.js'),('docs','*.md'),
                          ('.github/workflows','*.yml'),('native','*.md'),('native','*.py'),
                          ('native','*.hpp'),('native','*.cpp'),('native','*.cmd')]:
    allowed.extend((root/directory).glob(pattern))
allowed.extend((root/'docs/handbook').glob('*.md'))
if (root/'demo').exists():allowed.extend((root/'demo').glob('*.html'))
revision=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True)
dirty=subprocess.run(['git','status','--porcelain'],cwd=root,capture_output=True,text=True)
with tempfile.TemporaryDirectory(prefix='vision-release-',dir=out) as temporary:
    stage=Path(temporary)/f'BDO-Vision-{version}'
    stage.mkdir()
    for path in sorted(set(allowed)):
        target=stage/path.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
    generate(stage)  # All packaged images are deterministic generated artwork/fixtures.
    hashes={str(p.relative_to(stage)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(stage.rglob('*')) if p.is_file()}
    manifest={'version':version,'git_commit':revision.stdout.strip() if revision.returncode==0 else None,
              'uncommitted_source':bool(dirty.stdout.strip()),'entrypoint':'RUN.bat',
              'profile':'%USERPROFILE%/.bdo-vision','files':hashes}
    (stage/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    target=out/f'BDO-Vision-{version}-Windows-Source.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                info=zipfile.ZipInfo(str(path.relative_to(Path(temporary))).replace('\\','/'),date_time=(2026,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(info,path.read_bytes())
    checksum=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(checksum+'  '+target.name+'\n',encoding='ascii')
    print(target);print('SHA256:',checksum);print('Packaged files:',len(hashes)+1)
