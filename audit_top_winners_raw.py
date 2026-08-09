import pandas as pd

df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (3).csv")

# Filter out initial test-mode tokens (< 20 hours)
df_24h = df[(df["tfinal_timestamp"] - df["t0_timestamp"]) / 3600.0 >= 20.0]

# Filter strict Gate 11 scope ($30k-$100k MCap & >= $10k Liq)
strict_df = df_24h[
    (df_24h["t0_mcap_usd"] >= 30000) & 
    (df_24h["t0_mcap_usd"] <= 100000) & 
    (df_24h["t0_liquidity_usd"] >= 10000)
].copy()

top_winners = strict_df.sort_values(by="roi_24h", ascending=False).head(10)

print("=" * 80)
print("REAL RAW AUDIT OF TOP 10 WINNERS IN RESOLVED_TOKENS (3).CSV")
print("=" * 80)

for idx, row in top_winners.iterrows():
    print(f"Row #{idx}: Symbol='{row['symbol']}'")
    print(f"  Token Address : {row['token_address']}")
    print(f"  Pool Address  : {row['pool_address']}")
    print(f"  T0 Date       : {row['t0_date']}")
    print(f"  T0 Price      : ${row['t0_price_usd']:.8f}")
    print(f"  T0 MCap       : ${row['t0_mcap_usd']:,.2f}")
    print(f"  T0 Liquidity  : ${row['t0_liquidity_usd']:,.2f}")
    print(f"  T0 Dev Wallet%: {row['t0_dev_wallet_pct']:.1f}%")
    print(f"  T0 Top10 %    : {row['t0_top10_holder_pct']:.1f}%")
    print(f"  TFinal Date   : {row['tfinal_date']}")
    print(f"  TFinal Price  : ${row['tfinal_24h_price_usd']:.8f}")
    print(f"  24h ROI       : {row['roi_24h']:,.2f}x")
    print("-" * 80)
