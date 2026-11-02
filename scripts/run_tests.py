"""Run native Tk regression modules in separate, disposable user profiles."""
from pathlib import Path
import argparse,subprocess,sys,tempfile,os,json,re,sqlite3

project=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--module',action='append',default=[],help='Test module name, with or without test_ / .py; repeat to select several')
args=parser.parse_args()
modules=sorted((project/'tests').glob('test_*.py'))
if args.module:
    names={name.removesuffix('.py') for name in args.module}
    names={name if name.startswith('test_') else 'test_'+name for name in names}
    unknown=names-{m.stem for m in modules}
    if unknown:parser.error('Unknown test modules: '+', '.join(sorted(unknown)))
    modules=[m for m in modules if m.stem in names]
report=[];total=0;failed=[]
for module in modules:
    with tempfile.TemporaryDirectory(prefix='vision-tests-') as folder:
        env=dict(os.environ,BDO_VISION_DATA_DIR=folder,PYTHONUTF8='1')
        Path(folder,'settings.json').write_text(json.dumps({'loot_enabled':False,'auto_scan':False}))
        sqlite3.connect(Path(folder,'loot-history.sqlite3')).close()
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
report_name='test-selected-report.txt' if args.module else 'test-report.txt'
result_name='test-selected-results.json' if args.module else 'test-results.json'
(folder/report_name).write_text('\n'.join(report),encoding='utf-8')
identity=subprocess.run(['git','rev-parse','HEAD'],cwd=project,capture_output=True,text=True)
(folder/result_name).write_text(json.dumps({'version':(project/'VERSION').read_text().strip(),
    'git_commit':identity.stdout.strip(),'scope':'selected' if args.module else 'full','modules':[m.name for m in modules],
    'tests':total,'failed_modules':failed},indent=2),encoding='utf-8')
print(f'TOTAL: {total} tests; {len(failed)} failed modules',flush=True)
raise SystemExit(bool(failed))
