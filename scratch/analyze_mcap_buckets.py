import pandas as pd
import numpy as np

def main():
    df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (8).csv")
    df = df[df['status'] == 'RESOLVED']
    
    # Define bins
    bins = [0, 5000, 15000, 30000, 50000, 100000, 150000, 300000, 500000, np.inf]
    labels = ['$0-5k', '$5k-15k', '$15k-30k', '$30k-50k', '$50k-100k', '$100k-150k', '$150k-300k', '$300k-500k', '$500k+']
    
    df['mcap_bucket'] = pd.cut(df['t0_mcap_usd'], bins=bins, labels=labels, right=False)
    
    # 1. Bucket distribution
    pivot = pd.crosstab(df['mcap_bucket'], df['outcome_label'], margins=True)
    print("=== MARKET CAP BUCKETS VS OUTCOME ===")
    print(pivot)
    
    # Winner rates per bucket
    print("\n=== WINNER, RUG & SCAM RATES PER BUCKET ===")
    bucket_stats = []
    for bucket in labels:
        bdf = df[df['mcap_bucket'] == bucket]
        total = len(bdf)
        if total == 0:
            continue
        winners = len(bdf[bdf['outcome_label'] == 'Winner'])
        rugs = len(bdf[bdf['outcome_label'] == 'Rug / dead'])
        scams = len(bdf[bdf['outcome_label'] == 'Scam / washed'])
        
        winner_rate = (winners / total) * 100
        rug_rate = (rugs / total) * 100
        scam_rate = (scams / total) * 100
        bucket_stats.append(f"{bucket:<10} | Total: {total:<4} | Winners: {winners:<3} ({winner_rate:>5.1f}%) | Rugs: {rugs:<4} ({rug_rate:>5.1f}%) | Scams: {scams:<3} ({scam_rate:>4.1f}%)")
        
    for stat in bucket_stats:
        print(stat)
        
    # 2. Deep Dive: $5k-$25k range (let's use $5k-$30k buckets combined)
    print("\n=== LIQUIDITY CHECK: $5k-$30k MARKET CAP ===")
    micro_df = df[(df['t0_mcap_usd'] >= 5000) & (df['t0_mcap_usd'] < 30000)]
    print(f"Total tokens in $5k-$30k range: {len(micro_df)}")
    
    # Calculate liq/mcap ratio
    # Note: t0_liquidity_usd might have some zeroes or NaNs, so we need to be careful
    micro_df = micro_df.dropna(subset=['t0_liquidity_usd', 't0_mcap_usd']).copy()
    micro_df['liq_ratio'] = micro_df['t0_liquidity_usd'] / micro_df['t0_mcap_usd']
    
    for outcome in ['Winner', 'Rug / dead', 'Scam / washed']:
        sub_df = micro_df[micro_df['outcome_label'] == outcome]
        print(f"--- {outcome.upper()} ---")
        if len(sub_df) == 0:
            print("No tokens in this bucket.")
            continue
        print(sub_df[['t0_liquidity_usd', 'liq_ratio']].describe(percentiles=[0.25, 0.5, 0.75]).to_string())
        print()

if __name__ == "__main__":
    main()
