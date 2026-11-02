import subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


class FairyIntegrationTests(unittest.TestCase):
    def test_exact_matches_quantities_and_unknown_pieces(self):
        script=r'''
const assert=require('node:assert/strict'),F=require('./desktop/assets/fairy-vision.js');
const catalog=[{name:'HP Potion',parts:[{name:'Ash Halfmoon Kagtunak'}]}];
const rows=F.matchRows([{item:'Ash Halfmoon Kagtunak',quantity:1},{item:'Ancient Kagtunak fragment',quantity:10},{item:'bad',quantity:-1}],catalog);
assert.equal(rows.length,2);assert.deepEqual(rows[0].matches,['HP Potion']);assert.deepEqual(rows[1].matches,[]);
assert.equal(F.nameKey(' Ron’s  Tintinnabulum '),"ron's tintinnabulum");
assert.equal(F.matchRows(Array.from({length:100},(_,i)=>({item:'i'+i,quantity:1})),catalog).length,80);
assert.deepEqual(F.matchRows([{item:'<img onerror=alert(1)>',quantity:1}],catalog)[0].matches,[]);
'''
        result=subprocess.run(['node','-e',script],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_regeneration_is_deterministic_and_preserves_upstream(self):
        before=(ROOT/'fairycodex.html').read_bytes()
        subprocess.run([sys.executable,'scripts/build_fairy.py'],cwd=ROOT,check=True,capture_output=True)
        self.assertEqual(before,(ROOT/'fairycodex.html').read_bytes())
        source=(ROOT/'desktop/assets/fairy-vision.js').read_text()
        self.assertNotIn('localStorage.setItem',source)
        self.assertNotIn('innerHTML',source)
        self.assertIn('document.hidden',source)
