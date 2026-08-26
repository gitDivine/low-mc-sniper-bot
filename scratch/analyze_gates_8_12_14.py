import pandas as pd
import numpy as np

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from src.evaluator.scorer import OfflineScorer

def main():
    print("=" * 80)
    print("GATES 8 & 14 RE-CALIBRATION DATA")
    print("=" * 80)

    try:
        scorer = OfflineScorer()
        filepath = Path(r"C:\Users\njoku\Downloads\resolved_tokens (8).csv")
        records = scorer.load_dataset(filepath)
        df = pd.DataFrame([r.model_dump() for r in records])
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    df['t0_mcap_usd'] = pd.to_numeric(df['t0_mcap_usd'], errors='coerce')
    df['t0_single_wallet_vol_pct'] = pd.to_numeric(df['t0_single_wallet_vol_pct'], errors='coerce')
    df['pool_time'] = pd.to_numeric(df['pool_time'], errors='coerce')
    df['snapshot_timestamp'] = pd.to_numeric(df['snapshot_timestamp'], errors='coerce')
    df['age_minutes'] = (df['snapshot_timestamp'] - df['pool_time']) / 60.0

    df = df.dropna(subset=['outcome_label', 't0_mcap_usd'])

    # Modes
    df_micro = df[(df['t0_mcap_usd'] >= 5000) & (df['t0_mcap_usd'] <= 30000)]
    df_grad = df[(df['t0_mcap_usd'] >= 150000) & (df['t0_mcap_usd'] <= 500000)]

    def print_stats(subset_df, col, title):
        print(f"\n--- {title} ---")
        winners = subset_df[subset_df['outcome_label'] == 'Winner'][col].dropna()
        rugs = subset_df[subset_df['outcome_label'] == 'Rug / dead'][col].dropna()
        scams = subset_df[subset_df['outcome_label'] == 'Scam / washed'][col].dropna()
        
        for name, data in [("Winners", winners), ("Rugs/Dead", rugs), ("Scams/Washed", scams)]:
            if len(data) > 0:
                p1 = np.percentile(data, 1)
                p5 = np.percentile(data, 5)
                p10 = np.percentile(data, 10)
                p25 = np.percentile(data, 25)
                p50 = np.percentile(data, 50)
                p75 = np.percentile(data, 75)
                p90 = np.percentile(data, 90)
                p95 = np.percentile(data, 95)
                print(f"{name:12s} (n={len(data)}): 1st={p1:.2f} | 5th={p5:.2f} | 25th={p25:.2f} | Med={p50:.2f} | 75th={p75:.2f} | 90th={p90:.2f} | 95th={p95:.2f}")

    print_stats(df_micro, 't0_single_wallet_vol_pct', "MICRO MODE: Gate 8 (Single Wallet Vol %)")
    print_stats(df_grad, 't0_single_wallet_vol_pct', "GRADUATE MODE: Gate 8 (Single Wallet Vol %)")

    print_stats(df_micro, 'age_minutes', "MICRO MODE: Gate 14 (Age Minutes)")
    print_stats(df_grad, 'age_minutes', "GRADUATE MODE: Gate 14 (Age Minutes)")

if __name__ == "__main__":
    main()
