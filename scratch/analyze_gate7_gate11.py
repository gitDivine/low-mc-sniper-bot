import pandas as pd
from pathlib import Path
import numpy as np

def analyze_batch8():
    filepath = Path(r"C:\Users\njoku\Downloads\resolved_tokens (8).csv")
    df = pd.read_csv(filepath)
    
    # The CSV already has outcome_label
    # Split into Micro and Graduate bands
    df_micro = df[(df['t0_mcap_usd'] >= 5000) & (df['t0_mcap_usd'] <= 30000)].copy()
    df_grad = df[(df['t0_mcap_usd'] >= 150000) & (df['t0_mcap_usd'] <= 500000)].copy()
    
    print("=" * 80)
    print("GATE 7 (BUY/SELL RATIO) RE-CALIBRATION DATA")
    print("=" * 80)
    
    def print_gate7_stats(subset_df, title, is_micro=False):
        print(f"\n--- {title} ---")
        winners = subset_df[subset_df['outcome_label'] == 'Winner']['t0_buy_sell_ratio'].dropna()
        rugs = subset_df[subset_df['outcome_label'] == 'Rug / dead']['t0_buy_sell_ratio'].dropna()
        scams = subset_df[subset_df['outcome_label'] == 'Scam / washed']['t0_buy_sell_ratio'].dropna()
        
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
                print(f"{name:12s} (n={len(data)}): 1st={p1:.2f} | 5th={p5:.2f} | 10th={p10:.2f} | 25th={p25:.2f} | Med={p50:.2f} | 75th={p75:.2f} | 90th={p90:.2f} | 95th={p95:.2f}")
    
    print_gate7_stats(df_micro, "MICRO MODE ($5k - $30k) BUY/SELL RATIO", is_micro=True)
    print_gate7_stats(df_grad, "GRADUATE MODE ($150k - $500k) BUY/SELL RATIO", is_micro=False)
    
    
    print("\n" + "=" * 80)
    print("GATE 11 (LIQUIDITY FLOOR) OVERLAP RE-CHECK (Batch 8)")
    print("=" * 80)
    
    def print_gate11_stats(subset_df, title):
        print(f"\n--- {title} ---")
        winners = subset_df[subset_df['outcome_label'] == 'Winner']['t0_liquidity_usd'].dropna()
        rugs = subset_df[subset_df['outcome_label'] == 'Rug / dead']['t0_liquidity_usd'].dropna()
        scams = subset_df[subset_df['outcome_label'] == 'Scam / washed']['t0_liquidity_usd'].dropna()
        
        for name, data in [("Winners", winners), ("Rugs/Dead", rugs), ("Scams/Washed", scams)]:
            if len(data) > 0:
                p5 = np.percentile(data, 5)
                p25 = np.percentile(data, 25)
                p50 = np.percentile(data, 50)
                p75 = np.percentile(data, 75)
                p90 = np.percentile(data, 90)
                p95 = np.percentile(data, 95)
                print(f"{name:12s} (n={len(data)}): 5th=${p5:.0f} | 25th=${p25:.0f} | Med=${p50:.0f} | 75th=${p75:.0f} | 90th=${p90:.0f} | 95th=${p95:.0f}")
                
    print_gate11_stats(df_micro, "MICRO MODE ($5k - $30k) INITIAL LIQUIDITY ($)")
    print_gate11_stats(df_grad, "GRADUATE MODE ($150k - $500k) INITIAL LIQUIDITY ($)")

if __name__ == '__main__':
    analyze_batch8()
