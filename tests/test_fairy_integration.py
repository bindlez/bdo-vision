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
const session={id:'run1',ended_at:1000,observed_seconds:90,excluded_seconds:30,units:20,value:null,spot:'Test'};
const receipt=F.sessionReceipt('history1',session);assert(receipt.text.includes('unpriced'));assert(receipt.text.includes('kills unknown'));
assert.equal(receipt.key,F.sessionReceipt('history1',session).key);
assert.notEqual(receipt.key,F.sessionReceipt('history2',session).key);
assert.throws(()=>F.sessionReceipt('history1',{...session,ended_at:null}));
const fs=require('node:fs'),vm=require('node:vm'),page=fs.readFileSync('fairycodex.html','utf8');
const hook=page.match(/window.VisionImportReceipt=function\(receipt\)\{[\s\S]*?\n\};/)[0];
let fail=false,saved='';const context={window:{},T:{journal:[],piece:{owned:1},sessions:[]},KEY:'test',localStorage:{setItem:(k,v)=>{if(fail)throw Error('quota');saved=v;}},redraw:()=>{}};
vm.runInNewContext(hook,context);const importReceipt=context.window.VisionImportReceipt;
importReceipt(receipt);assert.equal(context.T.journal.length,1);assert.equal(JSON.parse(saved).journal[0].visionKey,receipt.key);
assert.equal(importReceipt(receipt),'Already imported');assert.equal(context.T.journal.length,1);
fail=true;assert.throws(()=>importReceipt({...receipt,key:'new-run'}),/not saved/);assert.equal(context.T.journal.length,1);
assert.equal(context.T.piece.owned,1);assert.equal(context.T.sessions.length,0);
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
