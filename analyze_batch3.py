import pandas as pd
import json

def main():
    file_path = r"C:\Users\njoku\Downloads\resolved_tokens (5).csv"
    print(f"Loading data from {file_path}")
    
    df = pd.read_csv(file_path)
    print(f"Total resolved tokens: {len(df)}")
    
    print("\n--- OUTCOME BREAKDOWN ---")
    outcome_counts = df['outcome_label'].value_counts()
    for label, count in outcome_counts.items():
        print(f"{label}: {count} ({count/len(df)*100:.1f}%)")
        
    winners = df[df['outcome_label'] == 'Winner'].copy()
    print(f"\nTotal Winners: {len(winners)}")
    
    if len(winners) > 0:
        print("\n--- WINNER T0 METRICS ANALYSIS ---")
        
        # Analyze metrics for Gates calibration that are available in CSV
        
        print("\nLiq/MCap Ratio (Gate 9):")
        if 'liq_mcap_ratio' in winners.columns:
            print(winners['liq_mcap_ratio'].describe(percentiles=[.05, .1, .25, .5, .75]))
        
        print("\nT0 Liquidity USD:")
        if 't0_liquidity_usd' in winners.columns:
            print(winners['t0_liquidity_usd'].describe(percentiles=[.05, .1, .25, .5, .75]))
            
        print("\nT0 Mcap USD:")
        if 't0_mcap_usd' in winners.columns:
            print(winners['t0_mcap_usd'].describe(percentiles=[.05, .1, .25, .5, .75]))

        # Are these real organics? Check their Top 10 and Dev percentages
        print("\n--- VERIFYING ORGANIC NATURE (Gates 4 & 5) ---")
        print("Top 10 Holder % (Should be <= 25.0):")
        if 't0_top10_holder_pct' in winners.columns:
            print(winners['t0_top10_holder_pct'].describe())
        
        print("\nDev Wallet % (Should be <= 5.0):")
        if 't0_dev_wallet_pct' in winners.columns:
            print(winners['t0_dev_wallet_pct'].describe())

if __name__ == "__main__":
    main()
