"""Verify the extracted Windows artifact with a disposable profile and no game."""
from pathlib import Path
import subprocess,sys,os,json,zipfile,tempfile,hashlib,time
from generate_assets import generate

root=Path(__file__).resolve().parents[1];version=(root/'VERSION').read_text().strip()
archive=root/'dist'/f'BDO-Vision-{version}-Windows.zip'
expected=archive.with_suffix('.zip.sha256').read_text().split()[0]
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected,'ZIP checksum mismatch'
with tempfile.TemporaryDirectory(prefix='vision-portable-check-') as folder:
    folder=Path(folder)
    with zipfile.ZipFile(archive) as package:
        for name in package.namelist():
            assert '..' not in Path(name).parts and not Path(name).is_absolute(),name
            assert Path(name).name not in ('settings.json','runtime-status.json','last_capture.png'),name
            assert not name.lower().endswith(('.sqlite3','.db')),name
        package.extractall(folder)
    stage=folder/f'BDO-Vision-{version}-Windows'
    manifest=json.loads((stage/'release-manifest.json').read_text())
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((stage/name).read_bytes()).hexdigest()==digest,name
    profile=folder/'isolated-profile';report=folder/'self-check.json'
    env=dict(os.environ,BDO_VISION_DATA_DIR=str(profile))
    generate(folder/'generated')
    started=time.monotonic()
    result=subprocess.run([str(stage/'desktop/BDO-Vision.exe'),'--self-check','--self-check-report',str(report),
                           '--ocr-fixture',str(folder/'generated/tests/fixtures/item-drop-log.png')],
                          env=env,cwd=stage,timeout=30)
    assert result.returncode==0,'Executable self-check failed'
    details=json.loads(report.read_text());assert details['ok'],details
    details['seconds']=round(time.monotonic()-started,3);details['zip_bytes']=archive.stat().st_size
    details['git_commit']=manifest['git_commit'];details['archive_sha256']=expected
    (root/'build/windows-check.json').write_text(json.dumps(details,indent=2))
    archive.with_suffix('.zip.checks.json').write_text(json.dumps(details,indent=2))
    print(json.dumps(details,indent=2))
