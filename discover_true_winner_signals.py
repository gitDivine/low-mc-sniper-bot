import pandas as pd
import numpy as np

df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (3).csv")
df["time_delta_hours"] = (df["tfinal_timestamp"] - df["t0_timestamp"]) / 3600.0

df_24h = df[df["time_delta_hours"] >= 20.0].copy()
strict_df = df_24h[
    (df_24h["t0_mcap_usd"] >= 30000) & 
    (df_24h["t0_mcap_usd"] <= 100000) & 
    (df_24h["t0_liquidity_usd"] >= 10000)
].copy()

winners = strict_df[strict_df["outcome_label"] == "Winner"]
rugs = strict_df[strict_df["outcome_label"] == "Rug / dead"]
flats = strict_df[strict_df["outcome_label"] == "Flat / mediocre"]

print("=" * 75)
print("FEATURE DIFFERENTIAL AUDIT: WINNERS vs RUGS (1,055 SCOPE CANDIDATES)")
print("=" * 75)

metrics = [
    "t0_price_usd", "t0_liquidity_usd", "t0_mcap_usd", "t0_volume_usd_15m",
    "t0_top10_holder_pct", "t0_dev_wallet_pct", "liq_mcap_ratio"
]

for m in metrics:
    if m in strict_df.columns:
        w_mean = winners[m].mean()
        r_mean = rugs[m].mean()
        f_mean = flats[m].mean()
        w_med = winners[m].median()
        r_med = rugs[m].median()
        print(f"  {m:<24}: Winner Mean={w_mean:>12.2f} (Med={w_med:>10.2f}) | Rug Mean={r_mean:>12.2f} (Med={r_med:>10.2f}) | Flat Mean={f_mean:>12.2f}")

print("\n--- 15M Volume / Liquidity Ratio ---")
strict_df["vol_liq_ratio"] = strict_df["t0_volume_usd_15m"] / (strict_df["t0_liquidity_usd"] + 1)
winners = strict_df[strict_df["outcome_label"] == "Winner"]
rugs = strict_df[strict_df["outcome_label"] == "Rug / dead"]
flats = strict_df[strict_df["outcome_label"] == "Flat / mediocre"]

print(f"  Winner Mean Vol/Liq Ratio: {winners['vol_liq_ratio'].mean():.4f} | Median: {winners['vol_liq_ratio'].median():.4f}")
print(f"  Rug    Mean Vol/Liq Ratio: {rugs['vol_liq_ratio'].mean():.4f} | Median: {rugs['vol_liq_ratio'].median():.4f}")
print(f"  Flat   Mean Vol/Liq Ratio: {flats['vol_liq_ratio'].mean():.4f} | Median: {flats['vol_liq_ratio'].median():.4f}")

print("\n--- 15M Volume / Mcap Ratio ---")
strict_df["vol_mcap_ratio"] = strict_df["t0_volume_usd_15m"] / (strict_df["t0_mcap_usd"] + 1)
winners = strict_df[strict_df["outcome_label"] == "Winner"]
rugs = strict_df[strict_df["outcome_label"] == "Rug / dead"]

print(f"  Winner Mean Vol/MCap Ratio: {winners['vol_mcap_ratio'].mean():.4f} | Median: {winners['vol_mcap_ratio'].median():.4f}")
print(f"  Rug    Mean Vol/MCap Ratio: {rugs['vol_mcap_ratio'].mean():.4f} | Median: {rugs['vol_mcap_ratio'].median():.4f}")

print("=" * 75)
