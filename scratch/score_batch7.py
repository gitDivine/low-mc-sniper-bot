import os
import sys
import pandas as pd
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.evaluator.scorer import OfflineScorer
from src.data_puller.harvester import TokenSnapshotRecord

def main():
    df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (7).csv")
    df = df.where(pd.notnull(df), None)
    
    # Exclude DROPPED tokens
    df = df[df['status'] == 'RESOLVED']
    
    records_dict = df.to_dict('records')
    for r in records_dict:
        r.setdefault('chain', 'solana')
        r.setdefault('name', 'Unknown')
        r.setdefault('created_at_utc', '2026-08-01T00:00:00Z')
        r.setdefault('age_hours', 1.0)
    records = [TokenSnapshotRecord.model_construct(**r) for r in records_dict]
    
    scorer = OfflineScorer()
    scorer.evaluate_all(records)
    
    passed_winners = [r for r in scorer.scored_records if r.outcome_label == 'Winner' and r.passed_all_gates]
    failed_winners = [r for r in scorer.scored_records if r.outcome_label == 'Winner' and not r.passed_all_gates]
    
    print(f"Total Winners Passed: {len(passed_winners)}")
    print(f"Total Winners Failed: {len(failed_winners)}\n")
    
    from collections import Counter
    reasons = Counter([r.first_failed_gate for r in failed_winners])
    print("--- Where Did Winners Fail? ---")
    for reason, count in reasons.most_common():
        print(f"{count:3d} : {reason}")


if __name__ == "__main__":
    main()
