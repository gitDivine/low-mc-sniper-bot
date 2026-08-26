import pandas as pd

def main():
    file_path = r"C:\Users\njoku\Downloads\resolved_tokens (5).csv"
    df = pd.read_csv(file_path)
    
    winners = df[df['outcome_label'] == 'Winner'].copy()
    
    # Ensure liq_mcap_ratio exists
    if 'liq_mcap_ratio' not in winners.columns:
        winners['liq_mcap_ratio'] = winners['t0_liquidity_usd'] / winners['t0_mcap_usd']
        
    bottom_3 = winners.sort_values(by='liq_mcap_ratio').head(3)
    
    print("--- BOTTOM 3 ORGANIC WINNERS BY LIQ/MCAP RATIO ---")
    for idx, row in bottom_3.iterrows():
        print(f"\nToken: {row['symbol']} ({row['pool_address']})")
        print(f"Liq/MCap Ratio: {row['liq_mcap_ratio']:.4f}")
        print(f"T0 Liquidity: ${row['t0_liquidity_usd']:.2f}")
        print(f"T0 Market Cap: ${row['t0_mcap_usd']:.2f}")
        print(f"Gate 11b Absolute Liquidity > $10k? {'Yes' if row['t0_liquidity_usd'] >= 10000 else 'No'}")
        print(f"T0 Top10: {row.get('t0_top10_holder_pct', 'N/A')}% | T0 Dev: {row.get('t0_dev_wallet_pct', 'N/A')}%")
        print(f"TFinal 24h ROI: {row.get('roi_24h', 'N/A')}")
        print("-" * 50)

if __name__ == "__main__":
    main()
