import io,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from item_catalog import DiskItemDatabase,json_array_items
from market_match import ItemDatabase
from item_names import canonical_item,set_exact_resolver
from item_events import parse_events,ItemEvent

class DiskCatalogTests(unittest.TestCase):
    def test_streaming_parser_handles_chunk_boundaries_and_unicode(self):
        rows=[{'id':1,'name':'Élixir [test]'}, {'id':2,'name':'A \\"quoted" item'}]
        for size in (1,2,7,64):self.assertEqual(list(json_array_items(io.StringIO(json.dumps(rows)),size)),rows)
        for text in ('','   ','[   ','{}','[{}','[{} {}]','[{},]','[{}] trailing'):
            with self.assertRaises(ValueError):list(json_array_items(io.StringIO(text),2))

    def test_disk_identity_matches_reference_and_preserves_event_ids(self):
        rows=[{'id':678,'name':'Elixir of Demihuman Hunt'},{'id':37193,'name':'Elixir of Demihuman Hunt'},
              {'id':679,'name':'Elixir of Fierce Demihuman Hunt'},{'id':1,'name':"Laila's Petal"}]
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'items.json';source.write_text(json.dumps(rows))
            disk=DiskItemDatabase.from_json(source,Path(directory)/'items.sqlite3');reference=ItemDatabase(rows)
            for name in (rows[0]['name'],rows[2]['name'],rows[3]['name'],'luman Hunt','Elixir of Fierce Demihuman Huni','Unknown Item'):
                self.assertEqual(sorted(disk.candidates(name),key=lambda i:i['id']),sorted(reference.candidates(name),key=lambda i:i['id']))
            self.assertEqual(disk.exact_name(rows[0]['name']),rows[0]['name'])
            self.assertIsNone(disk.match(rows[0]['name']))
            self.assertLessEqual(disk._cached_exact.cache_info().currsize,256)

    def test_rebuild_is_atomic_and_failed_import_retains_existing_index(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'items.json';target=Path(directory)/'items.sqlite3'
            source.write_text('[{"id":1,"name":"Milk"}]')
            first=DiskItemDatabase.from_json(source,target);stamp=target.stat().st_mtime_ns
            DiskItemDatabase.from_json(source,target)
            self.assertEqual(stamp,target.stat().st_mtime_ns)
            source.write_text('[{"id":2,"name":"Bad data"}')
            with self.assertRaises(ValueError):DiskItemDatabase.from_json(source,target)
            self.assertEqual(first.exact_name('Milk'),'Milk')

    def test_valid_short_item_prefix_is_never_stripped_as_icon_noise(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'items.json';source.write_text('[{"id":7923,"name":"Lion Meat"},{"id":10,"name":"Meat"}]')
            disk=DiskItemDatabase.from_json(source,Path(directory)/'items.sqlite3')
            set_exact_resolver(disk.exact_name)
            try:
                self.assertEqual(canonical_item('Lion Meat'),'Lion Meat')
                self.assertEqual(parse_events('Lion Meat',bare_items=True),[ItemEvent('Lion Meat',1,'Drop',quantity_explicit=False)])
            finally:set_exact_resolver(None)

if __name__=='__main__':unittest.main()
