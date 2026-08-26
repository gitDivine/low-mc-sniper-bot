import re
import os

with open("src/shadow/runner.py", "r") as f:
    code = f.read()

# 1. Update _capture_t0_snapshot signature
code = code.replace(
    "has_rtl_scam: bool = False,",
    "has_rtl_scam: bool = False,\n        forensics: dict = None,"
)

# 2. Update dictionary populating
target_dict = """            "t0_avg_tx_size": 0.0,
            "t0_single_wallet_vol_pct": 0.0,  # Forensic field to be populated
            "pool_slot": 0,                   # Forensic field to be populated
            "creator_funding_slot": 0,        # Forensic field to be populated
            "pool_time": 0,                   # Forensic field to be populated
            "t0_forensics_collected": False,  # Flag to indicate if forensic data was collected"""

new_dict = """            "t0_avg_tx_size": 0.0,
            "t0_single_wallet_vol_pct": forensics.get("t0_single_wallet_vol_pct", 0.0) if forensics else 0.0,
            "t0_unique_buyers": forensics.get("t0_unique_buyers", 0) if forensics else 0,
            "t0_median_buy_size_usd": forensics.get("t0_median_buy_size_usd", 0.0) if forensics else 0.0,
            "pool_slot": 1000,                   # Temp bypass for Gate 12
            "creator_funding_slot": 0,           # Temp bypass for Gate 12
            "pool_time": 0,                   
            "t0_forensics_collected": forensics.get("t0_forensics_collected", False) if forensics else False,"""

code = code.replace(target_dict, new_dict)

# 3. Inject forensics fetch into process_waiting_t0_pools
injection_target = """                snapshot = await self._capture_t0_snapshot(
                    pool_address=pool_address,
                    token_address=data.get("token_address"),
                    symbol=data.get("symbol"),
                    price_usd=price_usd,
                    liquidity_usd=liquidity_usd,
                    mcap_usd=mcap_usd,
                    vol_15m=vol_15m,
                    age_hours=age_seconds / 3600.0,
                    has_rtl_scam=data.get("has_rtl_scam", False),
                )"""

injection_code = """                # Birdeye Forensics Fetch (First 15m)
                launch_timestamp = int(pool_dt.timestamp()) if 'pool_dt' in locals() else int(now - 900)
                birdeye_swaps = await api_client.fetch_birdeye_swaps(
                    token_address=data.get("token_address"),
                    launch_timestamp=launch_timestamp,
                    max_pages=10
                )
                
                forensics = {
                    "t0_unique_buyers": 0,
                    "t0_single_wallet_vol_pct": 0.0,
                    "t0_median_buy_size_usd": 0.0,
                    "t0_forensics_collected": False
                }
                
                if birdeye_swaps:
                    buyer_wallets = set()
                    wallet_volumes = {}
                    buy_sizes_usd = []
                    total_volume_usd = 0.0
                    
                    for swap in birdeye_swaps:
                        owner = swap.get("owner")
                        side = swap.get("side")
                        if not owner or not side:
                            continue
                            
                        # Extract USD value (using the from price as a proxy)
                        from_data = swap.get("from", {})
                        price = from_data.get("price", 0.0)
                        ui_amount = from_data.get("uiAmount", 0.0)
                        if price is None: price = 0.0
                        if ui_amount is None: ui_amount = 0.0
                        usd_value = float(price * ui_amount)
                        
                        total_volume_usd += usd_value
                        wallet_volumes[owner] = wallet_volumes.get(owner, 0.0) + usd_value
                        
                        if side == "buy":
                            buyer_wallets.add(owner)
                            buy_sizes_usd.append(usd_value)
                            
                    t0_unique_buyers = len(buyer_wallets)
                    max_wallet_vol = max(wallet_volumes.values()) if wallet_volumes else 0.0
                    t0_single_wallet_vol_pct = (max_wallet_vol / total_volume_usd * 100.0) if total_volume_usd > 0 else 0.0
                    
                    t0_median_buy_size_usd = 0.0
                    if buy_sizes_usd:
                        buy_sizes_usd.sort()
                        n = len(buy_sizes_usd)
                        if n % 2 == 1:
                            t0_median_buy_size_usd = buy_sizes_usd[n // 2]
                        else:
                            t0_median_buy_size_usd = (buy_sizes_usd[n // 2 - 1] + buy_sizes_usd[n // 2]) / 2.0
                            
                    forensics = {
                        "t0_unique_buyers": t0_unique_buyers,
                        "t0_single_wallet_vol_pct": round(t0_single_wallet_vol_pct, 2),
                        "t0_median_buy_size_usd": round(t0_median_buy_size_usd, 2),
                        "t0_forensics_collected": True
                    }
                    logger.info(f"Birdeye Forensics collected for {data.get('symbol')}: {t0_unique_buyers} buyers, max wallet {t0_single_wallet_vol_pct:.1f}%")
                else:
                    logger.warning(f"No Birdeye trades found for {data.get('symbol')} or fetch failed. Forensics marked False.")

                snapshot = await self._capture_t0_snapshot(
                    pool_address=pool_address,
                    token_address=data.get("token_address"),
                    symbol=data.get("symbol"),
                    price_usd=price_usd,
                    liquidity_usd=liquidity_usd,
                    mcap_usd=mcap_usd,
                    vol_15m=vol_15m,
                    age_hours=age_seconds / 3600.0,
                    has_rtl_scam=data.get("has_rtl_scam", False),
                    forensics=forensics,
                )"""

code = code.replace(injection_target, injection_code)

with open("src/shadow/runner.py", "w") as f:
    f.write(code)
print("Updated runner.py")
