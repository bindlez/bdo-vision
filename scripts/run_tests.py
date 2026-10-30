"""Run native Tk regression modules in separate, disposable user profiles."""
from pathlib import Path
import subprocess,sys,tempfile,os,json,re

project=Path(__file__).resolve().parents[1]
report=[];total=0;failed=[]
for module in sorted((project/'tests').glob('test_*.py')):
    with tempfile.TemporaryDirectory(prefix='vision-tests-') as folder:
        env=dict(os.environ,BDO_VISION_DATA_DIR=folder,PYTHONUTF8='1')
        Path(folder,'settings.json').write_text(json.dumps({'loot_enabled':False,'auto_scan':False}))
        try:
            result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p',module.name],
                cwd=project,env=env,capture_output=True,text=True,encoding='utf-8',timeout=90)
            match=re.search(r'Ran (\d+) tests?',result.stderr)
            total+=int(match[1]) if match else 0
            okay=result.returncode==0 and match is not None
            report.append(module.name+'\n'+result.stdout+result.stderr)
            if not okay:failed.append(module.name);print(result.stderr[-5000:],flush=True)
        except subprocess.TimeoutExpired:
            okay=False;failed.append(module.name);report.append(module.name+' timed out')
        print(('PASS' if okay else 'FAIL'),module.name,flush=True)
folder=project/'build';folder.mkdir(exist_ok=True)
(folder/'test-report.txt').write_text('\n'.join(report),encoding='utf-8')
print(f'TOTAL: {total} tests; {len(failed)} failed modules',flush=True)
raise SystemExit(bool(failed))
