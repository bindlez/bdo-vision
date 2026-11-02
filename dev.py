"""One small entry point for development. The shipped app never imports this."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def run(*command, **options):
    return subprocess.run(command, cwd=ROOT, check=True, **options)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor', help='Read-only dependency and repository report')
    start = commands.add_parser('run', help='Start with a disposable profile by default')
    start.add_argument('--profile', type=Path, help='Explicit persistent DEVELOPMENT profile; never choose your live profile')
    tests = commands.add_parser('test', help='Run all tests or selected modules in isolated profiles')
    tests.add_argument('modules', nargs='*')
    commands.add_parser('check', help='Full Python, planner, gear, rendering-safety and handbook checks')
    commands.add_parser('docs', help='Build the offline Developer Handbook')
    args = parser.parse_args()
    if args.command == 'doctor':
        print('Python:', sys.version.split()[0], sys.executable)
        print('Windows:', os.name == 'nt')
        for module in ('PIL', 'tkinter', 'pywinauto', 'PyInstaller'):
            print(module + ':', bool(importlib.util.find_spec(module)))
        for binary in ('git', 'node', 'tesseract'):
            found = shutil.which(binary)
            if not found and binary == 'tesseract':
                path = Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
                found = str(path) if path.is_file() else None
            print(binary + ':', found or 'not found')
        print('Version:', (ROOT / 'VERSION').read_text().strip())
        run('git', 'status', '--short')
    elif args.command == 'run':
        def launch(folder):
            folder = Path(folder).resolve()
            folder.mkdir(parents=True, exist_ok=True)
            settings = folder / 'settings.json'
            if not (folder/'loot-history.sqlite3').exists():
                sqlite3.connect(folder/'loot-history.sqlite3').close()
            if not settings.exists():
                settings.write_text(json.dumps({'loot_enabled': False, 'auto_scan': False,
                                                'guild_quest_enabled': False}), encoding='utf-8')
            print('Development profile:', folder, flush=True)
            run(sys.executable, 'desktop/app.py', env=dict(os.environ, BDO_VISION_DATA_DIR=str(folder)))
        if args.profile:
            live = (Path.home() / '.bdo-vision').resolve()
            requested = args.profile.resolve()
            if requested == live or live in requested.parents:
                parser.error('Use a development profile outside the live .bdo-vision folder.')
            launch(requested)
        else:
            with tempfile.TemporaryDirectory(prefix='vision-dev-') as folder:
                launch(folder)
    elif args.command == 'test':
        selected = [arg for name in args.modules for arg in ('--module', name)]
        run(sys.executable, 'scripts/run_tests.py', *selected)
    elif args.command == 'docs':
        run(sys.executable, 'scripts/build_handbook.py')
    elif args.command == 'check':
        for command in (
            (sys.executable, 'scripts/run_tests.py'),
            (sys.executable, 'scripts/check_planner.py'),
            ('node', 'scripts/test_gear_core.js'),
            ('node', 'scripts/test_planner_security.js'),
            ('node', 'scripts/test_big_drops.js'),
            ('node', 'scripts/test_cp.js'),
            ('node', 'scripts/test_cp_page.js'),
            ('node', 'scripts/test_crafting.js'),
            ('node', 'scripts/test_crafting_page.js'),
            (sys.executable, '-m', 'compileall', '-q', 'desktop', 'scripts', 'tests', 'dev.py'),
            (sys.executable, 'scripts/build_handbook.py', '--check'),
        ):
            run(*command)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
