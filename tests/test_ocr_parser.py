"""Regression cases for BDO label OCR and noisy readings."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'desktop'))
from ocr_parser import choose_reading

class OCRParserTests(unittest.TestCase):
    def test_corrects_spurious_bracket_as_one(self):
        pair,n,fixed=choose_reading([(1350,3000)]*3,expected=350,expected_max=3000)
        self.assertEqual(pair,(350,3000));self.assertTrue(fixed)
    def test_keeps_legitimate_thousand(self):
        pair,n,fixed=choose_reading([(1350,3000)]*3,expected=1348,expected_max=3000)
        self.assertEqual(pair,(1350,3000));self.assertFalse(fixed)
    def test_no_context_never_strips_one(self):
        pair,n,fixed=choose_reading([(1350,3000)]*3)
        self.assertEqual(pair,(1350,3000));self.assertFalse(fixed)
    def test_majority_selection(self):
        pair,n,fixed=choose_reading([(350,3000)]*4+[(850,3000)],expected=349,expected_max=3000)
        self.assertEqual(pair,(350,3000));self.assertEqual(n,4)
    def test_rejects_invalid_readings(self):
        with self.assertRaises(ValueError):choose_reading([(500,300),(0,0)])
    def test_maximum_hint(self):
        pair,n,fixed=choose_reading([(200,1000)]*2+[(200,3000)]*2,expected=199,expected_max=3000)
        self.assertEqual(pair,(200,3000))
if __name__=='__main__':unittest.main()
