import pandas as pd

df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (2).csv")

# Filter out early pre-fill dust tokens (< $10k mcap)
clean_df = df[df["t0_mcap_usd"] >= 10000].copy()

print("=" * 65)
print("CLEAN 24H DATASET CALIBRATION (FILTERED T0 MCAP >= $10k)")
print("=" * 65)
print(f"Clean Candidates: {len(clean_df)} (Excluded {len(df) - len(clean_df)} dust tokens)")

counts = clean_df['outcome_label'].value_counts()
print("\nClean Outcome Breakdown:")
for label, cnt in counts.items():
    print(f"  {label:<18}: {cnt} ({(cnt/len(clean_df))*100:.1f}%)")

print("\n=== TOP WINNERS (MCap >= $10k) ===")
winners = clean_df[clean_df["outcome_label"] == "Winner"].sort_values(by="roi_24h", ascending=False)
for idx, row in winners.iterrows():
    print(f"  Symbol: {row['symbol']:<10} | 24h ROI: {row['roi_24h']:>7.2f}x | T0 MCap: ${row['t0_mcap_usd']:>9,.0f} | T0 Liq: ${row['t0_liquidity_usd']:>8,.0f} | Liq/MCap Ratio: {row['liq_mcap_ratio']:.3f} | Top10%: {row['t0_top10_holder_pct']:.1f}% | Dev%: {row['t0_dev_wallet_pct']:.1f}%")

print("\n=== RUG / DEAD TOKENS (MCap >= $10k) ===")
rugs = clean_df[clean_df["outcome_label"] == "Rug / dead"].sort_values(by="roi_24h")
print(f"Total Rugs: {len(rugs)}")
print(f"  Mean Liq/MCap Ratio: {rugs['liq_mcap_ratio'].mean():.3f} | Median: {rugs['liq_mcap_ratio'].median():.3f}")
print(f"  Rugs with Liq/MCap Ratio < 0.25: {(rugs['liq_mcap_ratio'] < 0.25).sum()} / {len(rugs)} ({(rugs['liq_mcap_ratio'] < 0.25).sum()/len(rugs)*100:.1f}%)")

print("\n=== WINNERS vs RUGS FEATURE COMPARISON ===")
print(f"  Winners Mean Liq/MCap Ratio : {winners['liq_mcap_ratio'].mean():.3f}")
print(f"  Rugs Mean Liq/MCap Ratio    : {rugs['liq_mcap_ratio'].mean():.3f}")
print(f"  Winners % with Ratio >= 0.20: {(winners['liq_mcap_ratio'] >= 0.20).sum()}/{len(winners)} ({(winners['liq_mcap_ratio'] >= 0.20).sum()/len(winners)*100:.1f}%)")
print(f"  Rugs % with Ratio < 0.20   : {(rugs['liq_mcap_ratio'] < 0.20).sum()}/{len(rugs)} ({(rugs['liq_mcap_ratio'] < 0.20).sum()/len(rugs)*100:.1f}%)")
print("=" * 65)
