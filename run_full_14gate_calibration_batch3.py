import pandas as pd
from pathlib import Path
from src.evaluator.scorer import OfflineScorer

scorer = OfflineScorer()
csv_file = Path(r"C:\Users\njoku\Downloads\resolved_tokens (3).csv")

records = scorer.load_dataset(csv_file)

# Exclude initial test-mode tokens (< 20 hours)
records = [r for r in records if r.tfinal_24h_vol_usd >= 0] # all 24h tokens

scored = scorer.evaluate_all(records)
report = scorer.generate_calibration_report()

print("=" * 80)
print("FULL 14-GATE PIPELINE CALIBRATION REPORT ON DATASET #3 (4,383 TOKENS)")
print("=" * 80)
print(report)
