import json
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from craft_economy import craft_spec
from imperial_planner import imperial_ranks


class ImperialPlannerTests(unittest.TestCase):
    def test_native_browser_cost_and_stock_parity_across_real_catalog(self):
        quotes={int(k):{'price':100+int(k)%100,'stock':10000000} for k in craft_spec()['items']}
        states=[{'boxes':1,'mastery':{'cooking':0,'alchemy':0}},
                {'boxes':245,'mastery':{'cooking':1500,'alchemy':3000},'guruOnly':True}]
        projections=('cost','profit','inStock','runs','recipeId')
        js="const fs=require('fs'),C=require('./desktop/assets/crafting-engine.js'),v=JSON.parse(fs.readFileSync(0,'utf8')),recipes=JSON.parse(fs.readFileSync('desktop/assets/recipes.json')),spec=JSON.parse(fs.readFileSync('desktop/assets/crafting-data.json'));console.log(JSON.stringify(v.states.map(o=>C.imperialRanks(recipes,spec,(n,id)=>v.quotes[id],o))));"
        for stock in ('available','missing','mixed'):
            for ident,q in quotes.items():
                if stock=='missing':q.pop('stock',None)
                else:q['stock']=10000000 if stock=='available' or ident%2 else 0
            other=json.loads(subprocess.check_output(['node','-e',js],input=json.dumps({'quotes':quotes,'states':states}).encode(),cwd=ROOT))
            for state,browser in zip(states,other):
                native=imperial_ranks(quotes,boxes=state['boxes'],mastery=state['mastery'],guru_only=state.get('guruOnly',False))
                for kind in ('cooking','alchemy'):
                    for mode in ('buy','craft','craftInStock'):
                        a={r['boxRecipeId']:r for r in native[kind][mode]};b={r['boxRecipeId']:r for r in browser[kind][mode]}
                        self.assertEqual(a.keys(),b.keys(),(stock,kind,mode))
                        for key in a:
                            for field in projections:
                                x=a[key].get(field);y=b[key].get(field)
                                if type(x) in (int,float) and type(y) in (int,float):self.assertAlmostEqual(x,y,places=5,msg=(stock,kind,mode,key,field))
                                else:self.assertEqual(x,y,(stock,kind,mode,key,field))


if __name__=='__main__':unittest.main()
