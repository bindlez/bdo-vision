import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('release_center', Path(__file__).resolve().parents[1]/'scripts/release_center.py')
center = importlib.util.module_from_spec(spec); spec.loader.exec_module(center)


class ReleaseIntegrityTests(unittest.TestCase):
    def archive(self, folder, *, extra=None, declared=b'hello', content=b'hello'):
        path = Path(folder)/'release.zip'
        manifest = {'version':'test-rc.1','files':{'app.txt':hashlib.sha256(declared).hexdigest()}}
        with zipfile.ZipFile(path, 'w') as package:
            package.writestr('release/app.txt', content)
            package.writestr('release/release-manifest.json', json.dumps(manifest))
            if extra: package.writestr(extra, b'unexpected')
        path.with_suffix('.zip.sha256').write_text(center.digest(path))
        return path

    def test_valid_release(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(center.verify(self.archive(folder))['version'], 'test-rc.1')

    def test_changed_zip_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.archive(folder); path.write_bytes(path.read_bytes()+b'changed')
            with self.assertRaisesRegex(ValueError, 'Archive checksum'): center.verify(path)

    def test_changed_member_is_rejected_even_with_updated_zip_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'File checksum'):
                center.verify(self.archive(folder, content=b'changed'))

    def test_undeclared_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'complete archive'):
                center.verify(self.archive(folder, extra='release/settings.json'))

    def test_traversal_and_windows_paths_are_rejected(self):
        for name in ['../escape', 'release/../escape', 'C:/escape', 'release\\escape']:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                # Windows zipfile normalizes backslashes before writing; either
                # the unsafe-path gate or the complete-manifest gate rejects it.
                with self.assertRaises(ValueError):
                    center.verify(self.archive(folder, extra=name))


if __name__ == '__main__': unittest.main()
