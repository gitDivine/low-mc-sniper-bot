import pandas as pd

df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (2).csv")
df["time_delta_hours"] = (df["tfinal_timestamp"] - df["t0_timestamp"]) / 3600.0

# 1. Require true 24h settled window (exclude test-mode 14m tokens)
df_24h = df[df["time_delta_hours"] >= 20.0].copy()

# 2. Require strict Gate 11a & 11b Spec V2 thresholds ($30k-$100k MCap & >= $10k Liquidity)
strict_df = df_24h[
    (df_24h["t0_mcap_usd"] >= 30000) & 
    (df_24h["t0_mcap_usd"] <= 100000) & 
    (df_24h["t0_liquidity_usd"] >= 10000)
].copy()

print("=" * 70)
print("STRICT SPEC V2 24-HOUR DATASET AUDIT ($30k-$100k MCap & >=$10k Liq)")
print("=" * 70)
print(f"Total 24h Settled Tokens in CSV : {len(df_24h)}")
print(f"Tokens Matching Strict Gate 11  : {len(strict_df)}")

print("\n=== OUTCOME DISTRIBUTION IN STRICT SPEC TARGET SCOPE ===")
counts = strict_df['outcome_label'].value_counts()
for label, cnt in counts.items():
    pct = (cnt / len(strict_df)) * 100
    print(f"  {label:<18}: {cnt:>3} ({pct:5.1f}%)")

print("\n=== ALL CANDIDATES IN STRICT GATE 11 SCOPE ($30k-$100k MCap) ===")
for idx, row in strict_df.sort_values(by="roi_24h", ascending=False).iterrows():
    print(f"  [{row['outcome_label']:<15}] Symbol: {row['symbol']:<10} | 24h ROI: {row['roi_24h']:>6.2f}x | T0 MCap: ${row['t0_mcap_usd']:>7,.0f} | T0 Liq: ${row['t0_liquidity_usd']:>6,.0f} | Liq/MCap Ratio: {row['liq_mcap_ratio']:.3f} | Top10%: {row['t0_top10_holder_pct']:.1f}% | Dev%: {row['t0_dev_wallet_pct']:.1f}%")

print("=" * 70)
