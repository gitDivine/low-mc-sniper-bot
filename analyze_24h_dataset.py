import pandas as pd

df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (2).csv")

print("=" * 65)
print("LIVE 24-HOUR SHADOW DATASET ANALYSIS REPORT")
print("=" * 65)
print(f"Total Resolved Tokens: {len(df)}")
print(f"Time Range: {df['t0_date'].min()} -> {df['tfinal_date'].max()}")
print("\n=== OUTCOME DISTRIBUTION ===")
counts = df['outcome_label'].value_counts()
for label, cnt in counts.items():
    pct = (cnt / len(df)) * 100
    print(f"  {label:<18}: {cnt:>4} ({pct:5.1f}%)")

print("\n=== ROI STATS BY OUTCOME ===")
for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
    sub = df[df["outcome_label"] == label]
    if len(sub) > 0:
        print(f"  {label:<18}: count={len(sub):<4} min={sub['roi_24h'].min():.2f}x  median={sub['roi_24h'].median():.2f}x  max={sub['roi_24h'].max():.2f}x  mean={sub['roi_24h'].mean():.2f}x")

print("\n=== GATE 9: LIQUIDITY / MARKET CAP RATIO ANALYSIS ===")
for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
    sub = df[df["outcome_label"] == label]
    if len(sub) > 0:
        pass_025 = (sub['liq_mcap_ratio'] >= 0.25).sum()
        pass_015 = (sub['liq_mcap_ratio'] >= 0.15).sum()
        mean_ratio = sub['liq_mcap_ratio'].mean()
        median_ratio = sub['liq_mcap_ratio'].median()
        print(f"  {label:<18}: >=0.25: {pass_025}/{len(sub)} ({pass_025/len(sub)*100:.1f}%) | >=0.15: {pass_015}/{len(sub)} ({pass_015/len(sub)*100:.1f}%) | Mean: {mean_ratio:.3f} | Median: {median_ratio:.3f}")

print("\n=== GATE 4: TOP 10 HOLDER % ANALYSIS ===")
for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
    sub = df[df["outcome_label"] == label]
    if len(sub) > 0:
        print(f"  {label:<18}: Mean Top10%: {sub['t0_top10_holder_pct'].mean():.2f}% | Median: {sub['t0_top10_holder_pct'].median():.2f}% | <=20%: {(sub['t0_top10_holder_pct'] <= 20).sum()}/{len(sub)}")

print("\n=== GATE 5: DEV WALLET % ANALYSIS ===")
for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
    sub = df[df["outcome_label"] == label]
    if len(sub) > 0:
        print(f"  {label:<18}: Mean Dev%: {sub['t0_dev_wallet_pct'].mean():.2f}% | Median: {sub['t0_dev_wallet_pct'].median():.2f}% | <=3%: {(sub['t0_dev_wallet_pct'] <= 3).sum()}/{len(sub)}")

print("\n=== TOP 10 WINNERS IN DATASET ===")
winners = df[df["outcome_label"] == "Winner"].sort_values(by="roi_24h", ascending=False)
if len(winners) > 0:
    for idx, row in winners.head(10).iterrows():
        print(f"  Symbol: {row['symbol']:<10} | 24h ROI: {row['roi_24h']:>7.2f}x | T0 MCap: ${row['t0_mcap_usd']:>9,.0f} | T0 Liq: ${row['t0_liquidity_usd']:>8,.0f} | Ratio: {row['liq_mcap_ratio']:.3f} | Top10: {row['t0_top10_holder_pct']:.1f}% | Dev: {row['t0_dev_wallet_pct']:.1f}% | Lock: {row['t0_lp_locked_days']}d")
else:
    print("  No winners yet in resolved set.")

print("=" * 65)
