import pandas as pd

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

print("=" * 75)
print("COMPREHENSIVE RUG-KILLER GATE AUDIT ON 1,055 CANDIDATES")
print("=" * 75)
print(f"Total Rugs: {len(rugs)} | Total Winners: {len(winners)}")

print("\n--- Gate 5: Dev Wallet % Cutoffs ---")
for cutoff in [50, 30, 20, 10, 5, 3]:
    rug_killed = (rugs["t0_dev_wallet_pct"] > cutoff).sum()
    win_killed = (winners["t0_dev_wallet_pct"] > cutoff).sum()
    print(f"  Dev Wallet > {cutoff}%: Kills {rug_killed}/{len(rugs)} Rugs ({rug_killed/len(rugs)*100:.1f}%) | Kills {win_killed}/{len(winners)} Winners ({win_killed/len(winners)*100:.1f}%)")

print("\n--- Gate 4: Top 10 Holder % Cutoffs ---")
for cutoff in [90, 80, 70, 60, 50]:
    rug_killed = (rugs["t0_top10_holder_pct"] > cutoff).sum()
    win_killed = (winners["t0_top10_holder_pct"] > cutoff).sum()
    print(f"  Top 10 > {cutoff}%: Kills {rug_killed}/{len(rugs)} Rugs ({rug_killed/len(rugs)*100:.1f}%) | Kills {win_killed}/{len(winners)} Winners ({win_killed/len(winners)*100:.1f}%)")

print("\n--- Gate 1: LP Lock / Burn (Locked >= 30 days) ---")
rug_locked = (rugs["t0_lp_locked_days"] >= 30).sum()
win_locked = (winners["t0_lp_locked_days"] >= 30).sum()
print(f"  LP Locked >= 30d: {rug_locked}/{len(rugs)} Rugs pass ({rug_locked/len(rugs)*100:.1f}%) | {win_locked}/{len(winners)} Winners pass ({win_locked/len(winners)*100:.1f}%)")

print("\n--- RTL Scam Filter ---")
if "t0_has_rtl_scam" in strict_df.columns:
    rtl_scams = (strict_df["t0_has_rtl_scam"] == True).sum()
    print(f"  RTL Scam Tokens Found in Target Scope: {rtl_scams}")

print("=" * 75)
