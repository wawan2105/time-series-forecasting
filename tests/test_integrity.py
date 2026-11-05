import unittest
import json
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SourceIntegrity(unittest.TestCase):
    def test_snapshot_checksums(self):
        manifest=json.loads((ROOT/'data/source_manifest.json').read_text(encoding='utf-8'))
        self.assertTrue(manifest)
        for name,metadata in manifest.items():
            self.assertEqual(hashlib.sha256((ROOT/'data/raw'/name).read_bytes()).hexdigest(),metadata['sha256'])
    def test_actual_results_and_reports_exist(self):
        result=json.loads((ROOT/'outputs/metrics.json').read_text(encoding='utf-8'))
        self.assertTrue(result)
        text=(ROOT/'outputs/executive_summary.md').read_text(encoding='utf-8')
        self.assertIn('Limitations and Future Work',text)
        self.assertIn('CV-ready bullets',text)

import numpy as np
import pandas as pd
from src.run import forecast
class TemporalIntegrity(unittest.TestCase):
    def test_evaluation_never_precedes_origin_or_enters_holdout(self):
        d=pd.read_csv(ROOT/'outputs/tables/backtest_predictions.csv')
        self.assertTrue((d.year>d.origin).all())
        self.assertTrue((d.year<=d.origin+3).all())
        self.assertLessEqual(d.year.max(),2021)
        holdout=pd.read_csv(ROOT/'outputs/tables/test_predictions.csv')
        self.assertEqual(holdout.year.tolist(),[2022,2023,2024])
    def test_naive_baseline_has_no_future_information(self):
        history=np.array([100,110,121])
        pred,_,_=forecast('Naive',history,3)
        np.testing.assert_allclose(pred,[121,121,121])

if __name__=='__main__': unittest.main()
