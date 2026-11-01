import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from tool_status import ToolStatus


def report(current=95,wear=0,active=None):
    return {'tools':[{'id':'a','name':'Alchemy Tool','current':current,'maximum':3000,
                     'wear_streak':wear,'state':'Visible','box':[1,2,3,4]}],
            'active_id':active,'duration':.5,'ocr_calls':2,'captured_at':100}


class ToolStatusTests(unittest.TestCase):
    def test_found_confirming_tracking_and_paused_are_distinct(self):
        status=ToolStatus();status.accept(report());self.assertEqual(status.stage,'found')
        status.accept(report(94,1));self.assertEqual(status.stage,'confirming')
        status.accept(report(93,2,'a'));self.assertEqual(status.stage,'tracking')
        status.set_stage('paused','BDO is covered')
        self.assertEqual(status.snapshot()['tools'][0]['current'],93)
        self.assertEqual(status.snapshot()['last_read_at'],100)

    def test_empty_and_unreadable_are_explained(self):
        status=ToolStatus();status.accept(report(0));self.assertEqual(status.stage,'empty')
        status.accept({'tools':[],'unreadable':[{'name':'Tool'}]})
        self.assertEqual(status.stage,'searching');self.assertIn('unreadable',status.detail)

    def test_history_and_data_are_bounded_without_capture_contents(self):
        status=ToolStatus()
        for n in range(40):status.set_stage('reading',str(n)+'x'*500)
        self.assertEqual(len(status.snapshot()['recent']),16);self.assertEqual(len(status.detail),220)
        status.accept(report());view=status.snapshot();self.assertNotIn('box',view['tools'][0])
        view['tools'][0]['current']=999
        self.assertEqual(status.snapshot()['tools'][0]['current'],95)
        revision=status.revision
        self.assertFalse(status.set_stage(status.stage,status.detail));self.assertEqual(status.revision,revision)
