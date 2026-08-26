import math
from typing import List, Dict, Any

def process_birdeye_swaps(swaps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process raw Birdeye swaps (first 15m) into forensic metrics:
    - t0_unique_buyers
    - t0_single_wallet_vol_pct
    - t0_median_buy_size_usd
    """
    if not swaps:
        return {
            "t0_unique_buyers": 0,
            "t0_single_wallet_vol_pct": 0.0,
            "t0_median_buy_size_usd": 0.0,
            "t0_forensics_collected": False
        }
        
    buyer_wallets = set()
    wallet_volumes = {}
    buy_sizes_usd = []
    
    total_volume_usd = 0.0
    
    for swap in swaps:
        owner = swap.get("owner")
        side = swap.get("side")
        if not owner or not side:
            continue
            
        # Extract USD value (using the from price as a proxy)
        from_data = swap.get("from", {})
        price = from_data.get("price", 0.0)
        ui_amount = from_data.get("uiAmount", 0.0)
        usd_value = float(price * ui_amount)
        
        total_volume_usd += usd_value
        wallet_volumes[owner] = wallet_volumes.get(owner, 0.0) + usd_value
        
        if side == "buy":
            buyer_wallets.add(owner)
            buy_sizes_usd.append(usd_value)
            
    # Calculate unique buyers
    t0_unique_buyers = len(buyer_wallets)
    
    # Calculate single wallet vol pct
    max_wallet_vol = max(wallet_volumes.values()) if wallet_volumes else 0.0
    t0_single_wallet_vol_pct = (max_wallet_vol / total_volume_usd * 100.0) if total_volume_usd > 0 else 0.0
    
    # Calculate median buy size
    t0_median_buy_size_usd = 0.0
    if buy_sizes_usd:
        buy_sizes_usd.sort()
        n = len(buy_sizes_usd)
        if n % 2 == 1:
            t0_median_buy_size_usd = buy_sizes_usd[n // 2]
        else:
            t0_median_buy_size_usd = (buy_sizes_usd[n // 2 - 1] + buy_sizes_usd[n // 2]) / 2.0
            
    return {
        "t0_unique_buyers": t0_unique_buyers,
        "t0_single_wallet_vol_pct": round(t0_single_wallet_vol_pct, 2),
        "t0_median_buy_size_usd": round(t0_median_buy_size_usd, 2),
        "t0_forensics_collected": True
    }
