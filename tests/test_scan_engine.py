import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from scan_engine import select_ocr_passes,candidate_is_stable,should_publish,SpeedEstimator
from ocr_parser import reading_is_plausible

class ScanEngineTests(unittest.TestCase):
    def test_fast_passes_are_bounded(self):
        passes=select_ocr_passes()
        self.assertLessEqual(len(passes),6)
        self.assertEqual(passes[0],('contrast',7))
    def test_two_agree_with_expected(self):
        self.assertTrue(candidate_is_stable([(350,3000),(350,3000)],349,3000))
    def test_one_noisy_reading_is_not_enough(self):
        self.assertFalse(candidate_is_stable([(1350,3000)],350,3000))
    def test_wrong_maximum_rejected(self):
        self.assertFalse(candidate_is_stable([(350,2000)]*2,350,3000))
    def test_duplicate_skipped(self):
        self.assertFalse(should_publish((350,3000,'a'),(350,3000),10,15,'a'))
    def test_decrement_sent(self):
        self.assertTrue(should_publish((350,3000,'a'),(347,3000),10,15,'a'))
    def test_session_changed(self):
        self.assertTrue(should_publish((350,3000,'a'),(350,3000),10,15,'b'))
    def test_heartbeat(self):
        self.assertTrue(should_publish((350,3000,'a'),(350,3000),10,71,'a'))
    def test_passive_speed(self):
        est=SpeedEstimator()
        self.assertIsNone(est.add(350,3000,100,'a'))
        self.assertIsNone(est.add(340,3000,110,'a'))
        self.assertAlmostEqual(est.add(330,3000,120,'a'),1)
    def test_tool_reset_clears_speed(self):
        est=SpeedEstimator()
        est.add(350,3000,100,'a');est.add(340,3000,110,'a');est.add(330,3000,120,'a')
        self.assertIsNone(est.add(3000,3000,121,'b'))
    def test_plausibility(self):
        self.assertTrue(reading_is_plausible(346,3000,350,3000))
        self.assertFalse(reading_is_plausible(1350,3000,350,3000))

if __name__=='__main__':unittest.main()
