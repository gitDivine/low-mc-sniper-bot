import csv
import sys
sys.path.append("C:/Users/njoku/low-mc-sniper-bot")

def find_hyper_clean_rugs():
    file_path = "scratch/resolved_tokens_batch12.csv"
    hyper_clean = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["outcome_label"] == "rug":
                # Check gates
                record = row # We can pass row to the gates if they expect a dict, but let's see.
                
                # Mock a TokenSnapshotRecord or just do the checks directly to avoid type errors
                try:
                    lp_days = float(row.get("t0_lp_locked_days", 0))
                    g1 = lp_days >= 30
                    
                    dev_pct = float(row.get("t0_dev_wallet_pct", 100))
                    g4 = dev_pct < 10.0
                    
                    holders = int(float(row.get("t0_holder_count_floor", 0)))
                    g5 = holders >= 50
                    
                    uniq_buyers = float(row.get("t0_unique_buyers", 0))
                    g8 = uniq_buyers >= 25
                    
                    vol_pct = float(row.get("t0_single_wallet_vol_pct", 100))
                    g10 = vol_pct <= 25.0
                    
                    med_buy = float(row.get("t0_median_buy_size_usd", 0))
                    g13 = med_buy >= 2.0
                    
                    if g1 and g4 and g5 and g8 and g10 and g13:
                        hyper_clean.append(row["token_address"])
                except Exception as e:
                    pass
                    
    print(f"Found {len(hyper_clean)} Hyper-Clean rugs.")
    
    # Pick 5
    sample = hyper_clean[:5]
    for r in sample:
        print(f"Token: {r}")

if __name__ == "__main__":
    find_hyper_clean_rugs()
