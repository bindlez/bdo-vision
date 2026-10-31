"""Build a one-directory Windows candidate; no Python installation is required."""
from pathlib import Path
import subprocess,sys,shutil,json,hashlib,zipfile,tempfile
from importlib import metadata
from generate_assets import generate

root=Path(__file__).resolve().parents[1];version=(root/'VERSION').read_text().strip()
build=root/'build';out=root/'dist';out.mkdir(exist_ok=True);build.mkdir(exist_ok=True)
safe=build/'generated-release-assets';generate(safe)
assets=safe/'desktop/assets'
for pattern in ('*.json','*.js','*.css'):
    for path in (root/'desktop/assets').glob(pattern):shutil.copy2(path,assets/path.name)
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
    '--name','BDO-Vision','--icon',str(assets/'bdo-lite.ico'),'--paths',str(root/'desktop'),
    '--distpath',str(build/'frozen'),'--workpath',str(build/'pyinstaller'),'--specpath',str(build),
    '--add-data',str(assets)+';assets','--hidden-import','pywinauto','--hidden-import','comtypes',
    '--exclude-module','numpy','--exclude-module','scipy','--exclude-module','matplotlib',
    '--exclude-module','pandas','--exclude-module','torch','--exclude-module','cv2',
    str(root/'desktop/app.py')],cwd=root,check=True)
stage=Path(tempfile.mkdtemp(prefix='portable-',dir=build))/f'BDO-Vision-{version}-Windows'
desktop=stage/'desktop';desktop.mkdir(parents=True,exist_ok=True)
shutil.copytree(build/'frozen/BDO-Vision',desktop,dirs_exist_ok=True)
shutil.copytree(assets,desktop/'assets',dirs_exist_ok=True)
for name in ('bdo-market-intelligence.html','VERSION','README.md','RELEASE_NOTES.md'):
    shutil.copy2(root/name,stage/name)
guide=root/'docs/QUICK-START.md'
if not guide.is_file():guide=root/'docs/FRIEND-TEST.md'
if guide.is_file():shutil.copy2(guide,stage/'START-HERE.md')
for name in ('FRIEND-TEST.md','PERFORMANCE-AND-SECURITY.md','RELEASE-SYSTEM.md'):
    if (root/'docs'/name).is_file():shutil.copy2(root/'docs'/name,stage/name)
evidence=stage/'CHECKS';evidence.mkdir(exist_ok=True)
for name in ('test-report.txt','test-results.json'):
    if (build/name).is_file():shutil.copy2(build/name,evidence/name)
licenses=stage/'LICENSES';licenses.mkdir(exist_ok=True);third_party=[]
for name in ('Pillow','pywinauto','comtypes','pywin32','pyinstaller'):
    try:distribution=metadata.distribution(name)
    except metadata.PackageNotFoundError:continue
    third_party.append(f'{name} {distribution.version}')
    for entry in distribution.files or []:
        if any(word in entry.name.casefold() for word in ('license','copying','notice')) and entry.suffix.casefold() in ('','.txt','.md','.rst'):
            source=Path(distribution.locate_file(entry))
            if source.is_file():shutil.copy2(source,licenses/(name+'-'+entry.name))
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.is_file():shutil.copy2(python_license,licenses/'Python-LICENSE.txt')
(licenses/'README.txt').write_text('Runtime components:\n'+'\n'.join(third_party)+'\nPython '+sys.version.split()[0]+'\nTcl/Tk licenses are also retained in the bundled runtime files. Tesseract is installed separately.\n',encoding='utf-8')
(stage/'OPEN-BDO-VISION.bat').write_text('@echo off\nstart "" "%~dp0desktop\\BDO-Vision.exe"\n',encoding='ascii')
revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
files={str(path.relative_to(stage)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest()
       for path in stage.rglob('*') if path.is_file() and path.name!='release-manifest.json'}
(stage/'release-manifest.json').write_text(json.dumps({'version':version,'git_commit':revision,
    'git_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip(),
    'uncommitted_source':bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()),
    'entrypoint':'OPEN-BDO-VISION.bat','ocr_requirement':'Tesseract English required separately','files':files},indent=2))
archive=out/f'BDO-Vision-{version}-Windows.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as package:
    for path in stage.rglob('*'):
        if path.is_file():package.write(path,path.relative_to(stage.parent))
checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix('.zip.sha256').write_text(checksum+'  '+archive.name+'\n',encoding='ascii')
print('Windows package:',archive);print('SHA256:',checksum)
