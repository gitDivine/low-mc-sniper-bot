import pandas as pd

# Load the existing harvest
df = pd.read_csv("data/raw/historical_tokens_solana_20260806_223859.csv")

# Re-label using ROI only (fixing the broken reserve_usd=0 bug)
def relabel(row):
    roi = row["tfinal_24h_price_usd"] / row["t0_price_usd"] if row["t0_price_usd"] > 0 else 0.0
    if roi >= 2.0:
        return "Winner", f"24h ROI was {roi:.2f}x", roi
    elif roi <= 0.2:
        return "Rug / dead", f"24h ROI plummeted to {roi:.2f}x", roi
    else:
        return "Flat / mediocre", f"Survived but ROI only {roi:.2f}x", roi

results = df.apply(relabel, axis=1, result_type="expand")
df["outcome_label"] = results[0]
df["outcome_reason"] = results[1]
df["roi_24h"] = results[2]

print("=" * 60)
print("CORRECTED ANALYSIS — 40 REAL SOLANA TOKENS")
print("=" * 60)
print()

# Outcome breakdown
print("=== OUTCOME BREAKDOWN (ROI-based, bug fixed) ===")
for label, count in df["outcome_label"].value_counts().items():
    pct = count / len(df) * 100
    print(f"  {label}: {count} ({pct:.1f}%)")
print()

# ROI stats per outcome
print("=== ROI DISTRIBUTION BY OUTCOME ===")
for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
    subset = df[df["outcome_label"] == label]
    if len(subset) > 0:
        print(f"  {label} ({len(subset)} tokens):")
        print(f"    Mean ROI: {subset['roi_24h'].mean():.2f}x")
        print(f"    Median ROI: {subset['roi_24h'].median():.2f}x")
        print(f"    Range: {subset['roi_24h'].min():.4f}x — {subset['roi_24h'].max():.2f}x")
print()

# Gate 1 cross-tabulated with outcome
print("=== GATE 1: LP LOCK/BURN vs OUTCOME ===")
for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
    subset = df[df["outcome_label"] == label]
    if len(subset) > 0:
        burned = (subset["t0_lp_locked_days"] >= 30).sum()
        print(f"  {label}: {burned}/{len(subset)} have LP burned/locked")
print()

# Gate 4 cross-tabulated
print("=== GATE 4: TOP 10 HOLDER % vs OUTCOME ===")
for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
    subset = df[df["outcome_label"] == label]
    if len(subset) > 0:
        passed = (subset["t0_top10_holder_pct"] <= 20).sum()
        mean_pct = subset["t0_top10_holder_pct"].mean()
        print(f"  {label}: {passed}/{len(subset)} pass (<=20%), mean={mean_pct:.1f}%")
print()

# Gate 5 cross-tabulated
print("=== GATE 5: DEV WALLET % vs OUTCOME ===")
for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
    subset = df[df["outcome_label"] == label]
    if len(subset) > 0:
        passed = (subset["t0_dev_wallet_pct"] <= 3).sum()
        mean_pct = subset["t0_dev_wallet_pct"].mean()
        print(f"  {label}: {passed}/{len(subset)} pass (<=3%), mean={mean_pct:.1f}%")
print()

# Gate 11a
print("=== GATE 11a: TOKEN-2022 vs OUTCOME ===")
for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
    subset = df[df["outcome_label"] == label]
    if len(subset) > 0:
        t2022 = subset["t0_is_token_2022"].sum()
        print(f"  {label}: {t2022}/{len(subset)} are Token-2022")
print()

# Volume sanity
print("=== T0 VOLUME vs OUTCOME ===")
for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
    subset = df[df["outcome_label"] == label]
    if len(subset) > 0:
        mean_vol = subset["t0_volume_usd_15m"].mean()
        median_vol = subset["t0_volume_usd_15m"].median()
        print(f"  {label}: mean vol=${mean_vol:,.0f}, median vol=${median_vol:,.0f}")
print()

# Show winners detail
winners = df[df["outcome_label"] == "Winner"]
if len(winners) > 0:
    print(f"=== WINNER DETAILS ({len(winners)} tokens) ===")
    cols = ["symbol", "roi_24h", "t0_price_usd", "tfinal_24h_price_usd", "t0_lp_locked_days", "t0_top10_holder_pct", "t0_dev_wallet_pct", "t0_volume_usd_15m"]
    print(winners[cols].to_string())
    print()

# Show rugs detail
rugs = df[df["outcome_label"] == "Rug / dead"]
if len(rugs) > 0:
    print(f"=== RUG/DEAD DETAILS (first 5 of {len(rugs)}) ===")
    cols = ["symbol", "roi_24h", "t0_price_usd", "tfinal_24h_price_usd", "t0_lp_locked_days", "t0_top10_holder_pct", "t0_dev_wallet_pct", "t0_volume_usd_15m"]
    print(rugs[cols].head(5).to_string())
print()

# Known limitations
print("=== KNOWN LIMITATIONS ===")
print("  1. Gates 4 & 5 (holder %) reflect CURRENT state, not T0 state.")
print("     Post-rug tokens concentrate into few wallets, inflating these values.")
print("  2. Gates 6,7,8,10,12,13 (swap-dependent) are N/A in this run.")
print("  3. Gate 9 (liq/mcap ratio) uses current mcap/liq which may be 0 for dead tokens.")
print("  4. All symbols show 'UNKNOWN' because we used stub dicts without DexScreener metadata.")
