"""Synthetic physical word rows; no user captures or history in the test corpus."""
import sys,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from item_events import ItemEvent
from loot_positioned import physical_rows,personal_row,recover_personal_feed


def words(lines):
    out=[]
    for row,line in enumerate(lines):
        for col,text in enumerate(line.split()):
            out.append({'text':text,'line':col if row==0 else row,'x':col*100,'y':row*48,'w':90,'h':22})
    # Engine line order can place the item before its receipt prefix.
    return list(reversed(out))


class Worker:
    def __init__(self,first,second=None):self.rows=iter([first,first if second is None else second]);self.calls=0
    def recognize(self,image,**kwargs):self.calls+=1;return {'words':next(self.rows)}


class PositionedLootTests(unittest.TestCase):
    def resolve(self,name):return name if name in ('Milk','Beer','Mysterious Catalyst') else None

    def recover(self,worker,baseline=()):
        return recover_personal_feed(Image.new('RGB',(400,200)),worker,False,self.resolve,baseline)

    def test_physical_rows_restore_engine_split_order_without_fabricating_words(self):
        source=['You have obtained [Milk] x4.','You have obtained [Beer] x3.','You have obtained [Milk] x2.']
        self.assertEqual(physical_rows(words(source)),source)
        r=self.recover(Worker(words(source)))
        self.assertEqual([e.quantity for e in r['events']],[4,3,2]);self.assertEqual(len(r['slots']),3)

    def test_prefix_only_normalization_preserves_item_and_count_and_other_player_guard(self):
        self.assertEqual(personal_row('*You håve7öbtained t [Milk] x4.',False,self.resolve),ItemEvent('Milk',4,'Drop'))
        for text in ['Bob has obtained [Milk] x4.','[Milk] x4.','You have obtained [Milk] x7O.','You have obtained [Miłk] x4.','You have obtained [Milk] x-4.']:
            self.assertIsNone(personal_row(text,False,self.resolve),text)

    def test_two_rows_must_agree_and_old_consensus_cannot_be_overruled(self):
        a=words(['You have obtained [Milk] x4.','You have obtained [Beer] x3.','You have obtained [Milk] x2.'])
        b=words(['You have obtained [Milk] x9.','You have obtained [Beer] x3.','You have obtained [Milk] x2.'])
        r=self.recover(Worker(a,b));self.assertIsNone(r['slots'][0]);self.assertEqual(len(r['events']),2)
        self.assertIsNone(self.recover(Worker(a,b),[ItemEvent('Milk',4,'Drop')]))
        self.assertIsNone(self.recover(Worker(a),[ItemEvent('Milk',99,'Drop')]))
        self.assertIsNone(self.recover(Worker(a),[ItemEvent('Milk',4,'Drop'),ItemEvent('Beer',3,'Drop'),ItemEvent('Milk',2,'Drop')]))

    def test_different_row_counts_and_invalid_geometry_do_not_shift_events(self):
        a=words(['You have obtained [Milk] x4.']*3);b=words(['You have obtained [Milk] x4.']*4)
        self.assertIsNone(self.recover(Worker(a,b)))
        self.assertEqual(physical_rows([{'x':float('nan'),'y':0,'w':10,'h':10,'text':'Milk'}]),[])
        self.assertIsNone(self.recover(None));self.assertIsNone(recover_personal_feed(Image.new('RGB',(1500,1500)),Worker(a),False,self.resolve,[]))


if __name__=='__main__':unittest.main()
