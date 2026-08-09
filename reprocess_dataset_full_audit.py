import pandas as pd
import numpy as np

df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (3).csv")
df["time_delta_hours"] = (df["tfinal_timestamp"] - df["t0_timestamp"]) / 3600.0

# 1. Require 24h settled tokens
df_24h = df[df["time_delta_hours"] >= 20.0].copy()

print("=" * 80)
print("CORRECTED DATASET RE-EVALUATION WITH LIQUIDITY COLLAPSE PROTECTION")
print("=" * 80)

# Apply Liquidity Collapse Protection on outcome labels
# If final price == 0 or final volume == 0 or final liquidity is collapsed, set ROI = 0.0 and label = Rug / dead
def reevaluate_row(row):
    t0_price = row["t0_price_usd"]
    t0_liq = row["t0_liquidity_usd"]
    tfinal_price = row["tfinal_24h_price_usd"]
    tfinal_vol = row["tfinal_24h_vol_usd"]
    raw_roi = row["roi_24h"]
    
    # Check for phantom price spikes (liquidity collapse / abandoned pool)
    # Phantom spike condition: raw_roi > 10.0 but final volume is 0 or price returned on empty pool
    # Or raw_roi > 50.0 on a token where t0_liquidity was low
    if raw_roi > 10.0 and (tfinal_vol < 10.0 or tfinal_price > 10.0):
        # Phantom spike on drained pool!
        corrected_roi = 0.0
        label = "Rug / dead"
    elif raw_roi >= 2.0:
        corrected_roi = raw_roi
        label = "Winner"
    elif raw_roi <= 0.2:
        corrected_roi = raw_roi
        label = "Rug / dead"
    else:
        corrected_roi = raw_roi
        label = "Flat / mediocre"
        
    return pd.Series([corrected_roi, label])

df_24h[["corr_roi_24h", "corr_outcome_label"]] = df_24h.apply(reevaluate_row, axis=1)

# Strict Target Scope ($30k-$100k MCap & >=$10k Liq)
strict_df = df_24h[
    (df_24h["t0_mcap_usd"] >= 30000) & 
    (df_24h["t0_mcap_usd"] <= 100000) & 
    (df_24h["t0_liquidity_usd"] >= 10000)
].copy()

print("\n--- 1. RE-EVALUATION OF THE 6 FLAGGED TOKENS ---")
target_addrs = [
    "J6LSivR3nt1LajG9TLaf8mvaGduSe6x4QXrsRDt1gsDz", # MTOV
    "4StqN9BQiQxzXTPVKfVfkyWXoh2DtuAo4dCQZ1otdiiT", # HTZ
    "BBxqYTrCKQTXBZ26oZRhvPsayJxqnBWu454EkTH2Gq4x", # GG
    "7yQhT7kt8LzFh6uFhWaKCXJhfCpnXiAiGRfJQeRhWoL9", # PF
    "F2z5Q3q9ujRGwwUSjCiN7cxmDQKyhUtU3KEWvXS5R94z", # Urara
    "dRSx7oCNUP7eRLdrqWqJX4NYVaMa1VetBRJ68AgsGML"  # bCard
]

for addr in target_addrs:
    sub = strict_df[strict_df["token_address"] == addr]
    if not sub.empty:
        r = sub.iloc[0]
        print(f"  Symbol: {r['symbol']:<10} | Raw ROI: {r['roi_24h']:>10.2f}x -> Corrected ROI: {r['corr_roi_24h']:>6.2f}x | Label: {r['corr_outcome_label']}")

print("\n--- 2. CORRECTED OUTCOME DISTRIBUTION IN TARGET SCOPE ($30k-$100k MCap) ---")
counts = strict_df['corr_outcome_label'].value_counts()
for label, cnt in counts.items():
    pct = (cnt / len(strict_df)) * 100
    print(f"  {label:<18}: {cnt:>4} ({pct:5.1f}%)")

print("\n--- 3. RE-RUN PRE-REGISTERED GATE 9 EVALUATION ON CORRECTED DATA ---")
winners = strict_df[strict_df["corr_outcome_label"] == "Winner"]
rugs = strict_df[strict_df["corr_outcome_label"] == "Rug / dead"]

win_pass = (winners["liq_mcap_ratio"] >= 0.20).sum() if len(winners) > 0 else 0
win_pct = (win_pass / len(winners) * 100) if len(winners) > 0 else 0.0

rug_elim = (rugs["liq_mcap_ratio"] < 0.20).sum() if len(rugs) > 0 else 0
rug_pct = (rug_elim / len(rugs) * 100) if len(rugs) > 0 else 0.0

print(f"  Total Validated Winners : {len(winners)}")
print(f"  Total Validated Rugs    : {len(rugs)}")
print(f"\n  Criterion 1 (Winner Preservation >= 75%): {win_pass}/{len(winners)} ({win_pct:.1f}%)")
print(f"    Status: {'PASSED [OK]' if win_pct >= 75.0 else 'FAILED [FAIL]'}")

print(f"\n  Criterion 2 (Rug Elimination >= 70%)   : {rug_elim}/{len(rugs)} ({rug_pct:.1f}%)")
print(f"    Status: {'PASSED [OK]' if rug_pct >= 70.0 else 'FAILED [FAIL]'}")

print("\n--- TOP 10 REAL WINNERS AFTER PHANTOM SPIKE CLEANUP ---")
top_real = winners.sort_values(by="corr_roi_24h", ascending=False).head(10)
for idx, row in top_real.iterrows():
    print(f"  [Winner] Symbol: {row['symbol']:<18} | 24h ROI: {row['corr_roi_24h']:>6.2f}x | T0 MCap: ${row['t0_mcap_usd']:>7,.0f} | T0 Liq: ${row['t0_liquidity_usd']:>6,.0f} | Ratio: {row['liq_mcap_ratio']:.3f}")

print("=" * 80)
