import json

with open("data/shadow/pending_tokens.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print(f"SHADOW MODE — CAPTURED REAL-TIME T0 SNAPSHOTS ({len(data)} tokens)")
print("=" * 80)

for pool_addr, snapshot in list(data.items())[:10]:
    sym = snapshot.get("symbol", "UNKNOWN")
    price = snapshot.get("t0_price_usd", 0.0)
    liq = snapshot.get("t0_liquidity_usd", 0.0)
    top10 = snapshot.get("t0_top10_holder_pct", 0.0)
    dev = snapshot.get("t0_dev_wallet_pct", 0.0)
    lock = snapshot.get("t0_lp_locked_days", 0)
    t2022 = snapshot.get("t0_is_token_2022", False)
    malicious = snapshot.get("t0_has_malicious_extensions", False)
    ratio = snapshot.get("liq_mcap_ratio", 0.0)

    clean_sym = sym.encode('ascii', 'replace').decode('ascii')
    print(f"[{clean_sym}] Pool: {pool_addr[:12]}...")
    print(f"  Price: ${price:.6f} | Liq: ${liq:,.0f} | Liq/MCap Ratio: {ratio:.3f}")
    print(f"  Top 10 Holder %: {top10}% | Dev Wallet %: {dev}%")
    print(f"  LP Lock: {lock} days | Token-2022: {t2022} | Malicious Ext: {malicious}")
    print("-" * 80)
