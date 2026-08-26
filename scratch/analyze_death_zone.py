import pandas as pd

def main():
    df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (8).csv")
    df = df[df['status'] == 'RESOLVED']
    
    # Check the $30k - $100k bucket
    bucket_df = df[(df['t0_mcap_usd'] >= 30000) & (df['t0_mcap_usd'] < 100000)]
    print("=== $30k - $100k BUCKET DANGER ANALYSIS ===")
    
    rugs = bucket_df[bucket_df['outcome_label'] == 'Rug / dead']
    print(f"Total Rugs in $30k-$100k: {len(rugs)}")
    
    print("\nTop 10 identical t0_top10_holder_pct values (Rugs):")
    print(rugs['t0_top10_holder_pct'].value_counts().head(10))
    
    print("\nTop 10 identical t0_liquidity_usd values (Rugs):")
    print(rugs['t0_liquidity_usd'].value_counts().head(10))
    
    scams = bucket_df[bucket_df['outcome_label'] == 'Scam / washed']
    print(f"\nTotal Scams in $30k-$100k: {len(scams)}")
    
    print("\nTop 10 identical t0_top10_holder_pct values (Scams):")
    print(scams['t0_top10_holder_pct'].value_counts().head(10))
    
    # Now check how many of these tokens would pass Gate 4 & 5 (the core rug filters)
    # Assume Gate 4 is top 10 <= 25%, Gate 5 is dev <= 5%
    passed_core_rug_filters = bucket_df[
        (bucket_df['t0_top10_holder_pct'] <= 25.0) & 
        (bucket_df['t0_dev_wallet_pct'] <= 5.0)
    ]
    
    print("\n=== TOKENS PASSING GATE 4 & 5 IN THIS BUCKET ===")
    print(passed_core_rug_filters['outcome_label'].value_counts())

if __name__ == "__main__":
    main()
