import pandas as pd

df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (2).csv")

dave_rows = df[df["symbol"].str.upper() == "DAVE"]

print("=" * 70)
print("RAW AUDIT: ALL DAVE TOKEN ROWS IN DATASET")
print("=" * 70)
print(f"Total 'Dave' Rows Found: {len(dave_rows)}")

for idx, row in dave_rows.iterrows():
    print(f"\nRow Index #{idx}:")
    print(f"  Symbol        : {row['symbol']}")
    print(f"  Pool Address  : {row['pool_address']}")
    print(f"  Token Address : {row['token_address']}")
    print(f"  T0 Date       : {row['t0_date']}")
    print(f"  T0 Price      : ${row['t0_price_usd']:.8f}")
    print(f"  T0 MCap       : ${row['t0_mcap_usd']:,.2f}")
    print(f"  T0 Liquidity  : ${row['t0_liquidity_usd']:,.2f}")
    print(f"  Liq/MCap Ratio: {row['liq_mcap_ratio']:.4f}")
    print(f"  TFinal Date   : {row['tfinal_date']}")
    print(f"  TFinal Price  : ${row['tfinal_24h_price_usd']:.8f}")
    print(f"  24h ROI       : {row['roi_24h']:.2f}x")
    print(f"  Outcome Label : {row['outcome_label']}")
print("=" * 70)
