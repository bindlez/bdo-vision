"""Catalog identities, resolved native costs and exact on-demand market snapshots."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from price_book import PriceBook
from craft_economy import recipes,validate_model,session_economy,craft_spec


class CraftingCatalogTests(unittest.TestCase):
    def test_real_recipe_replaces_old_demihuman_placeholder(self):
        r=next(r for r in recipes() if r['itemId']==678)
        self.assertEqual(r['id'],'alc_elixir_of_demihuman_hunt_9')
        self.assertFalse(any(m['name']=='Oil of Storms' for m in r['mats']))
        self.assertEqual(r['mats'][0]['required'],4);self.assertEqual(r['mats'][0]['groupId'],67)

    def test_resolved_groups_are_validated_and_native_uses_same_inputs(self):
        r=next(r for r in recipes() if r['name']=='Beer');model={'recipe_id':r['id'],'yield':2.5,'retention':84.5,'extra':0}
        rows=[{'itemId':m['itemId'],'name':m['name'],'qty':m['qty']} for m in r['mats']]
        option=next(o for o in craft_spec()['groups']['1'] if o['value']==7)
        rows[0]={'itemId':option['itemId'],'name':craft_spec()['items'][str(option['itemId'])]['name'],'qty':1}
        checked=validate_model({**model,'materials':rows});self.assertEqual(checked['materials'][0]['qty'],1)
        with self.assertRaises(ValueError):validate_model({**model,'materials':[{**rows[0],'qty':5},*rows[1:]]})
        quotes={m['name']:{'unit_price':10,'source':'market'} for m in rows};quotes['Beer']={'unit_price':100,'source':'market'}
        loot=[(1,'2026-11-02T10:00:00','Beer',25,'OCR','','Crafted')]
        result=session_economy(r,loot,quotes,checked)
        self.assertEqual(result['batches'],10);self.assertEqual(result['ingredient_cost'],1000)

    def test_id_quotes_cached_with_basis_stock_and_no_catalog_download(self):
        with tempfile.TemporaryDirectory() as folder:
            book=PriceBook(Path(folder)/'quotes.db')
            data={'id':5301,'sid':0,'name':'Clear Liquid Reagent','basePrice':12000,'currentStock':45,'lastSoldPrice':12500,'lastSoldTime':123}
            with patch.object(book,'_fetch_quotes',return_value=data) as fetch,patch.object(book,'ensure_catalog',side_effect=AssertionError('Unneeded catalog')):
                first=book.recipe_id_quotes([5301],'NA');self.assertIs(first,book.recipe_id_quotes([5301],'NA'));self.assertEqual(fetch.call_count,1)
                quote=book.all('NA')['Clear Liquid Reagent'];self.assertEqual(quote['unit_price'],12000);self.assertEqual(quote['stock'],45);self.assertEqual(quote['price_basis'],'market_base')
                self.assertEqual(first[0]['last_sold_price'],12500);self.assertTrue(first[0]['updated_at'])
            for invalid in ([],[True],[0],[1]*65,['5301']):
                with self.assertRaises(ValueError):book.recipe_id_quotes(invalid,'NA')

    def test_no_fallback_price_fields_in_any_new_recipe(self):
        self.assertEqual(len(recipes()),990)
        self.assertTrue(all('sell' not in r and all('fallback' not in m for m in r['mats']) for r in recipes()))
        for r in recipes():self.assertIn(str(r['itemId']),craft_spec()['items'])

    def test_locked_recursive_cost_matches_linked_plan_and_rejects_region_mix(self):
        r=next(r for r in recipes() if r['name']=='Beer')
        model=validate_model({'recipe_id':r['id'],'yield':2.5,'retention':84.5,'extra':5,'cost_basis':'recursive_plan','input_cost_per_batch':37.5,'region':'NA'})
        rows=[(1,'2026-11-02T10:00:00','Beer',25,'OCR','','Crafted')]
        value=session_economy(r,rows,{'Beer':{'unit_price':100,'source':'market','region':'NA'}},model)
        self.assertTrue(value['available']);self.assertEqual(value['ingredient_cost'],375)
        self.assertEqual(value['profit'],1687.5)
        self.assertFalse(session_economy(r,rows,{'Beer':{'unit_price':100,'source':'market','region':'EU'}},model)['available'])
        self.assertFalse(session_economy(r,rows,{},dict(model,input_cost_per_batch=None))['available'])


if __name__=='__main__':unittest.main()
