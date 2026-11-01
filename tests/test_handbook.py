"""Documentation must remain navigable and must render source as inert text."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('handbook',ROOT/'scripts/build_handbook.py')
handbook=importlib.util.module_from_spec(spec);spec.loader.exec_module(handbook)


class HandbookTests(unittest.TestCase):
    def test_build_escapes_code_links_symbols_and_excludes_private_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'build/site'
            for name in ('README.md','CHANGELOG.md','AGENTS.md','native/README.md','docs/handbook/01-start.md'):
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('# Guide\n\n## Details\n\n[Section](#details)\n',encoding='utf-8')
            (root/'VERSION').write_text('test')
            (root/'sample.py').write_text('"""<script>example</script>"""\ndef example():\n    return "<img onerror=alert(1)>"\n')
            private=root/'qa-private';private.mkdir();(private/'secret.py').write_text('SECRET_PERSONAL_CAPTURE')
            with patch.object(handbook,'ROOT',root),patch.object(handbook,'OUT',out):
                inventory=handbook.build()
                page=(out/handbook.page_name(root/'sample.py')).read_text(encoding='utf-8')
            self.assertEqual([r['path'] for r in inventory],['sample.py'])
            self.assertIn('id="L2"',page);self.assertIn('&lt;script&gt;',page)
            self.assertNotIn('<img onerror=',page)
            self.assertNotIn('SECRET_PERSONAL_CAPTURE',(out/'search-data.js').read_text())
            self.assertIn('\\u003cscript',(out/'search-data.js').read_text())

    def test_broken_file_and_section_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);page=folder/'index.html'
            for target in ('missing.html','index.html#missing','../outside.html'):
                page.write_text('<a href="'+target+'">Broken</a>')
                with self.assertRaises(ValueError):handbook.validate_links(folder)


if __name__=='__main__':unittest.main()
