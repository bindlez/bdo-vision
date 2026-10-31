"""On-demand release inventory and integrity checks; no resident service."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, html, json, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def verify(archive):
    """Check the ZIP checksum, complete member list and every manifest hash."""
    archive = Path(archive)
    expected = archive.with_suffix('.zip.sha256').read_text().split()[0]
    if digest(archive) != expected:
        raise ValueError('Archive checksum mismatch')
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive paths')
        for name in names:
            path = PurePosixPath(name)
            if '\\' in name or path.is_absolute() or '..' in path.parts or ':' in name:
                raise ValueError('Unsafe archive path')
        manifests = [n for n in names if n.count('/') == 1 and n.endswith('/release-manifest.json')]
        if len(manifests) != 1:
            raise ValueError('Exactly one release manifest required')
        prefix = manifests[0].split('/')[0] + '/'
        manifest = json.loads(package.read(manifests[0]))
        actual = {n for n in names if not n.endswith('/') and n != manifests[0]}
        declared = {prefix + name for name in manifest['files']}
        if actual != declared:
            raise ValueError('Manifest does not describe the complete archive')
        for name, expected in manifest['files'].items():
            if hashlib.sha256(package.read(prefix + name)).hexdigest() != expected:
                raise ValueError('File checksum mismatch: ' + name)
    return manifest


def inventory(root=ROOT):
    rows = []
    for archive in sorted((root / 'dist').glob('BDO-Vision-*.zip'), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            manifest = verify(archive)
            state = 'Integrity verified'
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            manifest = {}; state = 'CHECK FAILED: ' + str(exc)
        rows.append({'name': archive.name, 'version': manifest.get('version', 'Unknown'),
                     'commit': manifest.get('git_commit', ''), 'state': state,
                     'sha256': digest(archive), 'bytes': archive.stat().st_size,
                     'candidate': 'rc.' in manifest.get('version', ''),
                     'dirty': manifest.get('uncommitted_source', True)})
    return rows


def build_page(root=ROOT):
    rows = inventory(root); cards = []
    for row in rows:
        e = lambda value: html.escape(str(value), quote=True)
        cards.append(f'''<article><div class="label">{'TEST CANDIDATE' if row['candidate'] else 'ARCHIVE'} · {row['bytes']/1048576:.1f} MB</div>
<h2>{e(row['version'])}</h2><p>{e(row['name'])}</p><p>{e(row['state'])} · {'Uncommitted source' if row['dirty'] else 'Committed source'}</p>
<a class="button" href="{e(row['name'])}" download>Download ZIP</a> <a href="{e(row['name'])}.sha256">Checksum</a>
<details><summary>Build identity</summary><p>Source: <code>{e(row['commit'])}</code></p><p>SHA-256: <code>{row['sha256']}</code></p></details></article>''')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BDO Vision · Release Center</title><style>body{margin:0;background:#0c0a13;color:#f4efff;font:16px/1.6 'Segoe UI',sans-serif}main{max-width:1000px;margin:auto;padding:48px 24px}h1{font-size:40px;line-height:1.15}h2{margin:8px 0}p{color:#c9c0db}a{color:#d8b7ff}article,.intro{background:#171221;border:1px solid #443453;border-radius:16px;padding:24px;margin:20px 0}.label{color:#c9a0ff;font-size:12px;letter-spacing:2px}.button{display:inline-block;padding:10px 18px;background:#713dc2;color:white;border-radius:8px;text-decoration:none;margin:8px 14px 8px 0}a:focus-visible,summary:focus-visible{outline:3px solid #ffdc87;outline-offset:4px}code{overflow-wrap:anywhere;font-size:12px}summary{cursor:pointer;margin-top:16px}</style>
<main><div class="label">BDO VISION · YOUR RELEASE LIBRARY</div><h1>Your app. Every version.</h1>
<p>Download, verify, and keep a known working copy. This page runs only when opened; it has no background polling.</p>
<section class="intro"><strong>Start here</strong><p>Extract the entire Windows ZIP, then open OPEN-BDO-VISION.bat. Source ZIPs are for development. Test candidates are clearly labeled.</p>
<p>History stays in your existing protected profile, separate from these downloads. Close Vision before switching copies. An older app may not understand a newer profile: back up the profile before switching, and never copy an old database over your live history.</p>
<p>The Windows app includes Python. This candidate still requires Tesseract with English for live OCR. Icon-only recognition remains experimental; reviewed tooltip import is included.</p>
<a href="../docs/RELEASE-SYSTEM.md">Version and recovery guide</a> · <a href="../build/test-report.txt">Latest source tests</a> · <a href="../build/windows-check.json">Latest packaged-app check</a>
<p>Integrity verification checks files, not OCR accuracy. Test reports describe the latest local run; compare its version with the release you select.</p></section>'''+''.join(cards)+'</main></html>'
    target = root / 'dist' / 'RELEASE-CENTER.html'; target.parent.mkdir(exist_ok=True)
    target.write_text(page, encoding='utf-8')
    (target.parent / 'release-index.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['refresh', 'verify', 'checkpoint'])
    parser.add_argument('target', nargs='?')
    args = parser.parse_args()
    if args.action == 'verify':
        print(json.dumps(verify(args.target), indent=2)[:600])
    elif args.action == 'checkpoint':
        if not args.target or not all(c.isalnum() or c in '.-_' for c in args.target):
            parser.error('Use a checkpoint name with letters, numbers, dots, dashes or underscores')
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
            parser.error('Commit reviewed source changes first. A checkpoint must refer to a clean revision.')
        subprocess.run(['git', 'tag', '-a', 'checkpoint/'+args.target, '-m', 'BDO Vision checkpoint '+args.target], cwd=ROOT, check=True)
        print('Checkpoint saved. Existing tags are never overwritten.')
    else:
        print(build_page())


if __name__ == '__main__':
    main()
