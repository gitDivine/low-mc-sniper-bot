import pandas as pd
import numpy as np

def main():
    df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (8).csv")
    df = df[df['status'] == 'RESOLVED']
    df = df.dropna(subset=['t0_liquidity_usd', 't0_mcap_usd']).copy()
    df['liq_ratio'] = df['t0_liquidity_usd'] / df['t0_mcap_usd']
    
    print("=========================================================")
    print("1. MICRO BAND ($5k - $30k) BOUNDARY OVERLAP CHECK")
    print("=========================================================")
    micro_df = df[(df['t0_mcap_usd'] >= 5000) & (df['t0_mcap_usd'] < 30000)]
    
    for outcome in ['Winner', 'Scam / washed', 'Rug / dead']:
        sub_df = micro_df[micro_df['outcome_label'] == outcome]
        print(f"--- {outcome.upper()} ---")
        if len(sub_df) == 0:
            print("No tokens in this bucket.")
            continue
        print(sub_df[['t0_liquidity_usd', 'liq_ratio']].describe(percentiles=[0.10, 0.25, 0.5, 0.75, 0.90]).to_string())
        print()
        
    print("=========================================================")
    print("2. GRADUATE BAND ($150k - $500k) LIQUIDITY & RATIO CHECK")
    print("=========================================================")
    grad_df = df[(df['t0_mcap_usd'] >= 150000) & (df['t0_mcap_usd'] <= 500000)]
    
    for outcome in ['Winner', 'Scam / washed', 'Rug / dead']:
        sub_df = grad_df[grad_df['outcome_label'] == outcome]
        print(f"--- {outcome.upper()} ---")
        if len(sub_df) == 0:
            print("No tokens in this bucket.")
            continue
        print(sub_df[['t0_liquidity_usd', 'liq_ratio']].describe(percentiles=[0.10, 0.25, 0.5, 0.75, 0.90]).to_string())
        print()

    print("=========================================================")
    print("3. SCAM CONCENTRATION CHECK ($100k - $150k)")
    print("=========================================================")
    scam_df = df[(df['t0_mcap_usd'] >= 100000) & (df['t0_mcap_usd'] < 150000) & (df['outcome_label'] == 'Scam / washed')]
    print(f"Total Scams in $100k-$150k: {len(scam_df)}")
    
    # Check for duplicate liquidity or mcap values (signs of scripted launches)
    print("\nTop 5 identical t0_liquidity_usd values:")
    print(scam_df['t0_liquidity_usd'].value_counts().head(5))
    print("\nTop 5 identical t0_mcap_usd values:")
    print(scam_df['t0_mcap_usd'].value_counts().head(5))
    print("\nTop 5 identical t0_top10_holder_pct values:")
    print(scam_df['t0_top10_holder_pct'].value_counts().head(5))
    print("\nTop 5 identical t0_buy_sell_ratio values:")
    print(scam_df['t0_buy_sell_ratio'].value_counts().head(5))
    
    # Show a few sample rows to visually inspect
    print("\nSample Scams in this bucket:")
    cols_to_show = ['t0_mcap_usd', 't0_liquidity_usd', 't0_top10_holder_pct', 't0_buy_sell_ratio', 't0_volume_usd_15m']
    print(scam_df[cols_to_show].head(10).to_string())

if __name__ == "__main__":
    main()
