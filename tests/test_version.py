"""The visible release identity must follow its own shipped files."""
from pathlib import Path
from unittest.mock import patch
import runpy,sys,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1]


class VersionTests(unittest.TestCase):
    def test_source_identity_uses_root_version(self):
        namespace=runpy.run_path(str(ROOT/'desktop/version.py'))
        self.assertEqual(namespace['APP_VERSION'],(ROOT/'VERSION').read_text().strip())

    def test_frozen_identity_uses_executable_sibling_release_not_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            release=Path(folder);(release/'VERSION').write_text('9.8.7-test')
            with patch.object(sys,'frozen',True,create=True),patch.object(sys,'executable',str(release/'desktop/BDO-Vision.exe')):
                self.assertEqual(runpy.run_path(str(ROOT/'desktop/version.py'))['APP_VERSION'],'9.8.7-test')
            (release/'VERSION').unlink()
            with patch.object(sys,'frozen',True,create=True),patch.object(sys,'executable',str(release/'desktop/BDO-Vision.exe')):
                self.assertEqual(runpy.run_path(str(ROOT/'desktop/version.py'))['APP_VERSION'],'unknown')
