from pathlib import Path
from src.evaluator.scorer import OfflineScorer

scorer = OfflineScorer()
csv_file = Path(r"C:\Users\njoku\Downloads\resolved_tokens (2).csv")

records = scorer.load_dataset(csv_file)
scored = scorer.evaluate_all(records)
report = scorer.generate_calibration_report()

print(report)
